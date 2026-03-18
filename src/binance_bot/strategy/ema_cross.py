from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from binance_bot.core.models import Candle


@dataclass(slots=True)
class TradeSignal:
    symbol: str
    action: str
    reason: str
    price: float
    ema_fast: float
    ema_slow: float
    candle_close_time: int


class EmaCrossStrategy:
    def __init__(self, fast_period: int, slow_period: int, interval: str, stale_data_multiplier: int) -> None:
        if fast_period >= slow_period:
            raise ValueError("FAST_EMA_PERIOD must be lower than SLOW_EMA_PERIOD.")
        self._fast_period = fast_period
        self._slow_period = slow_period
        self._interval_minutes = self._parse_interval_minutes(interval)
        self._stale_data_multiplier = stale_data_multiplier

    def evaluate(self, symbol: str, candles: list[Candle], last_processed_candle: int | None) -> TradeSignal:
        closed_candles = [candle for candle in candles if candle.is_closed]
        if len(closed_candles) < self._slow_period + 2:
            return TradeSignal(symbol, "HOLD", "not-enough-data", 0.0, 0.0, 0.0, 0)

        latest_closed = closed_candles[-1]
        if last_processed_candle and latest_closed.close_time <= last_processed_candle:
            return TradeSignal(symbol, "HOLD", "candle-already-processed", latest_closed.close_price, 0.0, 0.0, latest_closed.close_time)

        if not self._is_fresh(latest_closed):
            return TradeSignal(symbol, "HOLD", "stale-market-data", latest_closed.close_price, 0.0, 0.0, latest_closed.close_time)

        closes = [candle.close_price for candle in closed_candles]
        fast_ema_series = self._ema_series(closes, self._fast_period)
        slow_ema_series = self._ema_series(closes, self._slow_period)

        prev_fast, curr_fast = fast_ema_series[-2], fast_ema_series[-1]
        prev_slow, curr_slow = slow_ema_series[-2], slow_ema_series[-1]

        if prev_fast <= prev_slow and curr_fast > curr_slow:
            return TradeSignal(
                symbol=symbol,
                action="BUY",
                reason="ema20-crossed-above-ema50",
                price=latest_closed.close_price,
                ema_fast=curr_fast,
                ema_slow=curr_slow,
                candle_close_time=latest_closed.close_time,
            )

        if prev_fast >= prev_slow and curr_fast < curr_slow:
            return TradeSignal(
                symbol=symbol,
                action="SELL",
                reason="ema20-crossed-below-ema50",
                price=latest_closed.close_price,
                ema_fast=curr_fast,
                ema_slow=curr_slow,
                candle_close_time=latest_closed.close_time,
            )

        return TradeSignal(
            symbol=symbol,
            action="HOLD",
            reason="no-crossover",
            price=latest_closed.close_price,
            ema_fast=curr_fast,
            ema_slow=curr_slow,
            candle_close_time=latest_closed.close_time,
        )

    def _is_fresh(self, candle: Candle) -> bool:
        candle_time = datetime.fromtimestamp(candle.close_time / 1000, tz=UTC)
        age_seconds = (datetime.now(tz=UTC) - candle_time).total_seconds()
        max_age_seconds = self._interval_minutes * 60 * self._stale_data_multiplier
        return age_seconds <= max_age_seconds

    @staticmethod
    def _ema_series(values: list[float], period: int) -> list[float]:
        multiplier = 2 / (period + 1)
        series = [values[0]]
        for value in values[1:]:
            series.append((value - series[-1]) * multiplier + series[-1])
        return series

    @staticmethod
    def _parse_interval_minutes(interval: str) -> int:
        if interval != "15m":
            raise ValueError("Only 15m timeframe is supported in this version.")
        return 15
