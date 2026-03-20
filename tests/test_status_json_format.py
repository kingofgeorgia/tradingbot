from __future__ import annotations

# ruff: noqa: E402

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from binance_bot.core.models import BotState, StartupIssue
from binance_bot.services.status import build_runtime_status_report, runtime_status_report_to_dict
from tests.fakes import make_settings


class StatusJsonFormatTests(unittest.TestCase):
    def test_runtime_status_report_dict_uses_stable_top_level_keys(self) -> None:
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
        payload = runtime_status_report_to_dict(report)

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

    def test_symbol_status_entries_use_stable_keys(self) -> None:
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
            acknowledged_startup_issues=["BTCUSDT:quantity-mismatch:block-symbol"],
            last_manual_action_by_symbol={"BTCUSDT": "acknowledge"},
        )

        report = build_runtime_status_report(settings=settings, state=state)
        payload = runtime_status_report_to_dict(report)
        first_symbol = payload["symbol_statuses"][0]

        self.assertEqual(
            list(first_symbol.keys()),
            [
                "symbol",
                "category",
                "effective_runtime_mode",
                "has_open_position",
                "blocked",
                "suspect_position",
                "startup_issue_key",
                "issue_acknowledged",
                "last_manual_action",
                "reason",
            ],
        )
        self.assertEqual(first_symbol["symbol"], "BTCUSDT")
        self.assertEqual(first_symbol["category"], "blocked")
        self.assertEqual(first_symbol["issue_acknowledged"], True)

    def test_manual_review_queue_entries_use_stable_keys(self) -> None:
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
        payload = runtime_status_report_to_dict(report)
        first_item = payload["manual_review_queue"][0]

        self.assertEqual(
            list(first_item.keys()),
            [
                "queue_key",
                "symbol",
                "category",
                "priority",
                "startup_issue_key",
                "issue_acknowledged",
                "last_manual_action",
                "recommended_action",
                "reason",
            ],
        )
        self.assertEqual(first_item["symbol"], "BTCUSDT")
        self.assertEqual(first_item["category"], "startup-issue")


if __name__ == "__main__":
    unittest.main()