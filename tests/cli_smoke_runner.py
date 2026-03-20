from __future__ import annotations

# ruff: noqa: E402

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import binance_bot.main as app_main
from binance_bot.core.models import BotState, ExchangePositionSnapshot, Position, StartupIssue
from binance_bot.core.models import SymbolFilters
from binance_bot.strategy.ema_cross import TradeSignal
from tests.fakes import FakeBinanceClient, FakeJournal, FakeLoggers, FakeNotifier, FakeStateStore, make_settings


class FakeCliStrategy:
    def __init__(self) -> None:
        self.signals_by_symbol: dict[str, TradeSignal] = {}

    def evaluate(self, symbol: str, candles, last_processed_candle):
        return self.signals_by_symbol[symbol]


class FakeCliRiskManager:
    def __init__(self) -> None:
        self.refresh_calls: list[tuple[BotState, str, float]] = []

    def refresh_trading_day(self, state: BotState, current_day: str, current_equity: float) -> None:
        self.refresh_calls.append((state, current_day, current_equity))
        if state.trading_day == current_day:
            return
        state.trading_day = current_day
        state.day_start_equity = current_equity
        state.daily_realized_pnl = 0.0
        state.consecutive_losses = 0
        state.halted_until_day = None

    @staticmethod
    def can_open_position(symbol: str, state: BotState, current_day: str) -> tuple[bool, str]:
        if symbol in state.blocked_symbols:
            return False, state.blocked_symbols[symbol]
        return True, "allowed"


class FakeCliOrderManager:
    def __init__(self) -> None:
        self.logged_signals: list[TradeSignal] = []
        self.open_calls: list[tuple[str, str]] = []
        self.close_calls: list[tuple[str, str]] = []
        self.restore_calls: list[str] = []
        self.drop_calls: list[str] = []

    def log_signal(self, signal: TradeSignal) -> None:
        self.logged_signals.append(signal)

    def open_long(self, signal: TradeSignal, filters, state: BotState, total_equity: float, free_quote_balance: float) -> None:
        self.open_calls.append((signal.symbol, signal.action))

    def close_position(self, symbol: str, reason: str, state: BotState) -> None:
        self.close_calls.append((symbol, reason))

    def restore_position_from_exchange(self, snapshot: ExchangePositionSnapshot, state: BotState) -> None:
        self.restore_calls.append(snapshot.symbol)
        state.open_positions[snapshot.symbol] = Position(
            symbol=snapshot.symbol,
            quantity=snapshot.exchange_quantity,
            entry_price=snapshot.average_entry_price or 0.0,
            stop_loss=98.0,
            take_profit=104.0,
            opened_at="2026-03-20T10:00:00+00:00",
            order_id=snapshot.last_order_id or 0,
            mode="demo",
            quote_spent=(snapshot.average_entry_price or 0.0) * snapshot.exchange_quantity,
            fee_paid_quote=0.0,
        )

    def drop_local_position(self, symbol: str, state: BotState) -> None:
        state.open_positions.pop(symbol, None)
        state.suspect_positions.pop(symbol, None)
        self.drop_calls.append(symbol)

    @staticmethod
    def mark_position_unrecoverable(symbol: str, reason: str, state: BotState) -> None:
        state.suspect_positions[symbol] = reason


