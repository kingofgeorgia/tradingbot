from __future__ import annotations

# ruff: noqa: E402

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from binance_bot.backtesting.harness import format_backtest_report_json, load_candles_from_csv, run_backtest
from binance_bot.strategy.ema_cross import EmaCrossStrategy
from tests.test_ema_cross import build_candles


class BacktestingHarnessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.strategy = EmaCrossStrategy(fast_period=2, slow_period=3, interval="15m", stale_data_multiplier=2)

    def test_backtest_uses_historical_reference_time_instead_of_runtime_freshness(self) -> None:
        candles = build_candles([7, 7, 7, 7, 7, 8, 8, 7], latest_offset_minutes=10_000)

        report = run_backtest(strategy=self.strategy, symbol="BTCUSDT", candles=candles, position_size_quote=1000.0)

        self.assertEqual(report.buy_signal_count, 1)
        self.assertEqual(report.sell_signal_count, 1)
        self.assertEqual(report.completed_trade_count, 1)
        self.assertAlmostEqual(report.total_pnl_quote, -125.0)
        self.assertIsNone(report.open_trade)

    def test_csv_loader_reads_candles_for_backtest(self) -> None:
        candles = build_candles([7, 7, 7, 7, 7, 8], latest_offset_minutes=10_000)
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "candles.csv"
            with csv_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "open_time",
                        "open_price",
                        "high_price",
                        "low_price",
                        "close_price",
                        "volume",
                        "close_time",
                        "is_closed",
                    ],
                )
                writer.writeheader()
                for candle in candles:
                    writer.writerow(
                        {
                            "open_time": candle.open_time,
                            "open_price": candle.open_price,
                            "high_price": candle.high_price,
                            "low_price": candle.low_price,
                            "close_price": candle.close_price,
                            "volume": candle.volume,
                            "close_time": candle.close_time,
                            "is_closed": "true",
                        }
                    )

            loaded = load_candles_from_csv(csv_path)

        self.assertEqual(len(loaded), len(candles))
        self.assertEqual(loaded[-1].close_price, 8.0)

    def test_backtest_json_output_uses_stable_keys(self) -> None:
        candles = build_candles([7, 7, 7, 7, 7, 8, 8, 7], latest_offset_minutes=10_000)

        report = run_backtest(strategy=self.strategy, symbol="BTCUSDT", candles=candles, position_size_quote=1000.0)
        payload = json.loads(format_backtest_report_json(report))

        self.assertEqual(
            list(payload.keys()),
            [
                "symbol",
                "candle_count",
                "actionable_signal_count",
                "buy_signal_count",
                "sell_signal_count",
                "completed_trade_count",
                "open_trade",
                "total_pnl_quote",
                "win_rate",
                "trades",
            ],
        )
        self.assertEqual(payload["trades"][0]["symbol"], "BTCUSDT")


if __name__ == "__main__":
    unittest.main()