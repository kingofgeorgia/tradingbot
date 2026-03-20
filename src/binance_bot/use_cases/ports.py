from __future__ import annotations

from typing import Protocol

from binance_bot.core.exchange import ExchangeExecutionPort
from binance_bot.core.models import BotState, SymbolFilters


class TradeExecutionClient(ExchangeExecutionPort, Protocol):
    pass


class TradeRiskManager(Protocol):
    def calculate_order_quantity(
        self,
        *,
        symbol: str,
        entry_price: float,
        total_equity: float,
        free_quote_balance: float,
        filters: SymbolFilters,
    ) -> float: ...

    def register_closed_trade(self, state: BotState, pnl: float, current_day: str) -> str | None: ...


class TradeStateStore(Protocol):
    def save(self, state: BotState) -> None: ...


class TradeJournal(Protocol):
    def write(self, row: dict[str, object]) -> None: ...


class TradeNotifier(Protocol):
    def send(self, message: str) -> None: ...


class TradeLogger(Protocol):
    def info(self, message: str, *args: object) -> None: ...