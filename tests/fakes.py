from __future__ import annotations

from pathlib import Path

from binance_bot.config import Settings
from binance_bot.core.models import BotState


class FakeJournal:
    def __init__(self) -> None:
        self.rows: list[dict[str, object]] = []

    def write(self, row: dict[str, object]) -> None:
        self.rows.append(row)


class FakeNotifier:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def send(self, message: str) -> None:
        self.messages.append(message)


class FakeLogger:
    def __init__(self) -> None:
        self.records: list[tuple[str, tuple[object, ...]]] = []

    def info(self, message: str, *args: object) -> None:
        self.records.append((message, args))

    def error(self, message: str, *args: object, **kwargs: object) -> None:
        self.records.append((message, args))


class FakeLoggers:
    def __init__(self) -> None:
        self.app = FakeLogger()
        self.signal = FakeLogger()
        self.trade = FakeLogger()
        self.error = FakeLogger()


class FakeStateStore:
    def __init__(self, initial_state: BotState | None = None) -> None:
        self._state = initial_state or BotState()
        self.saved_states: list[BotState] = []

    def load(self) -> BotState:
        return self._state

    def save(self, state: BotState) -> None:
        self._state = state
        self.saved_states.append(state)


class FakeRiskManager:
    def __init__(self, quantity: float, halt_reason: str | None = None) -> None:
        self.quantity = quantity
        self.halt_reason = halt_reason
        self.calculate_calls: list[dict[str, object]] = []
        self.closed_trade_calls: list[tuple[float, str]] = []

    def calculate_order_quantity(
        self,
        *,
        entry_price: float,
        total_equity: float,
        free_quote_balance: float,
        filters: object,
    ) -> float:
        self.calculate_calls.append(
            {
                "entry_price": entry_price,
                "total_equity": total_equity,
                "free_quote_balance": free_quote_balance,
                "filters": filters,
            }
        )
        return self.quantity

    def register_closed_trade(self, state: BotState, pnl: float, current_day: str) -> str | None:
        state.daily_realized_pnl += pnl
        state.total_closed_trades += 1
        if pnl < 0:
            state.consecutive_losses += 1
        else:
            state.consecutive_losses = 0
        self.closed_trade_calls.append((pnl, current_day))
        if self.halt_reason is not None:
            state.halted_until_day = current_day
        return self.halt_reason


class FakeBinanceClient:
    def __init__(self) -> None:
        self.created_orders: list[tuple[str, str, float]] = []
        self.confirm_calls: list[tuple[str, int, int]] = []
        self.filters_by_symbol: dict[str, object] = {}
        self.next_create_payload: dict[str, object] | None = None
        self.next_confirm_payload: dict[str, object] | None = None
        self.rounded_quantity: float | None = None

    def create_market_order(self, symbol: str, side: str, quantity: float) -> dict[str, object]:
        self.created_orders.append((symbol, side, quantity))
        if self.next_create_payload is None:
            raise AssertionError("next_create_payload was not configured")
        return self.next_create_payload

    def confirm_order_filled(self, symbol: str, order_id: int, timeout_seconds: int) -> dict[str, object]:
        self.confirm_calls.append((symbol, order_id, timeout_seconds))
        if self.next_confirm_payload is None:
            return self.next_create_payload or {}
        return self.next_confirm_payload

    def calculate_average_fill_price(self, order_payload: dict[str, object]) -> float:
        executed_qty = float(order_payload["executedQty"])
        cumulative_quote_qty = float(order_payload["cummulativeQuoteQty"])
        return cumulative_quote_qty / executed_qty

    def calculate_quote_fee(self, order_payload: dict[str, object], quote_asset: str) -> float:
        fee = 0.0
        for fill in order_payload.get("fills", []):
            if fill.get("commissionAsset") == quote_asset:
                fee += float(fill.get("commission", 0.0))
        return fee

    def get_symbol_filters(self, symbol: str):
        return self.filters_by_symbol[symbol]

    def round_step_size(self, value: float, step_size: float) -> float:
        if self.rounded_quantity is not None:
            return self.rounded_quantity
        return value


def make_settings() -> Settings:
    project_root = Path(".")
    return Settings(
        app_mode="demo",
        binance_api_key="key",
        binance_secret_key="secret",
        binance_recv_window=5000,
        telegram_bot_token=None,
        telegram_chat_id=None,
        symbols=["BTCUSDT", "ETHUSDT"],
        timeframe="15m",
        candle_limit=120,
        fast_ema_period=20,
        slow_ema_period=50,
        stop_loss_pct=0.02,
        take_profit_pct=0.04,
        risk_per_trade_pct=0.01,
        max_position_pct=0.10,
        max_open_positions_total=2,
        max_open_positions_per_symbol=1,
        daily_loss_limit_pct=0.03,
        max_consecutive_losses=3,
        loop_interval_seconds=30,
        order_confirm_timeout_seconds=15,
        request_timeout_seconds=15,
        stale_data_multiplier=2,
        quote_asset="USDT",
        run_once=True,
        project_root=project_root,
        data_dir=project_root / "data",
        logs_dir=project_root / "logs",
    )
