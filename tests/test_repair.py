from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from binance_bot.core.models import BotState, ExchangePositionSnapshot, Position, StartupIssue
from binance_bot.services.repair import acknowledge_issue, inspect_runtime_issues, repair_symbol_state, unblock_symbol
from tests.fakes import FakeBinanceClient, FakeJournal, FakeLoggers, FakeStateStore, make_settings


class FakeOrderManager:
    def restore_position_from_exchange(self, snapshot: ExchangePositionSnapshot, state: BotState) -> None:
        state.open_positions[snapshot.symbol] = Position(
            symbol=snapshot.symbol,
            quantity=snapshot.exchange_quantity,
            entry_price=snapshot.average_entry_price or 0.0,
            stop_loss=98.0,
            take_profit=104.0,
            opened_at="2026-03-20T10:00:00+00:00",
            order_id=snapshot.last_order_id or 0,
            mode="demo",
            quote_spent=(snapshot.average_entry_price or 0.0) * snapshot.exchange_quantity,
            fee_paid_quote=0.0,
        )

    def drop_local_position(self, symbol: str, state: BotState) -> None:
        state.open_positions.pop(symbol, None)


class RepairFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = make_settings()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.settings.data_dir = Path(self.temp_dir.name)
        self.client = FakeBinanceClient()
        self.client.position_snapshots["BTCUSDT"] = ExchangePositionSnapshot(
            symbol="BTCUSDT",
            base_asset="BTC",
            exchange_quantity=0.25,
            average_entry_price=100.0,
            last_order_id=1001,
            last_trade_time=1710000000000,
            has_open_orders=False,
            has_recent_trades=True,
            step_size=0.001,
        )
        self.state = BotState(
            blocked_symbols={"BTCUSDT": "exchange-position-without-local-state"},
            startup_issues=[
                StartupIssue(
                    symbol="BTCUSDT",
                    issue_type="exchange-position-without-local-state",
                    local_qty=0.0,
                    exchange_qty=0.25,
                    action="block-symbol",
                    status="open",
                    message="needs review",
                )
            ],
        )
        self.state_store = FakeStateStore(self.state)
        self.repair_journal = FakeJournal()
        self.loggers = FakeLoggers()
        self.order_manager = FakeOrderManager()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_acknowledge_issue_records_review(self) -> None:
        message = acknowledge_issue(
            symbol="BTCUSDT",
            state=self.state,
            state_store=self.state_store,
            repair_journal=self.repair_journal,
            loggers=self.loggers,
            settings=self.settings,
        )

        self.assertIn("Acknowledged", message)
        self.assertEqual(len(self.state.acknowledged_startup_issues), 1)
        self.assertEqual(self.state.last_manual_action_by_symbol["BTCUSDT"], "acknowledge")

    def test_inspect_runtime_issues_includes_per_symbol_runtime_categories(self) -> None:
        self.state.suspect_positions = {"BTCUSDT": "exchange-position-without-local-state"}
        self.state.last_manual_action_by_symbol["BTCUSDT"] = "acknowledge"
        self.state.acknowledged_startup_issues = [self.state.startup_issues[0].issue_key]

        report = inspect_runtime_issues(
            settings=self.settings,
            client=self.client,
            state=self.state,
        )

        self.assertIn("Per-symbol status:", report)
        self.assertIn("BTCUSDT: category=blocked", report)
        self.assertIn("issue=BTCUSDT:exchange-position-without-local-state:block-symbol", report)
        self.assertIn("acknowledged=yes", report)
        self.assertIn("last_manual_action=acknowledge", report)

    def test_restore_from_exchange_clears_issue_and_restores_position(self) -> None:
        message = repair_symbol_state(
            settings=self.settings,
            client=self.client,
            state=self.state,
            state_store=self.state_store,
            order_manager=self.order_manager,
            repair_journal=self.repair_journal,
            loggers=self.loggers,
            symbol="BTCUSDT",
            action="restore-from-exchange",
        )

        self.assertIn("Applied manual repair", message)
        self.assertIn("BTCUSDT", self.state.open_positions)
        self.assertEqual(self.state.startup_issues, [])
        backup_files = list(self.settings.state_backups_dir.glob("*.json"))
        self.assertEqual(len(backup_files), 1)
        backup_payload = json.loads(backup_files[0].read_text(encoding="utf-8"))
        self.assertIn("BTCUSDT", backup_payload["blocked_symbols"])

    def test_unblock_denied_while_issue_still_open(self) -> None:
        message = unblock_symbol(
            settings=self.settings,
            client=self.client,
            state=self.state,
            state_store=self.state_store,
            repair_journal=self.repair_journal,
            loggers=self.loggers,
            symbol="BTCUSDT",
        )

        self.assertIn("startup-issue-still-open", message)
        self.assertEqual(list(self.settings.state_backups_dir.glob("*.json")), [])

    def test_unblock_allowed_after_issue_resolution(self) -> None:
        self.state.startup_issues = []
        self.state.suspect_positions = {}

        message = unblock_symbol(
            settings=self.settings,
            client=self.client,
            state=self.state,
            state_store=self.state_store,
            repair_journal=self.repair_journal,
            loggers=self.loggers,
            symbol="BTCUSDT",
        )

        self.assertIn("Unblocked", message)
        self.assertNotIn("BTCUSDT", self.state.blocked_symbols)
        backup_files = list(self.settings.state_backups_dir.glob("*.json"))
        self.assertEqual(len(backup_files), 1)


if __name__ == "__main__":
    unittest.main()