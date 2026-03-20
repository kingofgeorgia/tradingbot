from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from binance_bot.clients.binance_client import BinanceAPIError
from binance_bot.config import SymbolPolicyOverride
from binance_bot.core.models import BotState, Position
from binance_bot.services.position_monitor import manage_open_positions
from tests.fakes import FakeBinanceClient, FakeJournal, FakeLoggers, FakeNotifier, FakeStateStore, make_settings


class FakeOrderManager:
    def __init__(self) -> None:
        self.close_calls: list[tuple[str, str, BotState]] = []
        self.raise_close_error: dict[str, Exception] = {}

    def close_position(self, symbol: str, reason: str, state: BotState) -> None:
        self.close_calls.append((symbol, reason, state))
        if symbol in self.raise_close_error:
            raise self.raise_close_error[symbol]


class PositionMonitorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = make_settings()
        self.client = FakeBinanceClient()
        self.state = BotState(
            open_positions={
                "BTCUSDT": Position(
                    symbol="BTCUSDT",
                    quantity=0.25,
                    entry_price=100.0,
                    stop_loss=98.0,
                    take_profit=104.0,
                    opened_at="2026-03-19T12:00:00+00:00",
                    order_id=1,
                    mode="demo",
                    quote_spent=25.0,
                    fee_paid_quote=0.1,
                )
            }
        )
        self.state_store = FakeStateStore(self.state)
        self.order_manager = FakeOrderManager()
        self.errors_journal = FakeJournal()
        self.notifier = FakeNotifier()
        self.loggers = FakeLoggers()

    def test_market_price_error_is_recorded(self) -> None:
        self.client.latest_price_errors["BTCUSDT"] = BinanceAPIError("price failed")

        manage_open_positions(
            settings=self.settings,
            client=self.client,
            state=self.state,
            state_store=self.state_store,
            order_manager=self.order_manager,
            errors_journal=self.errors_journal,
            notifier=self.notifier,
            loggers=self.loggers,
        )

        self.assertEqual(self.order_manager.close_calls, [])
        self.assertEqual(self.errors_journal.rows[0]["scope"], "position-monitoring")
        self.assertEqual(self.notifier.messages, [])

    def test_price_inside_range_does_not_close_position(self) -> None:
        self.client.latest_prices["BTCUSDT"] = 100.0

        manage_open_positions(
            settings=self.settings,
            client=self.client,
            state=self.state,
            state_store=self.state_store,
            order_manager=self.order_manager,
            errors_journal=self.errors_journal,
            notifier=self.notifier,
            loggers=self.loggers,
        )

        self.assertEqual(self.order_manager.close_calls, [])
        self.assertEqual(self.state_store.saved_states, [])

    def test_stop_loss_closes_position(self) -> None:
        self.client.latest_prices["BTCUSDT"] = 98.0

        manage_open_positions(
            settings=self.settings,
            client=self.client,
            state=self.state,
            state_store=self.state_store,
            order_manager=self.order_manager,
            errors_journal=self.errors_journal,
            notifier=self.notifier,
            loggers=self.loggers,
        )

        self.assertEqual(self.order_manager.close_calls[0][1], "stop-loss-hit")
        self.assertEqual(len(self.state_store.saved_states), 1)

    def test_take_profit_closes_position(self) -> None:
        self.client.latest_prices["BTCUSDT"] = 104.0

        manage_open_positions(
            settings=self.settings,
            client=self.client,
            state=self.state,
            state_store=self.state_store,
            order_manager=self.order_manager,
            errors_journal=self.errors_journal,
            notifier=self.notifier,
            loggers=self.loggers,
        )

        self.assertEqual(self.order_manager.close_calls[0][1], "take-profit-hit")
        self.assertEqual(len(self.state_store.saved_states), 1)

    def test_stop_loss_close_error_is_recorded(self) -> None:
        self.client.latest_prices["BTCUSDT"] = 97.0
        self.order_manager.raise_close_error["BTCUSDT"] = BinanceAPIError("close failed")

        manage_open_positions(
            settings=self.settings,
            client=self.client,
            state=self.state,
            state_store=self.state_store,
            order_manager=self.order_manager,
            errors_journal=self.errors_journal,
            notifier=self.notifier,
            loggers=self.loggers,
        )

        self.assertEqual(self.errors_journal.rows[0]["scope"], "stop-loss-close")
        self.assertEqual(len(self.notifier.messages), 1)
        self.assertIn("Reaction: manual-review", self.notifier.messages[0])

    def test_take_profit_close_error_is_recorded(self) -> None:
        self.client.latest_prices["BTCUSDT"] = 105.0
        self.order_manager.raise_close_error["BTCUSDT"] = BinanceAPIError("close failed")

        manage_open_positions(
            settings=self.settings,
            client=self.client,
            state=self.state,
            state_store=self.state_store,
            order_manager=self.order_manager,
            errors_journal=self.errors_journal,
            notifier=self.notifier,
            loggers=self.loggers,
        )

        self.assertEqual(self.errors_journal.rows[0]["scope"], "take-profit-close")
        self.assertEqual(len(self.notifier.messages), 1)
        self.assertIn("Reaction: manual-review", self.notifier.messages[0])

    def test_processing_continues_after_error_for_one_symbol(self) -> None:
        self.state.open_positions["ETHUSDT"] = Position(
            symbol="ETHUSDT",
            quantity=0.5,
            entry_price=200.0,
            stop_loss=195.0,
            take_profit=210.0,
            opened_at="2026-03-19T12:05:00+00:00",
            order_id=2,
            mode="demo",
            quote_spent=100.0,
            fee_paid_quote=0.1,
        )
        self.client.latest_price_errors["BTCUSDT"] = BinanceAPIError("price failed")
        self.client.latest_prices["ETHUSDT"] = 210.0

        manage_open_positions(
            settings=self.settings,
            client=self.client,
            state=self.state,
            state_store=self.state_store,
            order_manager=self.order_manager,
            errors_journal=self.errors_journal,
            notifier=self.notifier,
            loggers=self.loggers,
        )

        self.assertEqual(len(self.errors_journal.rows), 1)
        self.assertEqual(self.order_manager.close_calls[0][0], "ETHUSDT")

    def test_suspect_position_is_not_auto_closed(self) -> None:
        self.state.suspect_positions["BTCUSDT"] = "local-position-missing-on-exchange"
        self.client.latest_prices["BTCUSDT"] = 97.0

        manage_open_positions(
            settings=self.settings,
            client=self.client,
            state=self.state,
            state_store=self.state_store,
            order_manager=self.order_manager,
            errors_journal=self.errors_journal,
            notifier=self.notifier,
            loggers=self.loggers,
        )

        self.assertEqual(self.order_manager.close_calls, [])
        self.assertEqual(self.state_store.saved_states, [])

    def test_observe_only_mode_skips_monitor_execution(self) -> None:
        self.settings.runtime_mode = "observe-only"
        self.client.latest_prices["BTCUSDT"] = 97.0

        manage_open_positions(
            settings=self.settings,
            client=self.client,
            state=self.state,
            state_store=self.state_store,
            order_manager=self.order_manager,
            errors_journal=self.errors_journal,
            notifier=self.notifier,
            loggers=self.loggers,
        )

        self.assertEqual(self.order_manager.close_calls, [])

    def test_symbol_override_observe_only_skips_auto_close_for_one_symbol(self) -> None:
        self.settings.symbol_policy_overrides["BTCUSDT"] = SymbolPolicyOverride(runtime_mode="observe-only")
        self.state.open_positions["ETHUSDT"] = Position(
            symbol="ETHUSDT",
            quantity=0.5,
            entry_price=200.0,
            stop_loss=195.0,
            take_profit=210.0,
            opened_at="2026-03-19T12:05:00+00:00",
            order_id=2,
            mode="demo",
            quote_spent=100.0,
            fee_paid_quote=0.1,
        )
        self.client.latest_prices["BTCUSDT"] = 97.0
        self.client.latest_prices["ETHUSDT"] = 194.0

        manage_open_positions(
            settings=self.settings,
            client=self.client,
            state=self.state,
            state_store=self.state_store,
            order_manager=self.order_manager,
            errors_journal=self.errors_journal,
            notifier=self.notifier,
            loggers=self.loggers,
        )

        self.assertEqual(len(self.order_manager.close_calls), 1)
        self.assertEqual(self.order_manager.close_calls[0][0], "ETHUSDT")


if __name__ == "__main__":
    unittest.main()