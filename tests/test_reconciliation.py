from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from binance_bot.clients.binance_client import BinanceAPIError
from binance_bot.core.models import BotState, ExchangePositionSnapshot, Position, SymbolFilters
from binance_bot.services.cycle import process_cycle
from binance_bot.services.reconciliation import apply_reconciliation_result, reconcile_runtime_state
from binance_bot.strategy.ema_cross import TradeSignal
from tests.fakes import FakeBinanceClient, FakeJournal, FakeLoggers, FakeNotifier, FakeRiskManager, FakeStateStore, make_settings


class FakeOrderManager:
    def __init__(self) -> None:
        self.restored: list[str] = []
        self.marked: list[tuple[str, str]] = []
        self.open_calls: list[tuple[TradeSignal, object, BotState, float, float]] = []

    def restore_position_from_exchange(self, snapshot: ExchangePositionSnapshot, state: BotState) -> None:
        state.open_positions[snapshot.symbol] = Position(
            symbol=snapshot.symbol,
            quantity=snapshot.exchange_quantity,
            entry_price=snapshot.average_entry_price or 0.0,
            stop_loss=(snapshot.average_entry_price or 0.0) * 0.98,
            take_profit=(snapshot.average_entry_price or 0.0) * 1.04,
            opened_at="2026-03-20T10:00:00+00:00",
            order_id=snapshot.last_order_id or 0,
            mode="demo",
            quote_spent=(snapshot.average_entry_price or 0.0) * snapshot.exchange_quantity,
            fee_paid_quote=0.0,
        )
        self.restored.append(snapshot.symbol)

    def mark_position_unrecoverable(self, symbol: str, reason: str, state: BotState) -> None:
        state.blocked_symbols[symbol] = reason
        if symbol in state.open_positions:
            state.suspect_positions[symbol] = reason
        self.marked.append((symbol, reason))

    def open_long(self, signal: TradeSignal, filters, state: BotState, total_equity: float, free_quote_balance: float) -> None:
        self.open_calls.append((signal, filters, state, total_equity, free_quote_balance))

    def log_signal(self, signal: TradeSignal) -> None:
        return None

    def close_position(self, symbol: str, reason: str, state: BotState):
        return None


class FakeStrategy:
    def __init__(self) -> None:
        self.signals_by_symbol: dict[str, TradeSignal] = {}

    def evaluate(self, symbol: str, candles, last_processed_candle):
        return self.signals_by_symbol[symbol]


class ReconciliationTests(unittest.TestCase):
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
        self.state_store = FakeStateStore(BotState())
        self.order_manager = FakeOrderManager()
        self.reconciliation_journal = FakeJournal()
        self.errors_journal = FakeJournal()
        self.notifier = FakeNotifier()
        self.loggers = FakeLoggers()

    def test_local_position_missing_on_exchange_blocks_symbol(self) -> None:
        state = BotState(
            open_positions={
                "BTCUSDT": Position(
                    symbol="BTCUSDT",
                    quantity=0.25,
                    entry_price=100.0,
                    stop_loss=98.0,
                    take_profit=104.0,
                    opened_at="2026-03-20T10:00:00+00:00",
                    order_id=1,
                    mode="demo",
                    quote_spent=25.0,
                    fee_paid_quote=0.1,
                )
            }
        )
        self.client.position_snapshots["BTCUSDT"] = ExchangePositionSnapshot(
            symbol="BTCUSDT",
            base_asset="BTC",
            exchange_quantity=0.0,
            average_entry_price=None,
            last_order_id=None,
            last_trade_time=None,
            has_open_orders=False,
            has_recent_trades=False,
            step_size=0.001,
        )
        self.client.position_snapshots["ETHUSDT"] = ExchangePositionSnapshot(
            symbol="ETHUSDT",
            base_asset="ETH",
            exchange_quantity=0.0,
            average_entry_price=None,
            last_order_id=None,
            last_trade_time=None,
            has_open_orders=False,
            has_recent_trades=False,
            step_size=0.001,
        )

        result = reconcile_runtime_state(settings=self.settings, client=self.client, state=state)
        apply_reconciliation_result(
            settings=self.settings,
            state=state,
            state_store=self.state_store,
            order_manager=self.order_manager,
            result=result,
            reconciliation_journal=self.reconciliation_journal,
            errors_journal=self.errors_journal,
            notifier=self.notifier,
            loggers=self.loggers,
        )

        self.assertIn("BTCUSDT", state.blocked_symbols)
        self.assertIn("BTCUSDT", state.suspect_positions)
        self.assertEqual(len(self.notifier.messages), 1)
        self.assertEqual(self.errors_journal.rows[0]["scope"], "startup-reconciliation")

    def test_exchange_position_without_local_state_is_restored_when_recoverable(self) -> None:
        state = BotState()
        self.client.position_snapshots["BTCUSDT"] = ExchangePositionSnapshot(
            symbol="BTCUSDT",
            base_asset="BTC",
            exchange_quantity=0.25,
            average_entry_price=100.0,
            last_order_id=55,
            last_trade_time=1710000000000,
            has_open_orders=False,
            has_recent_trades=True,
            step_size=0.001,
        )
        self.client.position_snapshots["ETHUSDT"] = ExchangePositionSnapshot(
            symbol="ETHUSDT",
            base_asset="ETH",
            exchange_quantity=0.0,
            average_entry_price=None,
            last_order_id=None,
            last_trade_time=None,
            has_open_orders=False,
            has_recent_trades=False,
            step_size=0.001,
        )

        result = reconcile_runtime_state(settings=self.settings, client=self.client, state=state)
        apply_reconciliation_result(
            settings=self.settings,
            state=state,
            state_store=self.state_store,
            order_manager=self.order_manager,
            result=result,
            reconciliation_journal=self.reconciliation_journal,
            errors_journal=self.errors_journal,
            notifier=self.notifier,
            loggers=self.loggers,
        )

        self.assertIn("BTCUSDT", state.open_positions)
        self.assertNotIn("BTCUSDT", state.blocked_symbols)
        self.assertEqual(self.order_manager.restored, ["BTCUSDT"])
        self.assertIn("Recovered from exchange", self.notifier.messages[0])

    def test_repeated_reconciliation_does_not_repeat_restore_side_effects(self) -> None:
        state = BotState()
        self.client.position_snapshots["BTCUSDT"] = ExchangePositionSnapshot(
            symbol="BTCUSDT",
            base_asset="BTC",
            exchange_quantity=0.25,
            average_entry_price=100.0,
            last_order_id=55,
            last_trade_time=1710000000000,
            has_open_orders=False,
            has_recent_trades=True,
            step_size=0.001,
        )
        self.client.position_snapshots["ETHUSDT"] = ExchangePositionSnapshot(
            symbol="ETHUSDT",
            base_asset="ETH",
            exchange_quantity=0.0,
            average_entry_price=None,
            last_order_id=None,
            last_trade_time=None,
            has_open_orders=False,
            has_recent_trades=False,
            step_size=0.001,
        )

        first_result = reconcile_runtime_state(settings=self.settings, client=self.client, state=state)
        apply_reconciliation_result(
            settings=self.settings,
            state=state,
            state_store=self.state_store,
            order_manager=self.order_manager,
            result=first_result,
            reconciliation_journal=self.reconciliation_journal,
            errors_journal=self.errors_journal,
            notifier=self.notifier,
            loggers=self.loggers,
        )

        second_result = reconcile_runtime_state(settings=self.settings, client=self.client, state=state)
        apply_reconciliation_result(
            settings=self.settings,
            state=state,
            state_store=self.state_store,
            order_manager=self.order_manager,
            result=second_result,
            reconciliation_journal=self.reconciliation_journal,
            errors_journal=self.errors_journal,
            notifier=self.notifier,
            loggers=self.loggers,
        )

        self.assertEqual(self.order_manager.restored, ["BTCUSDT"])
        self.assertEqual(len(self.notifier.messages), 1)
        self.assertEqual(len(self.reconciliation_journal.rows), 1)
        self.assertEqual(len(self.errors_journal.rows), 0)
        self.assertEqual(state.startup_issues, [])
        self.assertEqual(state.blocked_symbols, {})
        self.assertEqual(state.last_reconciliation_status, "clean")

    def test_snapshot_failure_blocks_symbol(self) -> None:
        state = BotState()
        self.client.position_snapshot_errors["BTCUSDT"] = BinanceAPIError("snapshot failed")
        self.client.position_snapshots["ETHUSDT"] = ExchangePositionSnapshot(
            symbol="ETHUSDT",
            base_asset="ETH",
            exchange_quantity=0.0,
            average_entry_price=None,
            last_order_id=None,
            last_trade_time=None,
            has_open_orders=False,
            has_recent_trades=False,
            step_size=0.001,
        )

        result = reconcile_runtime_state(settings=self.settings, client=self.client, state=state)

        self.assertIn("BTCUSDT", result.blocked_symbols)
        self.assertEqual(result.issues[0].issue_type, "snapshot-load-failed")

    def test_cycle_skips_blocked_symbol_without_repeat_notifier(self) -> None:
        state = BotState(blocked_symbols={"BTCUSDT": "quantity-mismatch"})
        strategy = FakeStrategy()
        strategy.signals_by_symbol = {
            "ETHUSDT": TradeSignal("ETHUSDT", "BUY", "ema20-crossed-above-ema50", 200.0, 201.0, 199.0, 1710000005000)
        }
        risk_manager = FakeRiskManager(quantity=0.25)

        process_cycle(
            settings=self.settings,
            client=self.client,
            state=state,
            state_store=self.state_store,
            strategy=strategy,
            risk_manager=risk_manager,
            order_manager=self.order_manager,
            errors_journal=self.errors_journal,
            notifier=self.notifier,
            loggers=self.loggers,
        )

        self.assertEqual(len(self.notifier.messages), 0)
        self.assertEqual(self.order_manager.open_calls[0][0].symbol, "ETHUSDT")

    def test_acknowledged_issue_does_not_resend_alert_on_next_reconciliation(self) -> None:
        state = BotState(
            open_positions={
                "BTCUSDT": Position(
                    symbol="BTCUSDT",
                    quantity=0.25,
                    entry_price=100.0,
                    stop_loss=98.0,
                    take_profit=104.0,
                    opened_at="2026-03-20T10:00:00+00:00",
                    order_id=1,
                    mode="demo",
                    quote_spent=25.0,
                    fee_paid_quote=0.1,
                )
            }
        )
        snapshot = ExchangePositionSnapshot(
            symbol="BTCUSDT",
            base_asset="BTC",
            exchange_quantity=0.0,
            average_entry_price=None,
            last_order_id=None,
            last_trade_time=None,
            has_open_orders=False,
            has_recent_trades=False,
            step_size=0.001,
        )
        self.client.position_snapshots["BTCUSDT"] = snapshot
        self.client.position_snapshots["ETHUSDT"] = ExchangePositionSnapshot(
            symbol="ETHUSDT",
            base_asset="ETH",
            exchange_quantity=0.0,
            average_entry_price=None,
            last_order_id=None,
            last_trade_time=None,
            has_open_orders=False,
            has_recent_trades=False,
            step_size=0.001,
        )

        first_result = reconcile_runtime_state(settings=self.settings, client=self.client, state=state)
        apply_reconciliation_result(
            settings=self.settings,
            state=state,
            state_store=self.state_store,
            order_manager=self.order_manager,
            result=first_result,
            reconciliation_journal=self.reconciliation_journal,
            errors_journal=self.errors_journal,
            notifier=self.notifier,
            loggers=self.loggers,
        )
        self.assertEqual(len(self.notifier.messages), 1)

        state.acknowledged_startup_issues = [state.startup_issues[0].issue_key]
        second_result = reconcile_runtime_state(settings=self.settings, client=self.client, state=state)
        apply_reconciliation_result(
            settings=self.settings,
            state=state,
            state_store=self.state_store,
            order_manager=self.order_manager,
            result=second_result,
            reconciliation_journal=self.reconciliation_journal,
            errors_journal=self.errors_journal,
            notifier=self.notifier,
            loggers=self.loggers,
        )

        self.assertEqual(len(self.notifier.messages), 1)

    def test_repeated_reconciliation_keeps_single_issue_and_single_alert(self) -> None:
        state = BotState(
            open_positions={
                "BTCUSDT": Position(
                    symbol="BTCUSDT",
                    quantity=0.25,
                    entry_price=100.0,
                    stop_loss=98.0,
                    take_profit=104.0,
                    opened_at="2026-03-20T10:00:00+00:00",
                    order_id=1,
                    mode="demo",
                    quote_spent=25.0,
                    fee_paid_quote=0.1,
                )
            }
        )
        self.client.position_snapshots["BTCUSDT"] = ExchangePositionSnapshot(
            symbol="BTCUSDT",
            base_asset="BTC",
            exchange_quantity=0.0,
            average_entry_price=None,
            last_order_id=None,
            last_trade_time=None,
            has_open_orders=False,
            has_recent_trades=False,
            step_size=0.001,
        )
        self.client.position_snapshots["ETHUSDT"] = ExchangePositionSnapshot(
            symbol="ETHUSDT",
            base_asset="ETH",
            exchange_quantity=0.0,
            average_entry_price=None,
            last_order_id=None,
            last_trade_time=None,
            has_open_orders=False,
            has_recent_trades=False,
            step_size=0.001,
        )

        first_result = reconcile_runtime_state(settings=self.settings, client=self.client, state=state)
        apply_reconciliation_result(
            settings=self.settings,
            state=state,
            state_store=self.state_store,
            order_manager=self.order_manager,
            result=first_result,
            reconciliation_journal=self.reconciliation_journal,
            errors_journal=self.errors_journal,
            notifier=self.notifier,
            loggers=self.loggers,
        )

        second_result = reconcile_runtime_state(settings=self.settings, client=self.client, state=state)
        apply_reconciliation_result(
            settings=self.settings,
            state=state,
            state_store=self.state_store,
            order_manager=self.order_manager,
            result=second_result,
            reconciliation_journal=self.reconciliation_journal,
            errors_journal=self.errors_journal,
            notifier=self.notifier,
            loggers=self.loggers,
        )

        self.assertEqual(len(state.startup_issues), 1)
        self.assertEqual(len(state.alerted_startup_issues), 1)
        self.assertEqual(len(self.notifier.messages), 1)
        self.assertEqual(state.startup_issues[0].issue_key, state.alerted_startup_issues[0])
        self.assertEqual(state.last_reconciliation_status, "blocked-symbols-present")


if __name__ == "__main__":
    unittest.main()