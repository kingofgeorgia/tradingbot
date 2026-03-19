from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from binance_bot.clients.binance_client import BinanceAPIError
from binance_bot.core.models import BotState, Position, SymbolFilters
from binance_bot.strategy.ema_cross import TradeSignal
from binance_bot.services.cycle import process_cycle
from tests.fakes import FakeBinanceClient, FakeJournal, FakeLoggers, FakeNotifier, FakeRiskManager, FakeStateStore, make_settings


class FakeStrategy:
    def __init__(self) -> None:
        self.signals_by_symbol: dict[str, TradeSignal] = {}
        self.calls: list[tuple[str, object, object]] = []

    def evaluate(self, symbol: str, candles, last_processed_candle):
        self.calls.append((symbol, candles, last_processed_candle))
        return self.signals_by_symbol[symbol]


class FakeOrderManager:
    def __init__(self) -> None:
        self.logged_signals: list[TradeSignal] = []
        self.open_calls: list[tuple[TradeSignal, object, BotState, float, float]] = []
        self.close_calls: list[tuple[str, str, BotState]] = []
        self.open_errors: dict[str, Exception] = {}
        self.close_errors: dict[str, Exception] = {}
        self.close_result: str | None = None

    def log_signal(self, signal: TradeSignal) -> None:
        self.logged_signals.append(signal)

    def open_long(self, signal: TradeSignal, filters, state: BotState, total_equity: float, free_quote_balance: float) -> None:
        self.open_calls.append((signal, filters, state, total_equity, free_quote_balance))
        if signal.symbol in self.open_errors:
            raise self.open_errors[signal.symbol]

    def close_position(self, symbol: str, reason: str, state: BotState) -> str | None:
        self.close_calls.append((symbol, reason, state))
        if symbol in self.close_errors:
            raise self.close_errors[symbol]
        return self.close_result


class CycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = make_settings()
        self.client = FakeBinanceClient()
        self.client.portfolio_value = 1000.0
        self.client.free_quote_balance = 500.0
        self.client.filters_by_symbol = {
            "BTCUSDT": SymbolFilters(step_size=0.001, min_qty=0.001, min_notional=10.0, tick_size=0.01),
            "ETHUSDT": SymbolFilters(step_size=0.001, min_qty=0.001, min_notional=10.0, tick_size=0.01),
        }
        self.client.klines_by_symbol = {
            "BTCUSDT": ["btc-candles"],
            "ETHUSDT": ["eth-candles"],
        }
        self.state = BotState()
        self.state_store = FakeStateStore(self.state)
        self.strategy = FakeStrategy()
        self.risk_manager = FakeRiskManager(quantity=0.25)
        self.order_manager = FakeOrderManager()
        self.errors_journal = FakeJournal()
        self.notifier = FakeNotifier()
        self.loggers = FakeLoggers()

    def test_portfolio_error_aborts_cycle(self) -> None:
        self.client.raise_portfolio_error = BinanceAPIError("portfolio failed")

        process_cycle(
            settings=self.settings,
            client=self.client,
            state=self.state,
            state_store=self.state_store,
            strategy=self.strategy,
            risk_manager=self.risk_manager,
            order_manager=self.order_manager,
            errors_journal=self.errors_journal,
            notifier=self.notifier,
            loggers=self.loggers,
        )

        self.assertEqual(self.errors_journal.rows[0]["scope"], "portfolio")
        self.assertEqual(self.order_manager.logged_signals, [])

    def test_refresh_trading_day_saves_state(self) -> None:
        self.strategy.signals_by_symbol = {
            "BTCUSDT": TradeSignal("BTCUSDT", "HOLD", "no-crossover", 100.0, 101.0, 99.0, 1710000000000),
            "ETHUSDT": TradeSignal("ETHUSDT", "HOLD", "no-crossover", 200.0, 201.0, 199.0, 1710000005000),
        }

        process_cycle(
            settings=self.settings,
            client=self.client,
            state=self.state,
            state_store=self.state_store,
            strategy=self.strategy,
            risk_manager=self.risk_manager,
            order_manager=self.order_manager,
            errors_journal=self.errors_journal,
            notifier=self.notifier,
            loggers=self.loggers,
        )

        self.assertNotEqual(self.state.trading_day, "")
        self.assertGreaterEqual(len(self.state_store.saved_states), 3)

    def test_market_data_error_records_and_continues(self) -> None:
        self.client.klines_errors["BTCUSDT"] = BinanceAPIError("klines failed")
        self.strategy.signals_by_symbol["ETHUSDT"] = TradeSignal(
            "ETHUSDT", "HOLD", "no-crossover", 200.0, 201.0, 199.0, 1710000005000
        )

        process_cycle(
            settings=self.settings,
            client=self.client,
            state=self.state,
            state_store=self.state_store,
            strategy=self.strategy,
            risk_manager=self.risk_manager,
            order_manager=self.order_manager,
            errors_journal=self.errors_journal,
            notifier=self.notifier,
            loggers=self.loggers,
        )

        self.assertEqual(self.errors_journal.rows[0]["scope"], "market-data")
        self.assertEqual(self.strategy.calls[0][0], "ETHUSDT")

    def test_hold_signal_updates_last_processed_candle_without_logging(self) -> None:
        self.strategy.signals_by_symbol = {
            "BTCUSDT": TradeSignal("BTCUSDT", "HOLD", "no-crossover", 100.0, 101.0, 99.0, 1710000000000),
            "ETHUSDT": TradeSignal("ETHUSDT", "HOLD", "no-crossover", 200.0, 201.0, 199.0, 1710000005000),
        }

        process_cycle(
            settings=self.settings,
            client=self.client,
            state=self.state,
            state_store=self.state_store,
            strategy=self.strategy,
            risk_manager=self.risk_manager,
            order_manager=self.order_manager,
            errors_journal=self.errors_journal,
            notifier=self.notifier,
            loggers=self.loggers,
        )

        self.assertEqual(self.state.last_processed_candle["BTCUSDT"], 1710000000000)
        self.assertEqual(self.order_manager.logged_signals, [])

    def test_sell_with_open_position_logs_and_closes(self) -> None:
        self.state.open_positions["BTCUSDT"] = Position(
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
        self.client.latest_prices["BTCUSDT"] = 100.0
        self.strategy.signals_by_symbol = {
            "BTCUSDT": TradeSignal("BTCUSDT", "SELL", "ema20-crossed-below-ema50", 100.0, 99.0, 101.0, 1710000000000),
            "ETHUSDT": TradeSignal("ETHUSDT", "HOLD", "no-crossover", 200.0, 201.0, 199.0, 1710000005000),
        }

        process_cycle(
            settings=self.settings,
            client=self.client,
            state=self.state,
            state_store=self.state_store,
            strategy=self.strategy,
            risk_manager=self.risk_manager,
            order_manager=self.order_manager,
            errors_journal=self.errors_journal,
            notifier=self.notifier,
            loggers=self.loggers,
        )

        self.assertEqual(self.order_manager.logged_signals[0].action, "SELL")
        self.assertEqual(self.order_manager.close_calls[0][0], "BTCUSDT")

    def test_sell_without_open_position_only_logs(self) -> None:
        self.strategy.signals_by_symbol = {
            "BTCUSDT": TradeSignal("BTCUSDT", "SELL", "ema20-crossed-below-ema50", 100.0, 99.0, 101.0, 1710000000000),
            "ETHUSDT": TradeSignal("ETHUSDT", "HOLD", "no-crossover", 200.0, 201.0, 199.0, 1710000005000),
        }

        process_cycle(
            settings=self.settings,
            client=self.client,
            state=self.state,
            state_store=self.state_store,
            strategy=self.strategy,
            risk_manager=self.risk_manager,
            order_manager=self.order_manager,
            errors_journal=self.errors_journal,
            notifier=self.notifier,
            loggers=self.loggers,
        )

        self.assertEqual(self.order_manager.logged_signals[0].action, "SELL")
        self.assertEqual(self.order_manager.close_calls, [])

    def test_buy_denied_logs_skip(self) -> None:
        self.risk_manager.next_can_open = (False, "trading-halted-for-the-day")
        self.strategy.signals_by_symbol = {
            "BTCUSDT": TradeSignal("BTCUSDT", "BUY", "ema20-crossed-above-ema50", 100.0, 101.0, 99.0, 1710000000000),
            "ETHUSDT": TradeSignal("ETHUSDT", "HOLD", "no-crossover", 200.0, 201.0, 199.0, 1710000005000),
        }

        process_cycle(
            settings=self.settings,
            client=self.client,
            state=self.state,
            state_store=self.state_store,
            strategy=self.strategy,
            risk_manager=self.risk_manager,
            order_manager=self.order_manager,
            errors_journal=self.errors_journal,
            notifier=self.notifier,
            loggers=self.loggers,
        )

        self.assertEqual(self.order_manager.open_calls, [])
        self.assertIn("Skipping BUY for %s: %s", self.loggers.app.records[0][0])

    def test_buy_allowed_opens_position(self) -> None:
        self.strategy.signals_by_symbol = {
            "BTCUSDT": TradeSignal("BTCUSDT", "BUY", "ema20-crossed-above-ema50", 100.0, 101.0, 99.0, 1710000000000),
            "ETHUSDT": TradeSignal("ETHUSDT", "HOLD", "no-crossover", 200.0, 201.0, 199.0, 1710000005000),
        }

        process_cycle(
            settings=self.settings,
            client=self.client,
            state=self.state,
            state_store=self.state_store,
            strategy=self.strategy,
            risk_manager=self.risk_manager,
            order_manager=self.order_manager,
            errors_journal=self.errors_journal,
            notifier=self.notifier,
            loggers=self.loggers,
        )

        self.assertEqual(self.order_manager.open_calls[0][0].action, "BUY")
        self.assertEqual(self.client.klines_calls[0][0], "BTCUSDT")

    def test_open_error_is_recorded(self) -> None:
        self.strategy.signals_by_symbol = {
            "BTCUSDT": TradeSignal("BTCUSDT", "BUY", "ema20-crossed-above-ema50", 100.0, 101.0, 99.0, 1710000000000),
            "ETHUSDT": TradeSignal("ETHUSDT", "HOLD", "no-crossover", 200.0, 201.0, 199.0, 1710000005000),
        }
        self.order_manager.open_errors["BTCUSDT"] = ValueError("open failed")

        process_cycle(
            settings=self.settings,
            client=self.client,
            state=self.state,
            state_store=self.state_store,
            strategy=self.strategy,
            risk_manager=self.risk_manager,
            order_manager=self.order_manager,
            errors_journal=self.errors_journal,
            notifier=self.notifier,
            loggers=self.loggers,
        )

        self.assertEqual(self.errors_journal.rows[0]["scope"], "open-position")

    def test_close_error_is_recorded(self) -> None:
        self.state.open_positions["BTCUSDT"] = Position(
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
        self.client.latest_prices["BTCUSDT"] = 100.0
        self.strategy.signals_by_symbol = {
            "BTCUSDT": TradeSignal("BTCUSDT", "SELL", "ema20-crossed-below-ema50", 100.0, 99.0, 101.0, 1710000000000),
            "ETHUSDT": TradeSignal("ETHUSDT", "HOLD", "no-crossover", 200.0, 201.0, 199.0, 1710000005000),
        }
        self.order_manager.close_errors["BTCUSDT"] = BinanceAPIError("close failed")

        process_cycle(
            settings=self.settings,
            client=self.client,
            state=self.state,
            state_store=self.state_store,
            strategy=self.strategy,
            risk_manager=self.risk_manager,
            order_manager=self.order_manager,
            errors_journal=self.errors_journal,
            notifier=self.notifier,
            loggers=self.loggers,
        )

        self.assertEqual(self.errors_journal.rows[0]["scope"], "close-position")

    def test_halt_reason_sends_notification(self) -> None:
        self.state.open_positions["BTCUSDT"] = Position(
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
        self.client.latest_prices["BTCUSDT"] = 100.0
        self.strategy.signals_by_symbol = {
            "BTCUSDT": TradeSignal("BTCUSDT", "SELL", "ema20-crossed-below-ema50", 100.0, 99.0, 101.0, 1710000000000),
            "ETHUSDT": TradeSignal("ETHUSDT", "HOLD", "no-crossover", 200.0, 201.0, 199.0, 1710000005000),
        }
        self.order_manager.close_result = "daily-loss-limit-reached"

        process_cycle(
            settings=self.settings,
            client=self.client,
            state=self.state,
            state_store=self.state_store,
            strategy=self.strategy,
            risk_manager=self.risk_manager,
            order_manager=self.order_manager,
            errors_journal=self.errors_journal,
            notifier=self.notifier,
            loggers=self.loggers,
        )

        self.assertIn("Daily loss limit reached.", self.notifier.messages[0])


if __name__ == "__main__":
    unittest.main()