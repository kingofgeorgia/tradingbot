from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


CURRENT_STATE_SCHEMA_VERSION = 1


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
class ExchangePositionSnapshot:
    symbol: str
    base_asset: str
    exchange_quantity: float
    average_entry_price: float | None
    last_order_id: int | None
    last_trade_time: int | None
    has_open_orders: bool
    has_recent_trades: bool
    step_size: float


@dataclass(slots=True)
class StartupIssue:
    symbol: str
    issue_type: str
    local_qty: float
    exchange_qty: float
    action: str
    status: str
    message: str

    @property
    def issue_key(self) -> str:
        return f"{self.symbol}:{self.issue_type}:{self.action}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "StartupIssue":
        return cls(
            symbol=str(payload.get("symbol", "")),
            issue_type=str(payload.get("issue_type", "unknown")),
            local_qty=float(payload.get("local_qty", 0.0)),
            exchange_qty=float(payload.get("exchange_qty", 0.0)),
            action=str(payload.get("action", "none")),
            status=str(payload.get("status", "open")),
            message=str(payload.get("message", "")),
        )


@dataclass(slots=True)
class SymbolRuntimeStatus:
    symbol: str
    status: str
    blocked: bool
    suspect_position: bool
    reason: str
    effective_runtime_mode: str = "trade"
    has_open_position: bool = False
    startup_issue_key: str | None = None
    issue_acknowledged: bool = False
    last_manual_action: str | None = None


@dataclass(slots=True)
class ReconciliationResult:
    symbol_statuses: dict[str, SymbolRuntimeStatus] = field(default_factory=dict)
    issues: list[StartupIssue] = field(default_factory=list)
    blocked_symbols: dict[str, str] = field(default_factory=dict)
    suspect_positions: dict[str, str] = field(default_factory=dict)
    restored_snapshots: dict[str, ExchangePositionSnapshot] = field(default_factory=dict)
    status: str = "clean"


@dataclass(slots=True)
class RepairRecord:
    symbol: str
    action: str
    status: str
    note: str
    timestamp_utc: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RepairRecord":
        return cls(
            symbol=str(payload.get("symbol", "")),
            action=str(payload.get("action", "unknown")),
            status=str(payload.get("status", "unknown")),
            note=str(payload.get("note", "")),
            timestamp_utc=str(payload.get("timestamp_utc", "")),
        )


@dataclass(slots=True)
class RuntimeStatusReport:
    runtime_mode: str
    blocked_symbols: dict[str, str]
    suspect_positions: dict[str, str]
    open_positions: list[str]
    startup_issue_keys: list[str]
    symbol_statuses: list[SymbolRuntimeStatus]
    last_reconciled_at: str | None
    last_reconciliation_status: str | None
    last_manual_review_at: str | None


@dataclass(slots=True)
class BotState:
    schema_version: int = CURRENT_STATE_SCHEMA_VERSION
    trading_day: str = ""
    day_start_equity: float = 0.0
    daily_realized_pnl: float = 0.0
    consecutive_losses: int = 0
    open_positions: dict[str, Position] = field(default_factory=dict)
    halted_until_day: str | None = None
    total_closed_trades: int = 0
    last_processed_candle: dict[str, int] = field(default_factory=dict)
    blocked_symbols: dict[str, str] = field(default_factory=dict)
    suspect_positions: dict[str, str] = field(default_factory=dict)
    startup_issues: list[StartupIssue] = field(default_factory=list)
    acknowledged_startup_issues: list[str] = field(default_factory=list)
    alerted_startup_issues: list[str] = field(default_factory=list)
    repair_history: list[RepairRecord] = field(default_factory=list)
    last_reconciled_at: str | None = None
    last_reconciliation_status: str | None = None
    last_manual_review_at: str | None = None
    last_manual_action_by_symbol: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "trading_day": self.trading_day,
            "day_start_equity": self.day_start_equity,
            "daily_realized_pnl": self.daily_realized_pnl,
            "consecutive_losses": self.consecutive_losses,
            "open_positions": {symbol: position.to_dict() for symbol, position in self.open_positions.items()},
            "halted_until_day": self.halted_until_day,
            "total_closed_trades": self.total_closed_trades,
            "last_processed_candle": self.last_processed_candle,
            "blocked_symbols": self.blocked_symbols,
            "suspect_positions": self.suspect_positions,
            "startup_issues": [issue.to_dict() for issue in self.startup_issues],
            "acknowledged_startup_issues": self.acknowledged_startup_issues,
            "alerted_startup_issues": self.alerted_startup_issues,
            "repair_history": [record.to_dict() for record in self.repair_history],
            "last_reconciled_at": self.last_reconciled_at,
            "last_reconciliation_status": self.last_reconciliation_status,
            "last_manual_review_at": self.last_manual_review_at,
            "last_manual_action_by_symbol": self.last_manual_action_by_symbol,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "BotState":
        positions = {
            symbol: Position.from_dict(position_payload)
            for symbol, position_payload in payload.get("open_positions", {}).items()
        }
        startup_issues = [
            StartupIssue.from_dict(issue_payload)
            for issue_payload in payload.get("startup_issues", [])
            if isinstance(issue_payload, dict)
        ]
        repair_history = [
            RepairRecord.from_dict(record_payload)
            for record_payload in payload.get("repair_history", [])
            if isinstance(record_payload, dict)
        ]
        return cls(
            schema_version=int(payload.get("schema_version", CURRENT_STATE_SCHEMA_VERSION)),
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
            blocked_symbols={
                str(symbol): str(reason) for symbol, reason in payload.get("blocked_symbols", {}).items()
            },
            suspect_positions={
                str(symbol): str(reason) for symbol, reason in payload.get("suspect_positions", {}).items()
            },
            startup_issues=startup_issues,
            acknowledged_startup_issues=[str(item) for item in payload.get("acknowledged_startup_issues", [])],
            alerted_startup_issues=[str(item) for item in payload.get("alerted_startup_issues", [])],
            repair_history=repair_history,
            last_reconciled_at=payload.get("last_reconciled_at"),
            last_reconciliation_status=payload.get("last_reconciliation_status"),
            last_manual_review_at=payload.get("last_manual_review_at"),
            last_manual_action_by_symbol={
                str(symbol): str(action) for symbol, action in payload.get("last_manual_action_by_symbol", {}).items()
            },
        )
