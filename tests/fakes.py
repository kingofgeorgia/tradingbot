from __future__ import annotations

import sys
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from binance_bot.config import Settings
from binance_bot.core.models import BotState, SymbolFilters


class FakeNotifier:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def send(self, message: str) -> None:
        self.messages.append(message)


class FakeJournal:
    def __init__(self) -> None:
        self.rows: list[dict[str, object]] = []

    def write(self, row: dict[str, object]) -> None:
        self.rows.append(dict(row))


class FakeLogger:
    def __init__(self) -> None:
        self.entries: list[str] = []

    def info(self, msg: str, *args, **kwargs) -> None:
        self.entries.append(msg % args if args else msg)

    def error(self, msg: str, *args, **kwargs) -> None:
        self.entries.append(msg % args if args else msg)


class FakeLoggers:
    def __init__(self) -> None:
        self.app = FakeLogger()
        self.signal = FakeLogger()
        self.trade = FakeLogger()
        self.error = FakeLogger()


class FakeStateStore:
    def __init__(self) -> None:
        self.saved_states: list[dict[str, object]] = []

    def save(self, state: BotState) -> None:
        self.saved_states.append(state.to_dict())


@dataclass
class FakeRiskManager:
    quantity: float = 0.05
    halt_reason: str | None = None

    def __post_init__(self) -> None:
        self.calculate_calls: list[dict[str, object]] = []
        self.closed_trade_calls: list[dict[str, object]] = []

    def calculate_order_quantity(
        self,
        entry_price: float,
        total_equity: float,
        free_quote_balance: float,
        filters: SymbolFilters,
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
        self.closed_trade_calls.append({"pnl": pnl, "current_day": current_day})
        state.daily_realized_pnl += pnl
        state.total_closed_trades += 1
        if pnl < 0:
            state.consecutive_losses += 1
        else:
            state.consecutive_losses = 0
        if self.halt_reason is not None:
            state.halted_until_day = current_day
        return self.halt_reason


class FakeClient:
    def __init__(
        self,
        *,
        filters: SymbolFilters | None = None,
        buy_price: float = 100.0,
        sell_price: float = 110.0,
        quote_asset: str = "USDT",
        buy_fee: float = 0.01,
        sell_fee: float = 0.01,
    ) -> None:
        self.filters = filters or SymbolFilters(step_size=0.001, min_qty=0.001, min_notional=10.0, tick_size=0.01)
        self.buy_price = buy_price
        self.sell_price = sell_price
        self.quote_asset = quote_asset
        self.buy_fee = buy_fee
        self.sell_fee = sell_fee
        self.created_orders: list[dict[str, object]] = []
        self.confirm_requests: list[dict[str, object]] = []
        self._next_order_id = 1000

    def create_market_order(self, symbol: str, side: str, quantity: float) -> dict[str, object]:
        self._next_order_id += 1
        price = self.buy_price if side == "BUY" else self.sell_price
        fee = self.buy_fee if side == "BUY" else self.sell_fee
        payload = {
            "symbol": symbol,
            "side": side,
            "status": "FILLED",
            "orderId": self._next_order_id,
            "executedQty": f"{quantity:.8f}",
            "cummulativeQuoteQty": f"{quantity * price:.8f}",
            "fills": [
                {
                    "commissionAsset": self.quote_asset,
                    "commission": f"{fee:.8f}",
                }
            ],
        }
        self.created_orders.append(payload)
        return payload

    def confirm_order_filled(self, symbol: str, order_id: int, timeout_seconds: int) -> dict[str, object]:
        self.confirm_requests.append(
            {"symbol": symbol, "order_id": order_id, "timeout_seconds": timeout_seconds}
        )
        raise AssertionError("confirm_order_filled should not be called for FILLED fake orders")

    @staticmethod
    def calculate_average_fill_price(order_payload: dict[str, object]) -> float:
        return float(order_payload["cummulativeQuoteQty"]) / float(order_payload["executedQty"])

    @staticmethod
    def calculate_quote_fee(order_payload: dict[str, object], quote_asset: str) -> float:
        fee_paid_quote = 0.0
        for fill in order_payload.get("fills", []):
            if fill.get("commissionAsset") == quote_asset:
                fee_paid_quote += float(fill.get("commission", 0.0))
        return fee_paid_quote

    def get_symbol_filters(self, symbol: str) -> SymbolFilters:
        return self.filters

    @staticmethod
    def round_step_size(value: float, step_size: float) -> float:
        if step_size <= 0:
            return value
        return float(Decimal(str(value)).quantize(Decimal(str(step_size)), rounding=ROUND_DOWN))


def make_settings() -> Settings:
    project_root = PROJECT_ROOT
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