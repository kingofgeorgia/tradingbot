from __future__ import annotations

# ruff: noqa: E402

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
from tests.fakes import FakeBinanceClient, FakeJournal, FakeLoggers, FakeStateStore, make_settings


class FakeCliOrderManager:
    def restore_position_from_exchange(self, snapshot: ExchangePositionSnapshot, state: BotState) -> None:
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

    @staticmethod
    def drop_local_position(symbol: str, state: BotState) -> None:
        state.open_positions.pop(symbol, None)
        state.suspect_positions.pop(symbol, None)


def build_runtime_for_scenario(scenario: str, temp_dir: str) -> SimpleNamespace:
    settings = make_settings()
    settings.data_dir = Path(temp_dir)
    client = FakeBinanceClient()
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

    if scenario in {"inspect", "acknowledge", "repair-restore", "unblock-open"}:
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
    elif scenario == "unblock-closed":
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
    else:
        raise ValueError(f"Unsupported smoke scenario: {scenario}")

    return SimpleNamespace(
        settings=settings,
        client=client,
        state_store=FakeStateStore(state),
        repair_journal=FakeJournal(),
        loggers=FakeLoggers(),
        order_manager=FakeCliOrderManager(),
    )


def main() -> int:
    scenario = os.environ["CLI_SMOKE_SCENARIO"]
    temp_dir = os.environ["CLI_SMOKE_TMP_DIR"]
    runtime = build_runtime_for_scenario(scenario, temp_dir)
    with patch("binance_bot.main.build_runtime", return_value=runtime):
        app_main.run(sys.argv[1:])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())