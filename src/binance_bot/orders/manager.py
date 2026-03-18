from __future__ import annotations

from datetime import UTC, datetime

from binance_bot.clients.binance_client import BinanceAPIError, BinanceSpotClient
from binance_bot.config import Settings
from binance_bot.core.journal import CsvJournal
from binance_bot.core.logging_setup import Loggers
from binance_bot.core.models import BotState, Position, SymbolFilters
from binance_bot.core.state import StateStore
from binance_bot.notify.telegram import TelegramNotifier
from binance_bot.risk.manager import RiskManager
from binance_bot.strategy.ema_cross import TradeSignal


class OrderManager:
    def __init__(
        self,
        settings: Settings,
        client: BinanceSpotClient,
        risk_manager: RiskManager,
        state_store: StateStore,
        loggers: Loggers,
        notifier: TelegramNotifier,
        signals_journal: CsvJournal,
        trades_journal: CsvJournal,
    ) -> None:
        self._settings = settings
        self._client = client
        self._risk_manager = risk_manager
        self._state_store = state_store
        self._loggers = loggers
        self._notifier = notifier
        self._signals_journal = signals_journal
        self._trades_journal = trades_journal

    def log_signal(self, signal: TradeSignal) -> None:
        self._signals_journal.write(
            {
                "timestamp_utc": self._utc_now_iso(),
                "symbol": signal.symbol,
                "action": signal.action,
                "reason": signal.reason,
                "price": signal.price,
                "ema_fast": signal.ema_fast,
                "ema_slow": signal.ema_slow,
                "mode": self._settings.app_mode,
            }
        )
        self._loggers.signal.info(
            "Signal %s for %s at %.4f | fast=%.4f slow=%.4f | %s",
            signal.action,
            signal.symbol,
            signal.price,
            signal.ema_fast,
            signal.ema_slow,
            signal.reason,
        )

    def open_long(
        self,
        signal: TradeSignal,
        filters: SymbolFilters,
        state: BotState,
        total_equity: float,
        free_quote_balance: float,
    ) -> None:
        quantity = self._risk_manager.calculate_order_quantity(
            entry_price=signal.price,
            total_equity=total_equity,
            free_quote_balance=free_quote_balance,
            filters=filters,
        )
        order_payload = self._client.create_market_order(signal.symbol, "BUY", quantity)
        confirmed_payload = self._confirm_order(signal.symbol, order_payload)

        average_price = self._client.calculate_average_fill_price(confirmed_payload)
        quote_spent = float(confirmed_payload["cummulativeQuoteQty"])
        fee_paid_quote = self._client.calculate_quote_fee(order_payload, self._settings.quote_asset)
        position = Position(
            symbol=signal.symbol,
            quantity=float(confirmed_payload["executedQty"]),
            entry_price=average_price,
            stop_loss=average_price * (1 - self._settings.stop_loss_pct),
            take_profit=average_price * (1 + self._settings.take_profit_pct),
            opened_at=self._utc_now_iso(),
            order_id=int(confirmed_payload["orderId"]),
            mode=self._settings.app_mode,
            quote_spent=quote_spent,
            fee_paid_quote=fee_paid_quote,
        )
        state.open_positions[signal.symbol] = position
        self._state_store.save(state)

        self._trades_journal.write(
            {
                "timestamp_utc": self._utc_now_iso(),
                "symbol": signal.symbol,
                "side": "BUY",
                "reason": signal.reason,
                "price": round(average_price, 8),
                "quantity": position.quantity,
                "stop_loss": round(position.stop_loss, 8),
                "take_profit": round(position.take_profit, 8),
                "fee_quote": round(fee_paid_quote, 8),
                "pnl_quote": "",
                "mode": self._settings.app_mode,
            }
        )
        self._loggers.trade.info(
            "Opened BUY %s | price=%.4f qty=%.8f stop=%.4f take=%.4f",
            signal.symbol,
            average_price,
            position.quantity,
            position.stop_loss,
            position.take_profit,
        )
        self._notifier.send(
            f"[{self._settings.app_mode}] Opened BUY {signal.symbol}\n"
            f"Price: {average_price:.4f}\n"
            f"Qty: {position.quantity:.8f}\n"
            f"Stop: {position.stop_loss:.4f}\n"
            f"Take: {position.take_profit:.4f}"
        )

    def close_position(self, symbol: str, reason: str, state: BotState) -> str | None:
        position = state.open_positions[symbol]
        filters = self._client.get_symbol_filters(symbol)
        quantity = self._client.round_step_size(position.quantity, filters.step_size)
        if quantity <= 0:
            raise BinanceAPIError(f"Position quantity for {symbol} became invalid after rounding.")

        order_payload = self._client.create_market_order(symbol, "SELL", quantity)
        confirmed_payload = self._confirm_order(symbol, order_payload)

        average_price = self._client.calculate_average_fill_price(confirmed_payload)
        quote_received = float(confirmed_payload["cummulativeQuoteQty"])
        exit_fee_quote = self._client.calculate_quote_fee(order_payload, self._settings.quote_asset)
        pnl_quote = quote_received - position.quote_spent - position.fee_paid_quote - exit_fee_quote
        current_day = datetime.now(tz=UTC).date().isoformat()

        del state.open_positions[symbol]
        halt_reason = self._risk_manager.register_closed_trade(state, pnl_quote, current_day)
        self._state_store.save(state)

        self._trades_journal.write(
            {
                "timestamp_utc": self._utc_now_iso(),
                "symbol": symbol,
                "side": "SELL",
                "reason": reason,
                "price": round(average_price, 8),
                "quantity": float(confirmed_payload["executedQty"]),
                "stop_loss": round(position.stop_loss, 8),
                "take_profit": round(position.take_profit, 8),
                "fee_quote": round(exit_fee_quote, 8),
                "pnl_quote": round(pnl_quote, 8),
                "mode": self._settings.app_mode,
            }
        )
        self._loggers.trade.info(
            "Closed %s | price=%.4f qty=%.8f pnl=%.4f | %s",
            symbol,
            average_price,
            float(confirmed_payload["executedQty"]),
            pnl_quote,
            reason,
        )
        self._notifier.send(
            f"[{self._settings.app_mode}] Closed {symbol}\n"
            f"Price: {average_price:.4f}\n"
            f"PnL: {pnl_quote:.4f} {self._settings.quote_asset}\n"
            f"Reason: {reason}"
        )
        if halt_reason is not None:
            self._notifier.send(
                f"[{self._settings.app_mode}] Trading halted\nReason: {halt_reason}\n"
                f"Daily PnL: {state.daily_realized_pnl:.4f} {self._settings.quote_asset}"
            )
        return halt_reason

    def _confirm_order(self, symbol: str, order_payload: dict[str, object]) -> dict[str, object]:
        if order_payload.get("status") == "FILLED":
            return order_payload
        return self._client.confirm_order_filled(
            symbol=symbol,
            order_id=int(order_payload["orderId"]),
            timeout_seconds=self._settings.order_confirm_timeout_seconds,
        )

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.now(tz=UTC).replace(microsecond=0).isoformat()
