from __future__ import annotations

import sys
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from binance_bot.core.models import Candle
from binance_bot.strategy.ema_cross import EmaCrossStrategy


def build_candles(closes: list[float], latest_offset_minutes: int = 0) -> list[Candle]:
    latest = datetime.now(tz=UTC) - timedelta(minutes=latest_offset_minutes)
    candles: list[Candle] = []
    for index, close in enumerate(closes):
        close_dt = latest - timedelta(minutes=15 * (len(closes) - index - 1))
        candles.append(
            Candle(
                open_time=int((close_dt - timedelta(minutes=15)).timestamp() * 1000),
                open_price=float(close),
                high_price=float(close),
                low_price=float(close),
                close_price=float(close),
                volume=1.0,
                close_time=int(close_dt.timestamp() * 1000),
                is_closed=True,
            )
        )
    return candles


class EmaCrossStrategyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.strategy = EmaCrossStrategy(fast_period=2, slow_period=3, interval="15m", stale_data_multiplier=2)

    def test_returns_hold_when_not_enough_data(self) -> None:
        signal = self.strategy.evaluate("BTCUSDT", build_candles([7, 7, 7, 8]), None)
        self.assertEqual(signal.action, "HOLD")
        self.assertEqual(signal.reason, "not-enough-data")

    def test_returns_buy_on_bullish_crossover(self) -> None:
        signal = self.strategy.evaluate("BTCUSDT", build_candles([7, 7, 7, 7, 7, 8]), None)
        self.assertEqual(signal.action, "BUY")
        self.assertEqual(signal.reason, "ema20-crossed-above-ema50")

    def test_returns_sell_on_bearish_crossover(self) -> None:
        signal = self.strategy.evaluate("BTCUSDT", build_candles([7, 7, 7, 7, 8, 7]), None)
        self.assertEqual(signal.action, "SELL")
        self.assertEqual(signal.reason, "ema20-crossed-below-ema50")

    def test_returns_hold_for_stale_market_data(self) -> None:
        signal = self.strategy.evaluate("BTCUSDT", build_candles([7, 7, 7, 7, 7, 8], latest_offset_minutes=31), None)
        self.assertEqual(signal.action, "HOLD")
        self.assertEqual(signal.reason, "stale-market-data")


if __name__ == "__main__":
    unittest.main()