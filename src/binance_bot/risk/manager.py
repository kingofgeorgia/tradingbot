from __future__ import annotations

from binance_bot.config import Settings
from binance_bot.core.models import BotState, SymbolFilters
from binance_bot.core.rounding import round_down_to_step


class RiskManager:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def refresh_trading_day(self, state: BotState, current_day: str, current_equity: float) -> None:
        if state.trading_day == current_day:
            return
        state.trading_day = current_day
        state.day_start_equity = current_equity
        state.daily_realized_pnl = 0.0
        state.consecutive_losses = 0
        state.halted_until_day = None

    def can_open_position(self, symbol: str, state: BotState, current_day: str) -> tuple[bool, str]:
        if state.halted_until_day == current_day:
            return False, "trading-halted-for-the-day"
        if symbol in state.blocked_symbols:
            return False, state.blocked_symbols[symbol]
        if symbol in state.open_positions:
            return False, "position-already-open-for-symbol"
        if len(state.open_positions) >= self._settings.max_open_positions_total:
            return False, "max-open-positions-total-reached"
        return True, "allowed"

    def calculate_order_quantity(
        self,
        symbol: str,
        entry_price: float,
        total_equity: float,
        free_quote_balance: float,
        filters: SymbolFilters,
    ) -> float:
        risk_budget = total_equity * self._settings.get_symbol_risk_per_trade_pct(symbol)
        max_notional_by_risk = risk_budget / self._settings.stop_loss_pct
        max_notional_by_balance = total_equity * self._settings.get_symbol_max_position_pct(symbol)
        available_quote_budget = free_quote_balance * 0.98
        trade_notional = min(max_notional_by_risk, max_notional_by_balance, available_quote_budget)

        if trade_notional <= 0:
            raise ValueError("No free quote balance available for a new trade.")
        if trade_notional < filters.min_notional:
            raise ValueError("Calculated notional is lower than Binance minimum notional.")

        raw_quantity = trade_notional / entry_price
        quantity = self._round_down(raw_quantity, filters.step_size)

        if quantity < filters.min_qty:
            raise ValueError("Calculated quantity is lower than Binance minimum quantity.")
        if quantity * entry_price < filters.min_notional:
            raise ValueError("Calculated quantity does not satisfy minimum notional.")
        return quantity

    def register_closed_trade(self, state: BotState, pnl: float, current_day: str) -> str | None:
        state.daily_realized_pnl += pnl
        state.total_closed_trades += 1

        if pnl < 0:
            state.consecutive_losses += 1
        else:
            state.consecutive_losses = 0

        daily_loss_limit_amount = state.day_start_equity * self._settings.daily_loss_limit_pct
        if daily_loss_limit_amount > 0 and state.daily_realized_pnl <= -daily_loss_limit_amount:
            state.halted_until_day = current_day
            return "daily-loss-limit-reached"
        if state.consecutive_losses >= self._settings.max_consecutive_losses:
            state.halted_until_day = current_day
            return "max-consecutive-losses-reached"
        return None

    @staticmethod
    def _round_down(value: float, step_size: float) -> float:
        return round_down_to_step(value, step_size)
