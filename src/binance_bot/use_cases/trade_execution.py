from __future__ import annotations

from datetime import UTC, datetime

from binance_bot.clients.binance_client import BinanceAPIError
from binance_bot.config import Settings
from binance_bot.core.models import BotState, Position, SymbolFilters
from binance_bot.core.trade_execution import OpenPositionResult, build_open_position_result, calculate_close_result
from binance_bot.strategy.ema_cross import TradeSignal
from binance_bot.use_cases.ports import (
    TradeExecutionClient,
    TradeJournal,
    TradeLogger,
    TradeNotifier,
    TradeRiskManager,
    TradeStateStore,
)


class OpenPositionUseCase:
    def __init__(
        self,
        *,
        settings: Settings,
        client: TradeExecutionClient,
        risk_manager: TradeRiskManager,
        state_store: TradeStateStore,
        trades_journal: TradeJournal,
        trade_logger: TradeLogger,
        notifier: TradeNotifier,
    ) -> None:
        self._settings = settings
        self._client = client
        self._risk_manager = risk_manager
        self._state_store = state_store
        self._trades_journal = trades_journal
        self._trade_logger = trade_logger
        self._notifier = notifier

    def execute(
        self,
        *,
        signal: TradeSignal,
        filters: SymbolFilters,
        state: BotState,
        total_equity: float,
        free_quote_balance: float,
    ) -> OpenPositionResult:
        quantity = self._risk_manager.calculate_order_quantity(
            symbol=signal.symbol,
            entry_price=signal.price,
            total_equity=total_equity,
            free_quote_balance=free_quote_balance,
            filters=filters,
        )
        order_payload = self._client.create_market_order(signal.symbol, "BUY", quantity)
        confirmed_payload = _confirm_order(
            client=self._client,
            symbol=signal.symbol,
            order_payload=order_payload,
            timeout_seconds=self._settings.order_confirm_timeout_seconds,
        )

        average_price = self._client.calculate_average_fill_price(confirmed_payload)
        quote_spent = float(confirmed_payload["cummulativeQuoteQty"])
        fee_paid_quote = self._client.calculate_quote_fee(order_payload, self._settings.quote_asset)
        result = build_open_position_result(
            symbol=signal.symbol,
            quantity=float(confirmed_payload["executedQty"]),
            average_price=average_price,
            stop_loss_pct=self._settings.stop_loss_pct,
            take_profit_pct=self._settings.take_profit_pct,
            opened_at=_utc_now_iso(),
            order_id=int(confirmed_payload["orderId"]),
            mode=self._settings.app_mode,
            quote_spent=quote_spent,
            fee_paid_quote=fee_paid_quote,
        )

        state.open_positions[signal.symbol] = result.position
        self._state_store.save(state)
        self._write_open_trade(signal=signal, result=result)
        self._notify_open(result)
        return result

    def _write_open_trade(self, *, signal: TradeSignal, result: OpenPositionResult) -> None:
        self._trades_journal.write(
            {
                "timestamp_utc": _utc_now_iso(),
                "symbol": signal.symbol,
                "side": "BUY",
                "reason": signal.reason,
                "price": round(result.average_price, 8),
                "quantity": result.quantity,
                "stop_loss": round(result.stop_loss, 8),
                "take_profit": round(result.take_profit, 8),
                "fee_quote": round(result.fee_paid_quote, 8),
                "pnl_quote": "",
                "mode": self._settings.app_mode,
            }
        )
        self._trade_logger.info(
            "Opened BUY %s | price=%.4f qty=%.8f stop=%.4f take=%.4f",
            signal.symbol,
            result.average_price,
            result.quantity,
            result.stop_loss,
            result.take_profit,
        )

    def _notify_open(self, result: OpenPositionResult) -> None:
        self._notifier.send(
            f"[{self._settings.app_mode}] Opened BUY {result.symbol}\n"
            f"Price: {result.average_price:.4f}\n"
            f"Qty: {result.quantity:.8f}\n"
            f"Stop: {result.stop_loss:.4f}\n"
            f"Take: {result.take_profit:.4f}"
        )


