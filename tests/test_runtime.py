from __future__ import annotations

# ruff: noqa: E402

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from binance_bot.core.models import BotState, StartupIssue
from binance_bot.services.runtime import run_loop
from tests.fakes import FakeJournal, FakeLoggers, FakeNotifier, FakeStateStore, make_settings


class RuntimeHeartbeatTests(unittest.TestCase):
    def make_runtime(self):
        settings = make_settings()
        settings.run_once = True
        state = BotState(
            blocked_symbols={"BTCUSDT": "quantity-mismatch"},
            startup_issues=[
                StartupIssue(
                    symbol="BTCUSDT",
                    issue_type="quantity-mismatch",
                    local_qty=0.25,
                    exchange_qty=0.20,
                    action="block-symbol",
                    status="open",
                    message="qty mismatch",
                )
            ],
            last_reconciliation_status="blocked-symbols-present",
        )
        return SimpleNamespace(
            settings=settings,
            loggers=FakeLoggers(),
            notifier=FakeNotifier(),
            state_store=FakeStateStore(state),
            client=object(),
            strategy=object(),
            risk_manager=object(),
            order_manager=object(),
            errors_journal=FakeJournal(),
        )

    def test_run_loop_sends_heartbeat_when_interval_reached(self) -> None:
        runtime = self.make_runtime()
        runtime.settings.heartbeat_interval_cycles = 1

        with patch("binance_bot.services.runtime.process_cycle", return_value=None):
            run_loop(runtime)

        self.assertEqual(len(runtime.notifier.messages), 2)
        self.assertIn("Bot started", runtime.notifier.messages[0])
        self.assertIn("Runtime heartbeat", runtime.notifier.messages[1])
        self.assertIn("Blocked symbols: BTCUSDT", runtime.notifier.messages[1])

    def test_run_loop_skips_heartbeat_when_disabled(self) -> None:
        runtime = self.make_runtime()
        runtime.settings.heartbeat_interval_cycles = 0

        with patch("binance_bot.services.runtime.process_cycle", return_value=None):
            run_loop(runtime)

        self.assertEqual(len(runtime.notifier.messages), 1)
        self.assertIn("Bot started", runtime.notifier.messages[0])