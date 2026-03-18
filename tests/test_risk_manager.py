from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from binance_bot.config import Settings
from binance_bot.core.models import BotState, Position, SymbolFilters
from binance_bot.risk.manager import RiskManager


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


class RiskManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manager = RiskManager(make_settings())

    def test_calculate_order_quantity_uses_smallest_budget(self) -> None:
        filters = SymbolFilters(step_size=0.001, min_qty=0.001, min_notional=10.0, tick_size=0.01)
        quantity = self.manager.calculate_order_quantity(
            entry_price=19.87,
            total_equity=1000.0,
            free_quote_balance=200.0,
            filters=filters,
        )
        self.assertAlmostEqual(quantity, 5.032, places=3)

    def test_can_open_position_blocks_existing_symbol(self) -> None:
        state = BotState(
            open_positions={
                "BTCUSDT": Position(
                    symbol="BTCUSDT",
                    quantity=0.1,
                    entry_price=100.0,
                    stop_loss=98.0,
                    take_profit=104.0,
                    opened_at="2026-03-19T00:00:00+00:00",
                    order_id=1,
                    mode="demo",
                    quote_spent=10.0,
                    fee_paid_quote=0.01,
                )
            }
        )
        allowed, reason = self.manager.can_open_position("BTCUSDT", state, "2026-03-19")
        self.assertFalse(allowed)
        self.assertEqual(reason, "position-already-open-for-symbol")

    def test_register_closed_trade_halts_after_daily_loss_limit(self) -> None:
        state = BotState(trading_day="2026-03-19", day_start_equity=1000.0)
        reason = self.manager.register_closed_trade(state, pnl=-35.0, current_day="2026-03-19")
        self.assertEqual(reason, "daily-loss-limit-reached")
        self.assertEqual(state.halted_until_day, "2026-03-19")

    def test_refresh_trading_day_resets_daily_counters(self) -> None:
        state = BotState(
            trading_day="2026-03-18",
            day_start_equity=1000.0,
            daily_realized_pnl=-10.0,
            consecutive_losses=2,
            halted_until_day="2026-03-18",
        )
        self.manager.refresh_trading_day(state, current_day="2026-03-19", current_equity=1200.0)
        self.assertEqual(state.trading_day, "2026-03-19")
        self.assertEqual(state.day_start_equity, 1200.0)
        self.assertEqual(state.daily_realized_pnl, 0.0)
        self.assertEqual(state.consecutive_losses, 0)
        self.assertIsNone(state.halted_until_day)


if __name__ == "__main__":
    unittest.main()