from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class Candle:
    open_time: int
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float
    close_time: int
    is_closed: bool


@dataclass(slots=True)
class SymbolFilters:
    step_size: float
    min_qty: float
    min_notional: float
    tick_size: float


@dataclass(slots=True)
class Position:
    symbol: str
    quantity: float
    entry_price: float
    stop_loss: float
    take_profit: float
    opened_at: str
    order_id: int
    mode: str
    quote_spent: float
    fee_paid_quote: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Position":
        return cls(**payload)


@dataclass(slots=True)
class BotState:
    trading_day: str = ""
    day_start_equity: float = 0.0
    daily_realized_pnl: float = 0.0
    consecutive_losses: int = 0
    open_positions: dict[str, Position] = field(default_factory=dict)
    halted_until_day: str | None = None
    total_closed_trades: int = 0
    last_processed_candle: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trading_day": self.trading_day,
            "day_start_equity": self.day_start_equity,
            "daily_realized_pnl": self.daily_realized_pnl,
            "consecutive_losses": self.consecutive_losses,
            "open_positions": {symbol: position.to_dict() for symbol, position in self.open_positions.items()},
            "halted_until_day": self.halted_until_day,
            "total_closed_trades": self.total_closed_trades,
            "last_processed_candle": self.last_processed_candle,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "BotState":
        positions = {
            symbol: Position.from_dict(position_payload)
            for symbol, position_payload in payload.get("open_positions", {}).items()
        }
        return cls(
            trading_day=payload.get("trading_day", ""),
            day_start_equity=float(payload.get("day_start_equity", 0.0)),
            daily_realized_pnl=float(payload.get("daily_realized_pnl", 0.0)),
            consecutive_losses=int(payload.get("consecutive_losses", 0)),
            open_positions=positions,
            halted_until_day=payload.get("halted_until_day"),
            total_closed_trades=int(payload.get("total_closed_trades", 0)),
            last_processed_candle={
                symbol: int(value) for symbol, value in payload.get("last_processed_candle", {}).items()
            },
        )
