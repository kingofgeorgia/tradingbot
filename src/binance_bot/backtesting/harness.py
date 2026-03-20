from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from binance_bot.core.models import Candle
from binance_bot.strategy.ema_cross import EmaCrossStrategy


@dataclass(slots=True)
class BacktestTrade:
    symbol: str
    entry_time: int
    exit_time: int
    entry_price: float
    exit_price: float
    quantity: float
    pnl_quote: float
    pnl_pct: float


@dataclass(slots=True)
class BacktestReport:
    symbol: str
    candle_count: int
    actionable_signal_count: int
    buy_signal_count: int
    sell_signal_count: int
    completed_trade_count: int
    open_trade: dict[str, float | int] | None
    total_pnl_quote: float
    win_rate: float
    trades: list[BacktestTrade]


def load_candles_from_csv(csv_path: Path) -> list[Candle]:
    candles: list[Candle] = []
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            candles.append(
                Candle(
                    open_time=int(row["open_time"]),
                    open_price=float(row["open_price"]),
                    high_price=float(row["high_price"]),
                    low_price=float(row["low_price"]),
                    close_price=float(row["close_price"]),
                    volume=float(row["volume"]),
                    close_time=int(row["close_time"]),
                    is_closed=_parse_bool(row.get("is_closed", "true")),
                )
            )
    return candles


def run_backtest(
    *,
    strategy: EmaCrossStrategy,
    symbol: str,
    candles: list[Candle],
    position_size_quote: float = 1000.0,
) -> BacktestReport:
    last_processed_candle: int | None = None
    buy_signal_count = 0
    sell_signal_count = 0
    trades: list[BacktestTrade] = []
    open_trade: dict[str, float | int] | None = None

    for index in range(len(candles)):
        candle_slice = candles[: index + 1]
        latest_closed = _latest_closed_candle(candle_slice)
        reference_time_utc = None
        if latest_closed is not None:
            reference_time_utc = datetime.fromtimestamp(latest_closed.close_time / 1000, tz=UTC)

        signal = strategy.evaluate(
            symbol,
            candle_slice,
            last_processed_candle,
            reference_time_utc=reference_time_utc,
        )
        if signal.candle_close_time:
            last_processed_candle = signal.candle_close_time

        if signal.action == "BUY":
            buy_signal_count += 1
            if open_trade is None and signal.price > 0:
                quantity = position_size_quote / signal.price
                open_trade = {
                    "entry_time": signal.candle_close_time,
                    "entry_price": signal.price,
                    "quantity": quantity,
                }
        elif signal.action == "SELL":
            sell_signal_count += 1
            if open_trade is not None:
                pnl_quote = (signal.price - float(open_trade["entry_price"])) * float(open_trade["quantity"])
                pnl_pct = 0.0
                if float(open_trade["entry_price"]) > 0:
                    pnl_pct = ((signal.price / float(open_trade["entry_price"])) - 1.0) * 100
                trades.append(
                    BacktestTrade(
                        symbol=symbol,
                        entry_time=int(open_trade["entry_time"]),
                        exit_time=signal.candle_close_time,
                        entry_price=float(open_trade["entry_price"]),
                        exit_price=signal.price,
                        quantity=float(open_trade["quantity"]),
                        pnl_quote=pnl_quote,
                        pnl_pct=pnl_pct,
                    )
                )
                open_trade = None

    wins = sum(1 for trade in trades if trade.pnl_quote > 0)
    win_rate = 0.0 if not trades else wins / len(trades)
    return BacktestReport(
        symbol=symbol,
        candle_count=len(candles),
        actionable_signal_count=buy_signal_count + sell_signal_count,
        buy_signal_count=buy_signal_count,
        sell_signal_count=sell_signal_count,
        completed_trade_count=len(trades),
        open_trade=open_trade,
        total_pnl_quote=sum(trade.pnl_quote for trade in trades),
        win_rate=win_rate,
        trades=trades,
    )


def format_backtest_report(report: BacktestReport) -> str:
    open_trade = "none"
    if report.open_trade is not None:
        open_trade = (
            f"entry_time={report.open_trade['entry_time']}; "
            f"entry_price={float(report.open_trade['entry_price']):.4f}; "
            f"quantity={float(report.open_trade['quantity']):.8f}"
        )
    trade_lines = "\n".join(_format_backtest_trade(trade) for trade in report.trades) or "none"
    return (
        f"Backtest symbol: {report.symbol}\n"
        f"Candles: {report.candle_count}\n"
        f"Actionable signals: {report.actionable_signal_count}\n"
        f"BUY signals: {report.buy_signal_count}\n"
        f"SELL signals: {report.sell_signal_count}\n"
        f"Completed trades: {report.completed_trade_count}\n"
        f"Total PnL quote: {report.total_pnl_quote:.4f}\n"
        f"Win rate: {report.win_rate:.2%}\n"
        f"Open trade: {open_trade}\n"
        f"Trades:\n{trade_lines}"
    )


def format_backtest_report_json(report: BacktestReport) -> str:
    payload = {
        "symbol": report.symbol,
        "candle_count": report.candle_count,
        "actionable_signal_count": report.actionable_signal_count,
        "buy_signal_count": report.buy_signal_count,
        "sell_signal_count": report.sell_signal_count,
        "completed_trade_count": report.completed_trade_count,
        "open_trade": report.open_trade,
        "total_pnl_quote": report.total_pnl_quote,
        "win_rate": report.win_rate,
        "trades": [asdict(trade) for trade in report.trades],
    }
    return json.dumps(payload, indent=2)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a strategy-only EMA backtest from CSV candles.")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--candles-csv", required=True, type=Path)
    parser.add_argument("--fast-period", type=int, default=20)
    parser.add_argument("--slow-period", type=int, default=50)
    parser.add_argument("--interval", default="15m")
    parser.add_argument("--stale-data-multiplier", type=int, default=2)
    parser.add_argument("--position-size-quote", type=float, default=1000.0)
    parser.add_argument("--json", action="store_true")
    return parser


def run_cli(argv: list[str] | None = None) -> int:
    parser = build_argument_parser()
    arguments = parser.parse_args(argv)
    strategy = EmaCrossStrategy(
        fast_period=arguments.fast_period,
        slow_period=arguments.slow_period,
        interval=arguments.interval,
        stale_data_multiplier=arguments.stale_data_multiplier,
    )
    candles = load_candles_from_csv(arguments.candles_csv)
    report = run_backtest(
        strategy=strategy,
        symbol=arguments.symbol,
        candles=candles,
        position_size_quote=arguments.position_size_quote,
    )
    if arguments.json:
        print(format_backtest_report_json(report))
    else:
        print(format_backtest_report(report))
    return 0


def _format_backtest_trade(trade: BacktestTrade) -> str:
    return (
        f"- {trade.symbol}: entry_time={trade.entry_time}; exit_time={trade.exit_time}; "
        f"entry_price={trade.entry_price:.4f}; exit_price={trade.exit_price:.4f}; "
        f"quantity={trade.quantity:.8f}; pnl_quote={trade.pnl_quote:.4f}; pnl_pct={trade.pnl_pct:.4f}"
    )


def _latest_closed_candle(candles: list[Candle]) -> Candle | None:
    for candle in reversed(candles):
        if candle.is_closed:
            return candle
    return None


def _parse_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


if __name__ == "__main__":
    raise SystemExit(run_cli())