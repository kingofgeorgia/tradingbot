from __future__ import annotations

from typing import Protocol

from binance_bot.core.models import BotState, SymbolFilters


class TradeExecutionClient(Protocol):
    def create_market_order(self, symbol: str, side: str, quantity: float) -> dict[str, object]: ...

    def confirm_order_filled(self, symbol: str, order_id: int, timeout_seconds: int) -> dict[str, object]: ...

    def calculate_average_fill_price(self, order_payload: dict[str, object]) -> float: ...

    def calculate_quote_fee(self, order_payload: dict[str, object], quote_asset: str) -> float: ...

    def get_symbol_filters(self, symbol: str) -> SymbolFilters: ...

    def round_step_size(self, value: float, step_size: float) -> float: ...


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