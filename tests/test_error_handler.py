from __future__ import annotations

# ruff: noqa: E402

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from binance_bot.clients.binance_client import BinanceAPIError
from binance_bot.core.errors import classify_runtime_error
from binance_bot.core.models import BotState
from binance_bot.services.error_handler import record_api_error
from tests.fakes import FakeJournal, FakeLoggers, FakeNotifier, FakeStateStore, make_settings


class ErrorHandlingPolicyTests(unittest.TestCase):
    def test_runtime_io_warning_does_not_notify_operator(self) -> None:
        errors_journal = FakeJournal()
        notifier = FakeNotifier()
        loggers = FakeLoggers()

        descriptor = record_api_error(
            errors_journal,
            notifier,
            loggers,
            "demo",
            "market-data",
            "BTCUSDT",
            BinanceAPIError("klines failed"),
        )

        self.assertEqual(descriptor.category, "runtime-io")
        self.assertEqual(descriptor.reaction, "continue-cycle")
        self.assertEqual(notifier.messages, [])
        self.assertIn("warning/runtime-io", errors_journal.rows[0]["message"])

    def test_execution_error_notifies_operator_with_reaction(self) -> None:
        errors_journal = FakeJournal()
        notifier = FakeNotifier()
        loggers = FakeLoggers()
        settings = make_settings()
        state = BotState()
        state_store = FakeStateStore(state)

        descriptor = record_api_error(
            errors_journal,
            notifier,
            loggers,
            "demo",
            "open-position",
            "BTCUSDT",
            BinanceAPIError("order rejected"),
            settings=settings,
            state=state,
            state_store=state_store,
        )

        self.assertEqual(descriptor.category, "execution")
        self.assertEqual(descriptor.reaction, "manual-review")
        self.assertEqual(len(notifier.messages), 1)
        self.assertIn("Reaction: manual-review", notifier.messages[0])

    def test_execution_error_respects_alert_cooldown(self) -> None:
        errors_journal = FakeJournal()
        notifier = FakeNotifier()
        loggers = FakeLoggers()
        settings = make_settings()
        state = BotState()
        state_store = FakeStateStore(state)

        record_api_error(
            errors_journal,
            notifier,
            loggers,
            "demo",
            "open-position",
            "BTCUSDT",
            BinanceAPIError("order rejected"),
            settings=settings,
            state=state,
            state_store=state_store,
        )
        record_api_error(
            errors_journal,
            notifier,
            loggers,
            "demo",
            "open-position",
            "BTCUSDT",
            BinanceAPIError("order rejected"),
            settings=settings,
            state=state,
            state_store=state_store,
        )

        self.assertEqual(len(notifier.messages), 1)
        self.assertIn("runtime-error:open-position:BTCUSDT:execution", state.alert_cooldowns)

    def test_timeout_is_classified_as_transient_without_operator_alert(self) -> None:
        descriptor = classify_runtime_error(scope="market-data", exc=TimeoutError("request timeout"))

        self.assertEqual(descriptor.category, "transient-network")
        self.assertEqual(descriptor.reaction, "continue-cycle")
        self.assertFalse(descriptor.notify_operator)


if __name__ == "__main__":
    unittest.main()