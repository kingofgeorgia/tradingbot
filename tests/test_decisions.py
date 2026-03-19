from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from binance_bot.core.decisions import decide_position_close, decide_risk_entry, decide_signal_action


class DecisionTests(unittest.TestCase):
    def test_decide_risk_entry_allowed(self) -> None:
        decision = decide_risk_entry(True, "allowed")

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.reason, "allowed")

    def test_decide_risk_entry_denied(self) -> None:
        decision = decide_risk_entry(False, "trading-halted-for-the-day")

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "trading-halted-for-the-day")

    def test_decide_position_close_stop_loss_threshold(self) -> None:
        decision = decide_position_close(current_price=98.0, stop_loss=98.0, take_profit=104.0)

        self.assertTrue(decision.should_close)
        self.assertEqual(decision.reason, "stop-loss-hit")
        self.assertEqual(decision.error_scope, "stop-loss-close")

    def test_decide_position_close_stop_loss_below_threshold(self) -> None:
        decision = decide_position_close(current_price=97.5, stop_loss=98.0, take_profit=104.0)

        self.assertTrue(decision.should_close)
        self.assertEqual(decision.reason, "stop-loss-hit")

    def test_decide_position_close_take_profit_threshold(self) -> None:
        decision = decide_position_close(current_price=104.0, stop_loss=98.0, take_profit=104.0)

        self.assertTrue(decision.should_close)
        self.assertEqual(decision.reason, "take-profit-hit")
        self.assertEqual(decision.error_scope, "take-profit-close")

    def test_decide_position_close_take_profit_above_threshold(self) -> None:
        decision = decide_position_close(current_price=105.0, stop_loss=98.0, take_profit=104.0)

        self.assertTrue(decision.should_close)
        self.assertEqual(decision.reason, "take-profit-hit")

    def test_decide_position_close_no_close_condition(self) -> None:
        decision = decide_position_close(current_price=100.0, stop_loss=98.0, take_profit=104.0)

        self.assertFalse(decision.should_close)
        self.assertEqual(decision.reason, "no-close-condition")
        self.assertIsNone(decision.error_scope)

    def test_decide_signal_action_hold(self) -> None:
        decision = decide_signal_action("HOLD", "no-crossover", has_open_position=False)

        self.assertEqual(decision.action, "ignore")
        self.assertFalse(decision.should_log_signal)
        self.assertEqual(decision.reason, "hold-signal")

    def test_decide_signal_action_buy(self) -> None:
        decision = decide_signal_action("BUY", "ema20-crossed-above-ema50", has_open_position=False)

        self.assertEqual(decision.action, "evaluate-buy")
        self.assertTrue(decision.should_log_signal)
        self.assertEqual(decision.reason, "ema20-crossed-above-ema50")

    def test_decide_signal_action_sell_with_open_position(self) -> None:
        decision = decide_signal_action("SELL", "ema20-crossed-below-ema50", has_open_position=True)

        self.assertEqual(decision.action, "close-position")
        self.assertTrue(decision.should_log_signal)
        self.assertEqual(decision.reason, "ema20-crossed-below-ema50")

    def test_decide_signal_action_sell_without_open_position(self) -> None:
        decision = decide_signal_action("SELL", "ema20-crossed-below-ema50", has_open_position=False)

        self.assertEqual(decision.action, "ignore")
        self.assertTrue(decision.should_log_signal)
        self.assertEqual(decision.reason, "sell-without-open-position")

    def test_decide_signal_action_unsupported(self) -> None:
        decision = decide_signal_action("EXIT", "unsupported", has_open_position=False)

        self.assertEqual(decision.action, "ignore")
        self.assertFalse(decision.should_log_signal)
        self.assertEqual(decision.reason, "unsupported-signal-action")


if __name__ == "__main__":
    unittest.main()