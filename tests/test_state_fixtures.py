from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from binance_bot.core.models import BotState


class StateFixturesTests(unittest.TestCase):
    def test_legacy_state_fixture_is_backward_compatible(self) -> None:
        fixture_path = PROJECT_ROOT / "tests" / "fixtures" / "legacy_state.json"
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))

        state = BotState.from_dict(payload)

        self.assertEqual(state.schema_version, 1)
        self.assertEqual(state.blocked_symbols, {})
        self.assertEqual(state.startup_issues, [])
        self.assertEqual(state.repair_history, [])

    def test_blocked_state_fixture_preserves_runtime_safety_fields(self) -> None:
        fixture_path = PROJECT_ROOT / "tests" / "fixtures" / "blocked_state.json"
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))

        state = BotState.from_dict(payload)

        self.assertEqual(state.schema_version, 1)
        self.assertIn("BTCUSDT", state.blocked_symbols)
        self.assertEqual(state.startup_issues[0].issue_type, "quantity-mismatch")
        self.assertEqual(state.alerted_startup_issues, ["BTCUSDT:quantity-mismatch:block-symbol"])


if __name__ == "__main__":
    unittest.main()