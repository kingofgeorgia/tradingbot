from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from binance_bot.core.models import BotState, Position, SymbolFilters
from binance_bot.core.trade_execution import build_open_position_result, calculate_close_result
from binance_bot.strategy.ema_cross import TradeSignal
from binance_bot.use_cases.trade_execution import ClosePositionUseCase, OpenPositionUseCase
from tests.fakes import FakeBinanceClient, FakeJournal, FakeLogger, FakeNotifier, FakeRiskManager, FakeStateStore, make_settings


class TradeExecutionModelTests(unittest.TestCase):
    def test_build_open_position_result_creates_position_snapshot(self) -> None:
        result = build_open_position_result(
            symbol="BTCUSDT",
            quantity=0.25,
            average_price=100.0,
            stop_loss_pct=0.02,
            take_profit_pct=0.04,
            opened_at="2026-03-20T10:00:00+00:00",
            order_id=101,
            mode="demo",
            quote_spent=25.0,
            fee_paid_quote=0.1,
        )

        self.assertEqual(result.position.symbol, "BTCUSDT")
        self.assertAlmostEqual(result.stop_loss, 98.0)
        self.assertAlmostEqual(result.take_profit, 104.0)
        self.assertEqual(result.position.order_id, 101)

    def test_calculate_close_result_returns_expected_pnl(self) -> None:
        position = Position(
            symbol="BTCUSDT",
            quantity=0.25,
            entry_price=100.0,
            stop_loss=98.0,
            take_profit=104.0,
            opened_at="2026-03-20T10:00:00+00:00",
            order_id=101,
            mode="demo",
            quote_spent=25.0,
            fee_paid_quote=0.1,
        )

        result = calculate_close_result(
            symbol="BTCUSDT",
            reason="take-profit-hit",
            position=position,
            average_price=110.0,
            executed_quantity=0.25,
            quote_received=27.5,
            exit_fee_quote=0.2,
            halt_reason="daily-loss-limit-reached",
        )

        self.assertAlmostEqual(result.pnl_quote, 2.2)
        self.assertEqual(result.halt_reason, "daily-loss-limit-reached")


class OpenPositionUseCaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = make_settings()
        self.client = FakeBinanceClient()
        self.risk_manager = FakeRiskManager(quantity=0.25)
        self.state_store = FakeStateStore()
        self.trades_journal = FakeJournal()
        self.trade_logger = FakeLogger()
        self.notifier = FakeNotifier()
        self.use_case = OpenPositionUseCase(
            settings=self.settings,
            client=self.client,
            risk_manager=self.risk_manager,
            state_store=self.state_store,
            trades_journal=self.trades_journal,
            trade_logger=self.trade_logger,
            notifier=self.notifier,
        )

    def test_execute_confirms_pending_order_and_persists_position(self) -> None:
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
        filters = SymbolFilters(step_size=0.001, min_qty=0.001, min_notional=10.0, tick_size=0.01)
        self.client.next_create_payload = {
            "symbol": "BTCUSDT",
            "orderId": 101,
            "status": "NEW",
            "executedQty": "0.0",
            "cummulativeQuoteQty": "0.0",
            "fills": [],
        }
        self.client.next_confirm_payload = {
            "symbol": "BTCUSDT",
            "orderId": 101,
            "status": "FILLED",
            "executedQty": "0.25",
            "cummulativeQuoteQty": "25.0",
            "fills": [{"commissionAsset": "USDT", "commission": "0.1"}],
        }

        result = self.use_case.execute(
            signal=signal,
            filters=filters,
            state=state,
            total_equity=1000.0,
            free_quote_balance=500.0,
        )

        self.assertEqual(self.client.confirm_calls, [("BTCUSDT", 101, self.settings.order_confirm_timeout_seconds)])
        self.assertEqual(state.open_positions["BTCUSDT"].order_id, 101)
        self.assertEqual(len(self.state_store.saved_states), 1)
        self.assertEqual(self.trades_journal.rows[0]["side"], "BUY")
        self.assertIn("Opened BUY BTCUSDT", self.notifier.messages[0])
        self.assertAlmostEqual(result.position.quantity, 0.25)


class ClosePositionUseCaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = make_settings()
        self.client = FakeBinanceClient()
        self.risk_manager = FakeRiskManager(quantity=0.25, halt_reason="daily-loss-limit-reached")
        self.state_store = FakeStateStore()
        self.trades_journal = FakeJournal()
        self.trade_logger = FakeLogger()
        self.notifier = FakeNotifier()
        self.use_case = ClosePositionUseCase(
            settings=self.settings,
            client=self.client,
            risk_manager=self.risk_manager,
            state_store=self.state_store,
            trades_journal=self.trades_journal,
            trade_logger=self.trade_logger,
            notifier=self.notifier,
        )

    def test_execute_confirms_close_and_sends_halt_notification(self) -> None:
        state = BotState(
            open_positions={
                "BTCUSDT": Position(
                    symbol="BTCUSDT",
                    quantity=0.25,
                    entry_price=100.0,
                    stop_loss=98.0,
                    take_profit=104.0,
                    opened_at="2026-03-20T10:00:00+00:00",
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
        self.client.next_create_payload = {
            "symbol": "BTCUSDT",
            "orderId": 202,
            "status": "NEW",
            "executedQty": "0.0",
            "cummulativeQuoteQty": "0.0",
            "fills": [],
        }
        self.client.next_confirm_payload = {
            "symbol": "BTCUSDT",
            "orderId": 202,
            "status": "FILLED",
            "executedQty": "0.25",
            "cummulativeQuoteQty": "27.5",
            "fills": [{"commissionAsset": "USDT", "commission": "0.2"}],
        }

        halt_reason = self.use_case.execute(symbol="BTCUSDT", reason="take-profit-hit", state=state)

        self.assertEqual(halt_reason, "daily-loss-limit-reached")
        self.assertEqual(self.client.confirm_calls, [("BTCUSDT", 202, self.settings.order_confirm_timeout_seconds)])
        self.assertNotIn("BTCUSDT", state.open_positions)
        self.assertEqual(self.trades_journal.rows[0]["side"], "SELL")
        self.assertIn("Closed BTCUSDT", self.notifier.messages[0])
        self.assertIn("Trading halted", self.notifier.messages[1])


if __name__ == "__main__":
    unittest.main()