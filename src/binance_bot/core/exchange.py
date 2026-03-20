from __future__ import annotations

from typing import Protocol

from binance_bot.core.models import Candle, ExchangePositionSnapshot, SymbolFilters


class ExchangeAPIError(RuntimeError):
    """Raised when an exchange adapter returns an API or transport error."""


class ExchangeExecutionPort(Protocol):
    def create_market_order(self, symbol: str, side: str, quantity: float) -> dict[str, object]: ...

    def confirm_order_filled(self, symbol: str, order_id: int, timeout_seconds: int) -> dict[str, object]: ...

    def calculate_average_fill_price(self, order_payload: dict[str, object]) -> float: ...

    def calculate_quote_fee(self, order_payload: dict[str, object], quote_asset: str) -> float: ...

    def get_symbol_filters(self, symbol: str) -> SymbolFilters: ...

    def round_step_size(self, value: float, step_size: float) -> float: ...


class ExchangeMarketDataPort(Protocol):
    def get_portfolio_value(self, symbols: list[str], quote_asset: str) -> float: ...

    def get_asset_free_balance(self, asset: str) -> float: ...

    def get_klines(self, symbol: str, interval: str, limit: int) -> list[Candle]: ...

    def get_latest_price(self, symbol: str) -> float: ...

    def get_symbol_filters(self, symbol: str) -> SymbolFilters: ...


class ExchangeReconciliationPort(Protocol):
    def get_position_snapshot(self, symbol: str, quote_asset: str) -> ExchangePositionSnapshot: ...


class ExchangeRuntimePort(
    ExchangeExecutionPort,
    ExchangeMarketDataPort,
    ExchangeReconciliationPort,
    Protocol,
):
    def sync_time(self) -> None: ...