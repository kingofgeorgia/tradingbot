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
from binance_bot.orders.manager import OrderManager
from binance_bot.strategy.ema_cross import TradeSignal
from tests.fakes import (
    FakeBinanceClient,
    FakeJournal,
    FakeLoggers,
    FakeNotifier,
    FakeRiskManager,
    FakeStateStore,
    make_settings,
)


class OrderManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = make_settings()
        self.client = FakeBinanceClient()
        self.risk_manager = FakeRiskManager(quantity=0.25)
        self.state_store = FakeStateStore()
        self.loggers = FakeLoggers()
        self.notifier = FakeNotifier()
        self.signals_journal = FakeJournal()
        self.trades_journal = FakeJournal()
        self.manager = OrderManager(
            settings=self.settings,
            client=self.client,
            risk_manager=self.risk_manager,
            state_store=self.state_store,
            loggers=self.loggers,
            notifier=self.notifier,
            signals_journal=self.signals_journal,
            trades_journal=self.trades_journal,
        )

    def test_open_long_creates_position_and_writes_trade_journal(self) -> None:
        state = BotState()
        signal = TradeSignal(
            symbol="BTCUSDT",
            action="BUY",
            reason="ema20-crossed-above-ema50",
            price=100.0,
            ema_fast=101.0,
            ema_slow=99.0,
            candle_close_time=1710000000000,
        )
        filters = SymbolFilters(
            step_size=0.001,
            min_qty=0.001,
            min_notional=10.0,
            tick_size=0.01,
        )
        self.client.next_create_payload = {
            "symbol": "BTCUSDT",
            "orderId": 101,
            "status": "FILLED",
            "executedQty": "0.25",
            "cummulativeQuoteQty": "25.0",
            "fills": [{"commissionAsset": "USDT", "commission": "0.1"}],
        }

        self.manager.open_long(signal, filters, state, total_equity=1000.0, free_quote_balance=500.0)

        position = state.open_positions["BTCUSDT"]
        self.assertEqual(position.symbol, "BTCUSDT")
        self.assertAlmostEqual(position.quantity, 0.25)
        self.assertAlmostEqual(position.entry_price, 100.0)
        self.assertAlmostEqual(position.stop_loss, 98.0)
        self.assertAlmostEqual(position.take_profit, 104.0)
        self.assertEqual(self.client.created_orders, [("BTCUSDT", "BUY", 0.25)])
        self.assertEqual(len(self.state_store.saved_states), 1)
        self.assertEqual(self.trades_journal.rows[0]["side"], "BUY")
        self.assertEqual(self.trades_journal.rows[0]["symbol"], "BTCUSDT")
        self.assertIn("Opened BUY BTCUSDT", self.notifier.messages[0])

    def test_close_position_updates_pnl_and_sends_halt_notification(self) -> None:
        state = BotState(
            open_positions={
                "BTCUSDT": Position(
                    symbol="BTCUSDT",
                    quantity=0.25,
                    entry_price=100.0,
                    stop_loss=98.0,
                    take_profit=104.0,
                    opened_at="2026-03-19T12:00:00+00:00",
                    order_id=101,
                    mode="demo",
                    quote_spent=25.0,
                    fee_paid_quote=0.1,
                )
            }
        )
        self.client.filters_by_symbol["BTCUSDT"] = SymbolFilters(
            step_size=0.001,
            min_qty=0.001,
            min_notional=10.0,
            tick_size=0.01,
        )
        self.client.rounded_quantity = 0.25
        self.client.next_create_payload = {
            "symbol": "BTCUSDT",
            "orderId": 202,
            "status": "FILLED",
            "executedQty": "0.25",
            "cummulativeQuoteQty": "27.5",
            "fills": [{"commissionAsset": "USDT", "commission": "0.2"}],
        }
        self.risk_manager.halt_reason = "daily-loss-limit-reached"

        halt_reason = self.manager.close_position("BTCUSDT", "take-profit-hit", state)

        self.assertEqual(halt_reason, "daily-loss-limit-reached")
        self.assertNotIn("BTCUSDT", state.open_positions)
        self.assertEqual(self.client.created_orders, [("BTCUSDT", "SELL", 0.25)])
        self.assertEqual(len(self.state_store.saved_states), 1)
        self.assertAlmostEqual(self.risk_manager.closed_trade_calls[0][0], 2.2)
        self.assertEqual(self.trades_journal.rows[0]["side"], "SELL")
        self.assertEqual(self.trades_journal.rows[0]["reason"], "take-profit-hit")
        self.assertIn("Closed BTCUSDT", self.notifier.messages[0])
        self.assertIn("Trading halted", self.notifier.messages[1])

    def test_close_position_raises_when_quantity_rounds_to_zero(self) -> None:
        state = BotState(
            open_positions={
                "BTCUSDT": Position(
                    symbol="BTCUSDT",
                    quantity=0.0004,
                    entry_price=100.0,
                    stop_loss=98.0,
                    take_profit=104.0,
                    opened_at="2026-03-19T12:00:00+00:00",
                    order_id=101,
                    mode="demo",
                    quote_spent=0.04,
                    fee_paid_quote=0.0,
                )
            }
        )
        self.client.filters_by_symbol["BTCUSDT"] = SymbolFilters(
            step_size=0.001,
            min_qty=0.001,
            min_notional=10.0,
            tick_size=0.01,
        )
        self.client.rounded_quantity = 0.0

        with self.assertRaises(BinanceAPIError):
            self.manager.close_position("BTCUSDT", "stop-loss-hit", state)


if __name__ == "__main__":
    unittest.main()