class ClosePositionUseCase:
    def __init__(
        self,
        *,
        settings: Settings,
        client: TradeExecutionClient,
        risk_manager: TradeRiskManager,
        state_store: TradeStateStore,
        trades_journal: TradeJournal,
        trade_logger: TradeLogger,
        notifier: TradeNotifier,
    ) -> None:
        self._settings = settings
        self._client = client
        self._risk_manager = risk_manager
        self._state_store = state_store
        self._trades_journal = trades_journal
        self._trade_logger = trade_logger
        self._notifier = notifier

    def execute(self, *, symbol: str, reason: str, state: BotState) -> str | None:
        position = state.open_positions[symbol]
        filters = self._client.get_symbol_filters(symbol)
        quantity = self._client.round_step_size(position.quantity, filters.step_size)
        if quantity <= 0:
            raise BinanceAPIError(f"Position quantity for {symbol} became invalid after rounding.")

        order_payload = self._client.create_market_order(symbol, "SELL", quantity)
        confirmed_payload = _confirm_order(
            client=self._client,
            symbol=symbol,
            order_payload=order_payload,
            timeout_seconds=self._settings.order_confirm_timeout_seconds,
        )

        average_price = self._client.calculate_average_fill_price(confirmed_payload)
        quote_received = float(confirmed_payload["cummulativeQuoteQty"])
        exit_fee_quote = self._client.calculate_quote_fee(order_payload, self._settings.quote_asset)
        current_day = datetime.now(tz=UTC).date().isoformat()

        del state.open_positions[symbol]
        provisional_result = calculate_close_result(
            symbol=symbol,
            reason=reason,
            position=position,
            average_price=average_price,
            executed_quantity=float(confirmed_payload["executedQty"]),
            quote_received=quote_received,
            exit_fee_quote=exit_fee_quote,
            halt_reason=None,
        )
        halt_reason = self._risk_manager.register_closed_trade(state, provisional_result.pnl_quote, current_day)
        self._state_store.save(state)
        result = calculate_close_result(
            symbol=symbol,
            reason=reason,
            position=position,
            average_price=average_price,
            executed_quantity=float(confirmed_payload["executedQty"]),
            quote_received=quote_received,
            exit_fee_quote=exit_fee_quote,
            halt_reason=halt_reason,
        )

        self._write_close_trade(position=position, result=result)
        self._notify_close(state=state, result=result)
        return halt_reason

    def _write_close_trade(self, *, position: Position, result) -> None:
        self._trades_journal.write(
            {
                "timestamp_utc": _utc_now_iso(),
                "symbol": result.symbol,
                "side": "SELL",
                "reason": result.reason,
                "price": round(result.average_price, 8),
                "quantity": result.executed_quantity,
                "stop_loss": round(position.stop_loss, 8),
                "take_profit": round(position.take_profit, 8),
                "fee_quote": round(result.exit_fee_quote, 8),
                "pnl_quote": round(result.pnl_quote, 8),
                "mode": self._settings.app_mode,
            }
        )
        self._trade_logger.info(
            "Closed %s | price=%.4f qty=%.8f pnl=%.4f | %s",
            result.symbol,
            result.average_price,
            result.executed_quantity,
            result.pnl_quote,
            result.reason,
        )

    def _notify_close(self, *, state: BotState, result) -> None:
        self._notifier.send(
            f"[{self._settings.app_mode}] Closed {result.symbol}\n"
            f"Price: {result.average_price:.4f}\n"
            f"PnL: {result.pnl_quote:.4f} {self._settings.quote_asset}\n"
            f"Reason: {result.reason}"
        )
        if result.halt_reason is not None:
            self._notifier.send(
                f"[{self._settings.app_mode}] Trading halted\nReason: {result.halt_reason}\n"
                f"Daily PnL: {state.daily_realized_pnl:.4f} {self._settings.quote_asset}"
            )


def _confirm_order(
    *,
    client: TradeExecutionClient,
    symbol: str,
    order_payload: dict[str, object],
    timeout_seconds: int,
) -> dict[str, object]:
    if order_payload.get("status") == "FILLED":
        return order_payload
    return client.confirm_order_filled(
        symbol=symbol,
        order_id=int(order_payload["orderId"]),
        timeout_seconds=timeout_seconds,
    )


def _utc_now_iso() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat()