from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from binance_bot.core.models import BotState, Position
from binance_bot.core.state import StateStore


class StateStoreTests(unittest.TestCase):
    def test_load_returns_empty_state_when_file_does_not_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = StateStore(Path(tmp_dir) / "missing_state.json")
            state = store.load()

        self.assertEqual(state.open_positions, {})
        self.assertEqual(state.last_processed_candle, {})
        self.assertEqual(state.daily_realized_pnl, 0.0)

    def test_save_creates_state_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_file = Path(tmp_dir) / "state.json"
            store = StateStore(state_file)

            store.save(BotState())

            self.assertTrue(state_file.exists())

    def test_save_and_load_preserve_open_positions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_file = Path(tmp_dir) / "state.json"
            store = StateStore(state_file)
            original_state = BotState(
                open_positions={
                    "BTCUSDT": Position(
                        symbol="BTCUSDT",
                        quantity=0.125,
                        entry_price=100.0,
                        stop_loss=98.0,
                        take_profit=104.0,
                        opened_at="2026-03-19T00:00:00+00:00",
                        order_id=101,
                        mode="demo",
                        quote_spent=12.5,
                        fee_paid_quote=0.02,
                    )
                }
            )

            store.save(original_state)
            loaded_state = store.load()

        self.assertIn("BTCUSDT", loaded_state.open_positions)
        loaded_position = loaded_state.open_positions["BTCUSDT"]
        self.assertEqual(loaded_position.symbol, "BTCUSDT")
        self.assertAlmostEqual(loaded_position.quantity, 0.125)
        self.assertAlmostEqual(loaded_position.entry_price, 100.0)
        self.assertEqual(loaded_position.order_id, 101)

    def test_save_and_load_preserve_last_processed_candle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_file = Path(tmp_dir) / "state.json"
            store = StateStore(state_file)
            original_state = BotState(last_processed_candle={"BTCUSDT": 1742339700000})

            store.save(original_state)
            loaded_state = store.load()

        self.assertEqual(loaded_state.last_processed_candle["BTCUSDT"], 1742339700000)


if __name__ == "__main__":
    unittest.main()