def build_runtime_for_scenario(scenario: str, temp_dir: str) -> SimpleNamespace:
    settings = make_settings()
    settings.data_dir = Path(temp_dir)
    client = FakeBinanceClient()
    strategy = FakeCliStrategy()
    risk_manager = FakeCliRiskManager()
    order_manager = FakeCliOrderManager()
    settings.run_once = True
    client.portfolio_value = 1000.0
    client.free_quote_balance = 500.0
    client.filters_by_symbol = {
        "BTCUSDT": SymbolFilters(step_size=0.001, min_qty=0.001, min_notional=10.0, tick_size=0.01),
        "ETHUSDT": SymbolFilters(step_size=0.001, min_qty=0.001, min_notional=10.0, tick_size=0.01),
    }
    client.klines_by_symbol = {
        "BTCUSDT": ["btc-candles"],
        "ETHUSDT": ["eth-candles"],
    }
    strategy.signals_by_symbol = {
        "BTCUSDT": TradeSignal("BTCUSDT", "HOLD", "no-crossover", 100.0, 101.0, 99.0, 1710000000000),
        "ETHUSDT": TradeSignal("ETHUSDT", "HOLD", "no-crossover", 200.0, 201.0, 199.0, 1710000005000),
    }
    client.position_snapshots["ETHUSDT"] = ExchangePositionSnapshot(
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

    if scenario in {"inspect", "acknowledge", "repair-restore", "repair-restore-dry-run", "unblock-open"}:
        state = BotState(
            blocked_symbols={"BTCUSDT": "exchange-position-without-local-state"},
            startup_issues=[
                StartupIssue(
                    symbol="BTCUSDT",
                    issue_type="exchange-position-without-local-state",
                    local_qty=0.0,
                    exchange_qty=0.25,
                    action="block-symbol",
                    status="open",
                    message="needs review",
                )
            ],
        )
        client.position_snapshots["BTCUSDT"] = ExchangePositionSnapshot(
            symbol="BTCUSDT",
            base_asset="BTC",
            exchange_quantity=0.25,
            average_entry_price=100.0,
            last_order_id=1001,
            last_trade_time=1710000000000,
            has_open_orders=False,
            has_recent_trades=True,
            step_size=0.001,
        )
    elif scenario == "repair-drop":
        state = BotState(
            open_positions={
                "BTCUSDT": Position(
                    symbol="BTCUSDT",
                    quantity=0.25,
                    entry_price=100.0,
                    stop_loss=98.0,
                    take_profit=104.0,
                    opened_at="2026-03-20T10:00:00+00:00",
                    order_id=1001,
                    mode="demo",
                    quote_spent=25.0,
                    fee_paid_quote=0.1,
                )
            },
            blocked_symbols={"BTCUSDT": "local-position-missing-on-exchange"},
            startup_issues=[
                StartupIssue(
                    symbol="BTCUSDT",
                    issue_type="local-position-missing-on-exchange",
                    local_qty=0.25,
                    exchange_qty=0.0,
                    action="mark-unrecoverable",
                    status="open",
                    message="needs drop",
                )
            ],
        )
        client.position_snapshots["BTCUSDT"] = ExchangePositionSnapshot(
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
    elif scenario in {"unblock-closed", "unblock-closed-dry-run"}:
        state = BotState(blocked_symbols={"BTCUSDT": "resolved-manually"})
        client.position_snapshots["BTCUSDT"] = ExchangePositionSnapshot(
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
    elif scenario == "runtime-startup-check-only":
        settings.runtime_mode = "startup-check-only"
        state = BotState()
        client.position_snapshots["BTCUSDT"] = ExchangePositionSnapshot(
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
    elif scenario == "runtime-observe-only":
        settings.runtime_mode = "observe-only"
        state = BotState(
            open_positions={
                "BTCUSDT": Position(
                    symbol="BTCUSDT",
                    quantity=0.25,
                    entry_price=100.0,
                    stop_loss=98.0,
                    take_profit=104.0,
                    opened_at="2026-03-20T10:00:00+00:00",
                    order_id=1001,
                    mode="demo",
                    quote_spent=25.0,
                    fee_paid_quote=0.1,
                )
            }
        )
        strategy.signals_by_symbol = {
            "BTCUSDT": TradeSignal("BTCUSDT", "SELL", "ema20-crossed-below-ema50", 100.0, 99.0, 101.0, 1710000000000),
            "ETHUSDT": TradeSignal("ETHUSDT", "HOLD", "no-crossover", 200.0, 201.0, 199.0, 1710000005000),
        }
        client.position_snapshots["BTCUSDT"] = ExchangePositionSnapshot(
            symbol="BTCUSDT",
            base_asset="BTC",
            exchange_quantity=0.25,
            average_entry_price=100.0,
            last_order_id=1001,
            last_trade_time=1710000000000,
            has_open_orders=False,
            has_recent_trades=True,
            step_size=0.001,
        )
    elif scenario == "runtime-no-new-entries":
        settings.runtime_mode = "no-new-entries"
        state = BotState()
        strategy.signals_by_symbol = {
            "BTCUSDT": TradeSignal("BTCUSDT", "BUY", "ema20-crossed-above-ema50", 100.0, 101.0, 99.0, 1710000000000),
            "ETHUSDT": TradeSignal("ETHUSDT", "HOLD", "no-crossover", 200.0, 201.0, 199.0, 1710000005000),
        }
        client.position_snapshots["BTCUSDT"] = ExchangePositionSnapshot(
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
    else:
        raise ValueError(f"Unsupported smoke scenario: {scenario}")

    return SimpleNamespace(
        settings=settings,
        client=client,
        state_store=FakeStateStore(state),
        notifier=FakeNotifier(),
        signals_journal=FakeJournal(),
        trades_journal=FakeJournal(),
        errors_journal=FakeJournal(),
        reconciliation_journal=FakeJournal(),
        repair_journal=FakeJournal(),
        loggers=FakeLoggers(),
        strategy=strategy,
        risk_manager=risk_manager,
        order_manager=order_manager,
    )


def main() -> int:
    scenario = os.environ["CLI_SMOKE_SCENARIO"]
    temp_dir = os.environ["CLI_SMOKE_TMP_DIR"]
    runtime = build_runtime_for_scenario(scenario, temp_dir)
    with patch("binance_bot.main.build_runtime", return_value=runtime):
        app_main.run(sys.argv[1:])
    if scenario == "runtime-startup-check-only":
        state = runtime.state_store.load()
        print(
            json.dumps(
                {
                    "runtime_mode": runtime.settings.runtime_mode,
                    "last_reconciliation_status": state.last_reconciliation_status,
                    "notifier_messages": list(runtime.notifier.messages),
                }
            )
        )
    if scenario == "repair-restore-dry-run":
        state = runtime.state_store.load()
        print(
            json.dumps(
                {
                    "open_positions": sorted(state.open_positions.keys()),
                    "startup_issue_keys": [issue.issue_key for issue in state.startup_issues],
                    "repair_rows": len(runtime.repair_journal.rows),
                    "backups": len(list(runtime.settings.state_backups_dir.glob("*.json"))),
                    "restore_calls": list(runtime.order_manager.restore_calls),
                }
            )
        )
    if scenario == "unblock-closed-dry-run":
        state = runtime.state_store.load()
        print(
            json.dumps(
                {
                    "blocked_symbols": dict(state.blocked_symbols),
                    "repair_rows": len(runtime.repair_journal.rows),
                    "backups": len(list(runtime.settings.state_backups_dir.glob("*.json"))),
                }
            )
        )
    if scenario == "runtime-observe-only":
        state = runtime.state_store.load()
        print(
            json.dumps(
                {
                    "runtime_mode": runtime.settings.runtime_mode,
                    "logged_signals": [signal.symbol for signal in runtime.order_manager.logged_signals],
                    "close_calls": list(runtime.order_manager.close_calls),
                    "open_calls": list(runtime.order_manager.open_calls),
                    "open_positions": sorted(state.open_positions.keys()),
                    "last_processed_candle": dict(state.last_processed_candle),
                    "notifier_messages": list(runtime.notifier.messages),
                }
            )
        )
    if scenario == "runtime-no-new-entries":
        state = runtime.state_store.load()
        print(
            json.dumps(
                {
                    "runtime_mode": runtime.settings.runtime_mode,
                    "logged_signals": [signal.symbol for signal in runtime.order_manager.logged_signals],
                    "close_calls": list(runtime.order_manager.close_calls),
                    "open_calls": list(runtime.order_manager.open_calls),
                    "open_positions": sorted(state.open_positions.keys()),
                    "last_processed_candle": dict(state.last_processed_candle),
                    "notifier_messages": list(runtime.notifier.messages),
                }
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())