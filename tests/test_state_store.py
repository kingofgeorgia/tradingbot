from __future__ import annotations

import sys
import tempfile
import unittest
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from binance_bot.core.models import BotState, Position
from binance_bot.core.state import StateStore


class StateStoreTests(unittest.TestCase):
    def test_load_returns_empty_state_when_file_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_file = Path(tmp_dir) / "state.json"
            store = StateStore(state_file)

            state = store.load()

            self.assertEqual(state.to_dict(), BotState().to_dict())

    def test_save_and_load_roundtrip_preserves_nested_position_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_file = Path(tmp_dir) / "nested" / "state.json"
            store = StateStore(state_file)
            original_state = BotState(
                trading_day="2026-03-19",
                day_start_equity=1500.0,
                daily_realized_pnl=12.5,
                consecutive_losses=1,
                open_positions={
                    "BTCUSDT": Position(
                        symbol="BTCUSDT",
                        quantity=0.125,
                        entry_price=100000.0,
                        stop_loss=98000.0,
                        take_profit=104000.0,
                        opened_at="2026-03-19T12:00:00+00:00",
                        order_id=123,
                        mode="demo",
                        quote_spent=12500.0,
                        fee_paid_quote=5.0,
                    )
                },
                halted_until_day="2026-03-19",
                total_closed_trades=7,
                last_processed_candle={"BTCUSDT": 1710000000000},
            )

            store.save(original_state)
            loaded_state = store.load()

            self.assertEqual(loaded_state.to_dict(), original_state.to_dict())

    def test_load_old_state_without_reconciliation_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_file = Path(tmp_dir) / "state.json"
            state_file.write_text(
                json.dumps(
                    {
                        "trading_day": "2026-03-19",
                        "day_start_equity": 1500.0,
                        "daily_realized_pnl": 0.0,
                        "consecutive_losses": 0,
                        "open_positions": {},
                        "halted_until_day": None,
                        "total_closed_trades": 0,
                        "last_processed_candle": {},
                    }
                ),
                encoding="utf-8",
            )
            store = StateStore(state_file)

            state = store.load()

            self.assertEqual(state.blocked_symbols, {})
            self.assertEqual(state.suspect_positions, {})
            self.assertEqual(state.startup_issues, [])
            self.assertIsNone(state.last_reconciled_at)
            self.assertIsNone(state.last_reconciliation_status)


if __name__ == "__main__":
    unittest.main()
