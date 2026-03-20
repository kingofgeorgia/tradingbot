from __future__ import annotations

from datetime import UTC, datetime

from binance_bot.config import Settings
from binance_bot.core.exchange import ExchangeExecutionPort
from binance_bot.core.journal import CsvJournal
from binance_bot.core.logging_setup import Loggers
from binance_bot.core.models import BotState, ExchangePositionSnapshot, Position, SymbolFilters
from binance_bot.core.state import StateStore
from binance_bot.notify.telegram import TelegramNotifier
from binance_bot.risk.manager import RiskManager
from binance_bot.strategy.ema_cross import TradeSignal
from binance_bot.use_cases.trade_execution import ClosePositionUseCase, OpenPositionUseCase


class OrderManager:
    def __init__(
        self,
        settings: Settings,
        client: ExchangeExecutionPort,
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
        self._open_position = OpenPositionUseCase(
            settings=settings,
            client=client,
            risk_manager=risk_manager,
            state_store=state_store,
            trades_journal=trades_journal,
            trade_logger=loggers.trade,
            notifier=notifier,
        )
        self._close_position = ClosePositionUseCase(
            settings=settings,
            client=client,
            risk_manager=risk_manager,
            state_store=state_store,
            trades_journal=trades_journal,
            trade_logger=loggers.trade,
            notifier=notifier,
        )

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
        self._open_position.execute(
            signal=signal,
            filters=filters,
            state=state,
            total_equity=total_equity,
            free_quote_balance=free_quote_balance,
        )

    def close_position(self, symbol: str, reason: str, state: BotState) -> str | None:
        return self._close_position.execute(symbol=symbol, reason=reason, state=state)

    def restore_position_from_exchange(self, snapshot: ExchangePositionSnapshot, state: BotState) -> None:
        if snapshot.average_entry_price is None or snapshot.last_order_id is None:
            raise ValueError(f"Cannot restore {snapshot.symbol} without exchange entry price and order id.")

        average_price = snapshot.average_entry_price
        quantity = snapshot.exchange_quantity
        state.open_positions[snapshot.symbol] = Position(
            symbol=snapshot.symbol,
            quantity=quantity,
            entry_price=average_price,
            stop_loss=average_price * (1 - self._settings.stop_loss_pct),
            take_profit=average_price * (1 + self._settings.take_profit_pct),
            opened_at=self._utc_now_iso(),
            order_id=snapshot.last_order_id,
            mode=self._settings.app_mode,
            quote_spent=average_price * quantity,
            fee_paid_quote=0.0,
        )

    @staticmethod
    def drop_local_position(symbol: str, state: BotState) -> None:
        state.open_positions.pop(symbol, None)
        state.suspect_positions.pop(symbol, None)

    @staticmethod
    def mark_position_unrecoverable(symbol: str, reason: str, state: BotState) -> None:
        state.blocked_symbols[symbol] = reason
        if symbol in state.open_positions:
            state.suspect_positions[symbol] = reason

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.now(tz=UTC).replace(microsecond=0).isoformat()
