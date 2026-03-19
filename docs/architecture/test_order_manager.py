from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
TESTS_DIR = PROJECT_ROOT / "tests"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from binance_bot.core.models import BotState, Position, SymbolFilters
from binance_bot.orders.manager import OrderManager
from binance_bot.strategy.ema_cross import TradeSignal
from fakes import (
    FakeClient,
    FakeJournal,
    FakeLoggers,
    FakeNotifier,
    FakeRiskManager,
    FakeStateStore,
    make_settings,
)


def build_order_manager(
    *,
    buy_price: float = 100.0,
    sell_price: float = 110.0,
    quantity: float = 0.2,
    halt_reason: str | None = None,
) -> tuple[OrderManager, FakeClient, FakeRiskManager, FakeStateStore, FakeNotifier, FakeJournal, FakeJournal]:
    settings = make_settings()
    client = FakeClient(
        filters=SymbolFilters(step_size=0.001, min_qty=0.001, min_notional=10.0, tick_size=0.01),
        buy_price=buy_price,
        sell_price=sell_price,
        quote_asset=settings.quote_asset,
        buy_fee=0.01,
        sell_fee=0.01,
    )
    risk_manager = FakeRiskManager(quantity=quantity, halt_reason=halt_reason)
    state_store = FakeStateStore()
    loggers = FakeLoggers()
    notifier = FakeNotifier()
    signals_journal = FakeJournal()
    trades_journal = FakeJournal()
    manager = OrderManager(
        settings=settings,
        client=client,
        risk_manager=risk_manager,
        state_store=state_store,
        loggers=loggers,
        notifier=notifier,
        signals_journal=signals_journal,
        trades_journal=trades_journal,
    )
    return manager, client, risk_manager, state_store, notifier, signals_journal, trades_journal


class OrderManagerTests(unittest.TestCase):
    def test_log_signal_writes_row_to_signal_journal(self) -> None:
        manager, _client, _risk_manager, _state_store, _notifier, signals_journal, _trades_journal = build_order_manager()
        signal = TradeSignal(
            symbol="BTCUSDT",
            action="BUY",
            reason="ema20-crossed-above-ema50",
            price=101.25,
            ema_fast=100.9,
            ema_slow=100.1,
            candle_close_time=1742339700000,
        )

        manager.log_signal(signal)

        self.assertEqual(len(signals_journal.rows), 1)
        row = signals_journal.rows[0]
        self.assertEqual(row["symbol"], "BTCUSDT")
        self.assertEqual(row["action"], "BUY")
        self.assertEqual(row["reason"], "ema20-crossed-above-ema50")

    def test_open_long_creates_position_and_trade_row(self) -> None:
        manager, _client, risk_manager, state_store, notifier, _signals_journal, trades_journal = build_order_manager(
            buy_price=100.0,
            quantity=0.2,
        )
        signal = TradeSignal(
            symbol="BTCUSDT",
            action="BUY",
            reason="ema20-crossed-above-ema50",
            price=100.0,
            ema_fast=100.0,
            ema_slow=99.0,
            candle_close_time=1742339700000,
        )
        state = BotState()
        filters = SymbolFilters(step_size=0.001, min_qty=0.001, min_notional=10.0, tick_size=0.01)

        manager.open_long(
            signal=signal,
            filters=filters,
            state=state,
            total_equity=1_000.0,
            free_quote_balance=500.0,
        )

        self.assertIn("BTCUSDT", state.open_positions)
        position = state.open_positions["BTCUSDT"]
        self.assertAlmostEqual(position.quantity, 0.2)
        self.assertAlmostEqual(position.entry_price, 100.0)
        self.assertEqual(len(risk_manager.calculate_calls), 1)
        self.assertGreaterEqual(len(state_store.saved_states), 1)
        self.assertEqual(len(trades_journal.rows), 1)
        self.assertEqual(trades_journal.rows[0]["side"], "BUY")
        self.assertEqual(len(notifier.messages), 1)
        self.assertIn("Opened BUY BTCUSDT", notifier.messages[0])

    def test_close_position_removes_position_and_writes_sell_row(self) -> None:
        manager, _client, risk_manager, state_store, notifier, _signals_journal, trades_journal = build_order_manager(
            sell_price=110.0,
            halt_reason=None,
        )
        state = BotState(
            open_positions={
                "BTCUSDT": Position(
                    symbol="BTCUSDT",
                    quantity=0.2,
                    entry_price=100.0,
                    stop_loss=98.0,
                    take_profit=104.0,
                    opened_at="2026-03-19T00:00:00+00:00",
                    order_id=1001,
                    mode="demo",
                    quote_spent=20.0,
                    fee_paid_quote=0.01,
                )
            }
        )

        halt_reason = manager.close_position("BTCUSDT", "ema20-crossed-below-ema50", state)

        self.assertIsNone(halt_reason)
        self.assertNotIn("BTCUSDT", state.open_positions)
        self.assertEqual(len(risk_manager.closed_trade_calls), 1)
        self.assertGreaterEqual(len(state_store.saved_states), 1)
        self.assertEqual(len(trades_journal.rows), 1)
        self.assertEqual(trades_journal.rows[0]["side"], "SELL")
        self.assertEqual(len(notifier.messages), 1)
        self.assertIn("Closed BTCUSDT", notifier.messages[0])

    def test_close_position_returns_halt_reason_when_risk_manager_requests_stop(self) -> None:
        manager, _client, _risk_manager, _state_store, notifier, _signals_journal, _trades_journal = build_order_manager(
            sell_price=90.0,
            halt_reason="daily-loss-limit-reached",
        )
        state = BotState(
            open_positions={
                "BTCUSDT": Position(
                    symbol="BTCUSDT",
                    quantity=0.2,
                    entry_price=100.0,
                    stop_loss=98.0,
                    take_profit=104.0,
                    opened_at="2026-03-19T00:00:00+00:00",
                    order_id=1001,
                    mode="demo",
                    quote_spent=20.0,
                    fee_paid_quote=0.01,
                )
            }
        )

        halt_reason = manager.close_position("BTCUSDT", "stop-loss-hit", state)

        self.assertEqual(halt_reason, "daily-loss-limit-reached")
        self.assertEqual(len(notifier.messages), 2)
        self.assertIn("Trading halted", notifier.messages[1])


if __name__ == "__main__":
    unittest.main()