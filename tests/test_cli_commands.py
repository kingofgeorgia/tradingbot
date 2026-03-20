from __future__ import annotations

# ruff: noqa: E402

import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import binance_bot.main as app_main
from binance_bot.core.models import BotState, ExchangePositionSnapshot, Position, StartupIssue
from tests.fakes import FakeBinanceClient, FakeJournal, FakeLoggers, FakeStateStore, make_settings


class FakeCliOrderManager:
    def __init__(self) -> None:
        self.restore_calls: list[str] = []
        self.drop_calls: list[str] = []

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
        self.restore_calls.append(snapshot.symbol)

    def drop_local_position(self, symbol: str, state: BotState) -> None:
        state.open_positions.pop(symbol, None)
        state.suspect_positions.pop(symbol, None)
        self.drop_calls.append(symbol)


class CliCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.settings = make_settings()
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
        self.client.position_snapshots["ETHUSDT"] = ExchangePositionSnapshot(
            symbol="ETHUSDT",
            base_asset="ETH",
            exchange_quantity=0.0,
            average_entry_price=None,
            last_order_id=None,
            last_trade_time=None,
            has_open_orders=False,
            has_recent_trades=False,
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
        self.order_manager = FakeCliOrderManager()
        self.runtime = SimpleNamespace(
            settings=self.settings,
            client=self.client,
            state_store=self.state_store,
            repair_journal=self.repair_journal,
            loggers=self.loggers,
            order_manager=self.order_manager,
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def run_command(self, *arguments: str) -> str:
        buffer = StringIO()
        with patch("binance_bot.main.build_runtime", return_value=self.runtime):
            with redirect_stdout(buffer):
                app_main.run(list(arguments))
        return buffer.getvalue().strip()

    def test_inspect_command_outputs_runtime_status(self) -> None:
        output = self.run_command("inspect")

        self.assertIn("Blocked symbols: BTCUSDT", output)
        self.assertIn("Startup issues: BTCUSDT:exchange-position-without-local-state:block-symbol", output)

    def test_acknowledge_command_updates_issue_state(self) -> None:
        output = self.run_command("acknowledge", "BTCUSDT")

        self.assertIn("Acknowledged startup issue for BTCUSDT.", output)
        self.assertEqual(len(self.state.acknowledged_startup_issues), 1)
        self.assertEqual(self.state.last_manual_action_by_symbol["BTCUSDT"], "acknowledge")

    def test_repair_restore_from_exchange_command_restores_position(self) -> None:
        output = self.run_command("repair", "BTCUSDT", "restore-from-exchange")

        self.assertIn("Applied manual repair for BTCUSDT: restore-from-exchange.", output)
        self.assertIn("BTCUSDT", self.state.open_positions)
        self.assertEqual(self.state.startup_issues, [])
        self.assertEqual(self.order_manager.restore_calls, ["BTCUSDT"])

    def test_repair_drop_local_state_command_drops_position(self) -> None:
        self.state.open_positions["BTCUSDT"] = Position(
            symbol="BTCUSDT",
            quantity=0.25,
            entry_price=100.0,
            stop_loss=98.0,
            take_profit=104.0,
            opened_at="2026-03-20T10:00:00+00:00",
            order_id=1001,
            mode="demo",
            quote_spent=25.0,
            fee_paid_quote=0.1,
        )
        self.client.position_snapshots["BTCUSDT"] = ExchangePositionSnapshot(
            symbol="BTCUSDT",
            base_asset="BTC",
            exchange_quantity=0.0,
            average_entry_price=None,
            last_order_id=None,
            last_trade_time=None,
            has_open_orders=False,
            has_recent_trades=False,
            step_size=0.001,
        )
        self.state.startup_issues = [
            StartupIssue(
                symbol="BTCUSDT",
                issue_type="local-position-missing-on-exchange",
                local_qty=0.25,
                exchange_qty=0.0,
                action="mark-unrecoverable",
                status="open",
                message="needs drop",
            )
        ]

        output = self.run_command("repair", "BTCUSDT", "drop-local-state")

        self.assertIn("Applied manual repair for BTCUSDT: drop-local-state.", output)
        self.assertNotIn("BTCUSDT", self.state.open_positions)
        self.assertEqual(self.state.startup_issues, [])
        self.assertEqual(self.order_manager.drop_calls, ["BTCUSDT"])

    def test_unblock_command_denies_when_issue_still_open(self) -> None:
        output = self.run_command("unblock", "BTCUSDT")

        self.assertIn("BTCUSDT: startup-issue-still-open", output)
        self.assertIn("BTCUSDT", self.state.blocked_symbols)

    def test_unblock_command_allows_when_issue_is_resolved(self) -> None:
        self.state.startup_issues = []
        self.state.suspect_positions = {}
        self.client.position_snapshots["BTCUSDT"] = ExchangePositionSnapshot(
            symbol="BTCUSDT",
            base_asset="BTC",
            exchange_quantity=0.0,
            average_entry_price=None,
            last_order_id=None,
            last_trade_time=None,
            has_open_orders=False,
            has_recent_trades=False,
            step_size=0.001,
        )

        output = self.run_command("unblock", "BTCUSDT")

        self.assertIn("Unblocked BTCUSDT.", output)
        self.assertNotIn("BTCUSDT", self.state.blocked_symbols)
        self.assertEqual(self.state.last_manual_action_by_symbol["BTCUSDT"], "unblock")


if __name__ == "__main__":
    unittest.main()