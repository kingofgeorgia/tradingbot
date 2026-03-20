from __future__ import annotations

# ruff: noqa: E402

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from binance_bot.config import load_settings


class ConfigTests(unittest.TestCase):
    def test_load_settings_parses_symbol_policy_overrides(self) -> None:
        env = {
            "APP_MODE": "demo",
            "BINANCE_API_KEY": "key",
            "BINANCE_SECRET_KEY": "secret",
            "SYMBOLS": "BTCUSDT,ETHUSDT",
            "TIMEFRAME": "15m",
            "SYMBOL_POLICY_OVERRIDES": (
                '{"BTCUSDT": {"runtime_mode": "observe-only", "risk_per_trade_pct": 0.02, "max_position_pct": 0.05}}'
            ),
        }

        with patch.dict(os.environ, env, clear=True):
            settings = load_settings()

        self.assertEqual(settings.get_effective_symbol_runtime_mode("BTCUSDT"), "observe-only")
        self.assertEqual(settings.get_effective_symbol_runtime_mode("ETHUSDT"), "trade")
        self.assertEqual(settings.get_symbol_risk_per_trade_pct("BTCUSDT"), 0.02)
        self.assertEqual(settings.get_symbol_max_position_pct("BTCUSDT"), 0.05)

    def test_load_settings_rejects_unknown_override_symbol(self) -> None:
        env = {
            "APP_MODE": "demo",
            "BINANCE_API_KEY": "key",
            "BINANCE_SECRET_KEY": "secret",
            "SYMBOLS": "BTCUSDT,ETHUSDT",
            "TIMEFRAME": "15m",
            "SYMBOL_POLICY_OVERRIDES": '{"SOLUSDT": {"runtime_mode": "observe-only"}}',
        }

        with patch.dict(os.environ, env, clear=True):
            with self.assertRaisesRegex(ValueError, "unknown symbol"):
                load_settings()


if __name__ == "__main__":
    unittest.main()