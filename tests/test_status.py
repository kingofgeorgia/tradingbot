from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from binance_bot.core.models import BotState, StartupIssue
from binance_bot.services.status import (
    build_runtime_status_report,
    format_runtime_health_notification,
    format_status_report_json,
    format_startup_summary_notification,
    format_status_report,
)
from tests.fakes import make_settings


class StatusTests(unittest.TestCase):
    def test_status_report_includes_blocked_symbols_and_issues(self) -> None:
        settings = make_settings()
        settings.runtime_mode = "no-new-entries"
        settings.symbol_policy_overrides = {
            "BTCUSDT": type("Override", (), {"runtime_mode": "observe-only", "risk_per_trade_pct": None, "max_position_pct": None})()
        }
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
            last_manual_action_by_symbol={"BTCUSDT": "acknowledge"},
            acknowledged_startup_issues=["BTCUSDT:quantity-mismatch:block-symbol"],
        )

        report = build_runtime_status_report(settings=settings, state=state)
        text = format_status_report(report)

        self.assertIn("Runtime mode: no-new-entries", text)
        self.assertIn("Blocked symbols: BTCUSDT", text)
        self.assertIn("BTCUSDT:quantity-mismatch:block-symbol", text)
        self.assertIn("Manual review queue size: 1", text)
        self.assertIn("recommended_action=inspect", text)
        self.assertIn("Per-symbol status:", text)
        self.assertIn("BTCUSDT: category=blocked; effective_mode=observe-only", text)
        self.assertIn("acknowledged=yes", text)
        self.assertIn("last_manual_action=acknowledge", text)
        self.assertIn("ETHUSDT: category=ready; effective_mode=no-new-entries", text)

    def test_runtime_health_notification_includes_blocked_symbols_and_cycle(self) -> None:
        settings = make_settings()
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
        )

        report = build_runtime_status_report(settings=settings, state=state)
        text = format_runtime_health_notification(app_mode=settings.app_mode, report=report, cycle_number=3)

        self.assertIn("[demo] Runtime heartbeat", text)
        self.assertIn("Cycle: 3", text)
        self.assertIn("Blocked symbols: BTCUSDT", text)
        self.assertIn("Startup issues: BTCUSDT:quantity-mismatch:block-symbol", text)

    def test_startup_summary_notification_includes_suspect_positions(self) -> None:
        settings = make_settings()
        state = BotState(
            blocked_symbols={"BTCUSDT": "quantity-mismatch"},
            suspect_positions={"BTCUSDT": "quantity-mismatch"},
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

        report = build_runtime_status_report(settings=settings, state=state)
        text = format_startup_summary_notification(app_mode=settings.app_mode, report=report)

        self.assertIn("[demo] Startup summary", text)
        self.assertIn("Blocked symbols: BTCUSDT", text)
        self.assertIn("Suspect positions: BTCUSDT", text)
        self.assertIn("Last reconciliation status: blocked-symbols-present", text)

    def test_status_report_json_uses_stable_keys(self) -> None:
        settings = make_settings()
        state = BotState(
            blocked_symbols={"BTCUSDT": "quantity-mismatch"},
            suspect_positions={"BTCUSDT": "quantity-mismatch"},
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
            last_manual_action_by_symbol={"BTCUSDT": "acknowledge"},
            acknowledged_startup_issues=["BTCUSDT:quantity-mismatch:block-symbol"],
        )

        report = build_runtime_status_report(settings=settings, state=state)
        payload = json.loads(format_status_report_json(report))

        self.assertEqual(
            list(payload.keys()),
            [
                "runtime_mode",
                "open_positions",
                "blocked_symbols",
                "suspect_positions",
                "startup_issue_keys",
                "symbol_statuses",
                "last_reconciled_at",
                "last_reconciliation_status",
                "last_manual_review_at",
                "manual_review_queue",
            ],
        )
        self.assertEqual(payload["symbol_statuses"][0]["symbol"], "BTCUSDT")
        self.assertEqual(payload["symbol_statuses"][0]["category"], "blocked")
        self.assertEqual(payload["symbol_statuses"][0]["issue_acknowledged"], True)
        self.assertEqual(payload["manual_review_queue"][0]["symbol"], "BTCUSDT")
        self.assertEqual(payload["manual_review_queue"][0]["recommended_action"], "inspect")


if __name__ == "__main__":
    unittest.main()