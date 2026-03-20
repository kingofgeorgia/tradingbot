from __future__ import annotations

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