from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class CliSmokeTests(unittest.TestCase):
    def run_smoke(self, scenario: str, *arguments: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temp_dir:
            env = os.environ.copy()
            env["CLI_SMOKE_SCENARIO"] = scenario
            env["CLI_SMOKE_TMP_DIR"] = temp_dir
            return subprocess.run(
                [sys.executable, "-m", "tests.cli_smoke_runner", *arguments],
                cwd=PROJECT_ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

    @staticmethod
    def parse_last_stdout_json(stdout: str) -> dict[str, object]:
        return json.loads(stdout.strip().splitlines()[-1])

    def test_inspect_command_smoke(self) -> None:
        result = self.run_smoke("inspect", "inspect")

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("Blocked symbols: BTCUSDT", result.stdout)

    def test_acknowledge_command_smoke(self) -> None:
        result = self.run_smoke("acknowledge", "acknowledge", "BTCUSDT")

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("Acknowledged startup issue for BTCUSDT.", result.stdout)

    def test_repair_restore_command_smoke(self) -> None:
        result = self.run_smoke("repair-restore", "repair", "BTCUSDT", "restore-from-exchange")

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("Applied manual repair for BTCUSDT: restore-from-exchange.", result.stdout)

    def test_repair_restore_dry_run_command_smoke(self) -> None:
        result = self.run_smoke("repair-restore-dry-run", "repair", "BTCUSDT", "restore-from-exchange", "--dry-run")

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = self.parse_last_stdout_json(result.stdout)
        self.assertEqual(payload["open_positions"], [])
        self.assertEqual(payload["startup_issue_keys"], ["BTCUSDT:exchange-position-without-local-state:block-symbol"])
        self.assertEqual(payload["repair_rows"], 0)
        self.assertEqual(payload["backups"], 0)
        self.assertEqual(payload["restore_calls"], ["BTCUSDT"])

    def test_repair_drop_command_smoke(self) -> None:
        result = self.run_smoke("repair-drop", "repair", "BTCUSDT", "drop-local-state")

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("Applied manual repair for BTCUSDT: drop-local-state.", result.stdout)

    def test_unblock_command_smoke_for_open_issue(self) -> None:
        result = self.run_smoke("unblock-open", "unblock", "BTCUSDT")

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("BTCUSDT: startup-issue-still-open", result.stdout)

    def test_unblock_command_smoke_for_resolved_issue(self) -> None:
        result = self.run_smoke("unblock-closed", "unblock", "BTCUSDT")

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("Unblocked BTCUSDT.", result.stdout)

    def test_unblock_dry_run_command_smoke_for_resolved_issue(self) -> None:
        result = self.run_smoke("unblock-closed-dry-run", "unblock", "BTCUSDT", "--dry-run")

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = self.parse_last_stdout_json(result.stdout)
        self.assertEqual(payload["blocked_symbols"], {"BTCUSDT": "resolved-manually"})
        self.assertEqual(payload["repair_rows"], 0)
        self.assertEqual(payload["backups"], 0)

    def test_startup_check_only_mode_smoke(self) -> None:
        result = self.run_smoke("runtime-startup-check-only")

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["runtime_mode"], "startup-check-only")
        self.assertEqual(payload["last_reconciliation_status"], "clean")
        self.assertEqual(len(payload["notifier_messages"]), 1)
        self.assertIn("Startup summary", payload["notifier_messages"][0])

    def test_observe_only_mode_smoke(self) -> None:
        result = self.run_smoke("runtime-observe-only")

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["runtime_mode"], "observe-only")
        self.assertEqual(payload["logged_signals"], ["BTCUSDT"])
        self.assertEqual(payload["close_calls"], [])
        self.assertEqual(payload["open_calls"], [])
        self.assertEqual(payload["open_positions"], ["BTCUSDT"])
        self.assertEqual(
            payload["last_processed_candle"],
            {"BTCUSDT": 1710000000000, "ETHUSDT": 1710000005000},
        )
        self.assertEqual(len(payload["notifier_messages"]), 2)
        self.assertIn("Startup summary", payload["notifier_messages"][0])
        self.assertIn("Runtime mode: observe-only", payload["notifier_messages"][1])

    def test_no_new_entries_mode_smoke(self) -> None:
        result = self.run_smoke("runtime-no-new-entries")

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["runtime_mode"], "no-new-entries")
        self.assertEqual(payload["logged_signals"], ["BTCUSDT"])
        self.assertEqual(payload["close_calls"], [])
        self.assertEqual(payload["open_calls"], [])
        self.assertEqual(payload["open_positions"], [])
        self.assertEqual(
            payload["last_processed_candle"],
            {"BTCUSDT": 1710000000000, "ETHUSDT": 1710000005000},
        )
        self.assertEqual(len(payload["notifier_messages"]), 2)
        self.assertIn("Startup summary", payload["notifier_messages"][0])
        self.assertIn("Runtime mode: no-new-entries", payload["notifier_messages"][1])