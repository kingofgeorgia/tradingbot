from __future__ import annotations

# ruff: noqa: E402

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from binance_bot.core.models import Position

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from binance_bot.core.exchange import ExchangeRuntimePort
from binance_bot.core.models import BotState, ExchangePositionSnapshot, StartupIssue
from binance_bot.core.state import StateStore
from binance_bot.services.runtime import ensure_runtime_state_file, reconcile_startup, run_loop
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
            client=self.make_exchange_port_stub(),
            strategy=object(),
            risk_manager=object(),
            order_manager=object(),
            errors_journal=FakeJournal(),
        )

    @staticmethod
    def make_exchange_port_stub() -> ExchangeRuntimePort:
        return SimpleNamespace(sync_time=lambda: None)

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

    def test_run_loop_sends_fatal_notification_with_policy_metadata(self) -> None:
        runtime = self.make_runtime()

        with self.assertRaisesRegex(RuntimeError, "fatal loop"):
            with patch("binance_bot.services.runtime.process_cycle", side_effect=RuntimeError("fatal loop")):
                run_loop(runtime)

        self.assertEqual(len(runtime.notifier.messages), 2)
        self.assertIn("Reaction: terminate-process", runtime.notifier.messages[1])
        self.assertEqual(runtime.errors_journal.rows[0]["scope"], "main-loop")


class StartupSummaryNotificationTests(unittest.TestCase):
    @staticmethod
    def make_runtime_with_state(state: BotState, client) -> SimpleNamespace:
        settings = make_settings()
        return SimpleNamespace(
            settings=settings,
            loggers=FakeLoggers(),
            notifier=FakeNotifier(),
            state_store=FakeStateStore(state),
            client=client,
            strategy=object(),
            risk_manager=object(),
            order_manager=SimpleNamespace(
                restore_position_from_exchange=lambda snapshot, runtime_state: runtime_state.open_positions.update(
                    {
                        snapshot.symbol: Position(
                            symbol=snapshot.symbol,
                            quantity=snapshot.exchange_quantity,
                            entry_price=snapshot.average_entry_price or 0.0,
                            stop_loss=(snapshot.average_entry_price or 0.0) * 0.98,
                            take_profit=(snapshot.average_entry_price or 0.0) * 1.04,
                            opened_at="2026-03-20T10:00:00+00:00",
                            order_id=snapshot.last_order_id or 0,
                            mode="demo",
                            quote_spent=(snapshot.average_entry_price or 0.0) * snapshot.exchange_quantity,
                            fee_paid_quote=0.0,
                        )
                    }
                ),
                mark_position_unrecoverable=lambda symbol, reason, runtime_state: None,
            ),
            reconciliation_journal=FakeJournal(),
            errors_journal=FakeJournal(),
            repair_journal=FakeJournal(),
        )

    def test_reconcile_startup_sends_clean_summary(self) -> None:
        state = BotState()
        client = SimpleNamespace(
            get_position_snapshot=lambda symbol, quote_asset: ExchangePositionSnapshot(
                symbol=symbol,
                base_asset=symbol[: -len(quote_asset)],
                exchange_quantity=0.0,
                average_entry_price=None,
                last_order_id=None,
                last_trade_time=None,
                has_open_orders=False,
                has_recent_trades=False,
                step_size=0.001,
            )
        )
        runtime = self.make_runtime_with_state(state, client)

        reconcile_startup(runtime)

        self.assertEqual(len(runtime.notifier.messages), 1)
        self.assertIn("Startup summary", runtime.notifier.messages[0])
        self.assertIn("Last reconciliation status: clean", runtime.notifier.messages[0])

    def test_reconcile_startup_sends_issue_alerts_and_summary(self) -> None:
        state = BotState(
            open_positions={
                "BTCUSDT": Position(
                    symbol="BTCUSDT",
                    quantity=0.25,
                    entry_price=100.0,
                    stop_loss=98.0,
                    take_profit=104.0,
                    opened_at="2026-03-20T10:00:00+00:00",
                    order_id=1,
                    mode="demo",
                    quote_spent=25.0,
                    fee_paid_quote=0.1,
                )
            }
        )

        def get_position_snapshot(symbol: str, quote_asset: str) -> ExchangePositionSnapshot:
            if symbol == "BTCUSDT":
                return ExchangePositionSnapshot(
                    symbol=symbol,
                    base_asset="BTC",
                    exchange_quantity=0.0,
                    average_entry_price=None,
                    last_order_id=None,
                    last_trade_time=None,
                    has_open_orders=False,
                    has_recent_trades=False,
                    step_size=0.001,
                )
            return ExchangePositionSnapshot(
                symbol=symbol,
                base_asset="ETH",
                exchange_quantity=0.0,
                average_entry_price=None,
                last_order_id=None,
                last_trade_time=None,
                has_open_orders=False,
                has_recent_trades=False,
                step_size=0.001,
            )

        runtime = self.make_runtime_with_state(state, SimpleNamespace(get_position_snapshot=get_position_snapshot))

        reconcile_startup(runtime)

        self.assertEqual(len(runtime.notifier.messages), 2)
        self.assertIn("Startup mismatch for BTCUSDT", runtime.notifier.messages[0])
        self.assertIn("Startup summary", runtime.notifier.messages[1])
        self.assertIn("Blocked symbols: BTCUSDT", runtime.notifier.messages[1])


class StateRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.settings = make_settings()
        self.settings.data_dir = Path(self.temp_dir.name)
        self.store = StateStore(self.settings.state_file)
        self.repair_journal = FakeJournal()
        self.notifier = FakeNotifier()
        self.loggers = FakeLoggers()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_ensure_runtime_state_file_recovers_invalid_json(self) -> None:
        self.settings.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.settings.state_file.write_text('{"broken": ', encoding="utf-8")

        ensure_runtime_state_file(
            settings=self.settings,
            state_store=self.store,
            repair_journal=self.repair_journal,
            notifier=self.notifier,
            loggers=self.loggers,
        )

        recovered_state = self.store.load()
        expected_state = BotState()
        expected_state.alert_cooldowns = recovered_state.alert_cooldowns
        expected_state.repair_history = recovered_state.repair_history

        self.assertEqual(recovered_state.to_dict(), expected_state.to_dict())
        self.assertEqual(len(self.repair_journal.rows), 1)
        self.assertEqual(self.repair_journal.rows[0]["action"], "recover-state-file")
        self.assertEqual(len(self.notifier.messages), 1)
        self.assertIn("State file recovery applied", self.notifier.messages[0])

        backup_files = list(self.settings.state_backups_dir.glob("*__runtime__state-load-recovery.json"))
        self.assertEqual(len(backup_files), 1)
        self.assertEqual(backup_files[0].read_text(encoding="utf-8"), '{"broken": ')
        self.assertEqual(len(recovered_state.repair_history), 1)

    def test_ensure_runtime_state_file_recovers_future_schema_payload(self) -> None:
        self.settings.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.settings.state_file.write_text('{"schema_version": 999, "open_positions": {}}', encoding="utf-8")

        ensure_runtime_state_file(
            settings=self.settings,
            state_store=self.store,
            repair_journal=self.repair_journal,
            notifier=self.notifier,
            loggers=self.loggers,
        )

        self.assertEqual(self.store.load().schema_version, 1)
        self.assertIn("Unsupported state schema_version", self.notifier.messages[0])