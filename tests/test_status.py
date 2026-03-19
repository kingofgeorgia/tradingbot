from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from binance_bot.core.models import BotState, StartupIssue
from binance_bot.services.status import build_runtime_status_report, format_status_report
from tests.fakes import make_settings


class StatusTests(unittest.TestCase):
    def test_status_report_includes_blocked_symbols_and_issues(self) -> None:
        settings = make_settings()
        settings.runtime_mode = "no-new-entries"
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
        text = format_status_report(report)

        self.assertIn("Runtime mode: no-new-entries", text)
        self.assertIn("Blocked symbols: BTCUSDT", text)
        self.assertIn("BTCUSDT:quantity-mismatch:block-symbol", text)


if __name__ == "__main__":
    unittest.main()