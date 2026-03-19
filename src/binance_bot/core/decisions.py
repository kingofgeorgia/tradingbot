from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class RiskDecision:
    allowed: bool
    reason: str


@dataclass(slots=True)
class CloseDecision:
    should_close: bool
    reason: str
    error_scope: str | None


@dataclass(slots=True)
class SignalDecision:
    action: str
    should_log_signal: bool
    reason: str


def decide_risk_entry(allowed: bool, reason: str) -> RiskDecision:
    return RiskDecision(allowed=allowed, reason=reason)


def decide_position_close(current_price: float, stop_loss: float, take_profit: float) -> CloseDecision:
    if current_price <= stop_loss:
        return CloseDecision(should_close=True, reason="stop-loss-hit", error_scope="stop-loss-close")
    if current_price >= take_profit:
        return CloseDecision(should_close=True, reason="take-profit-hit", error_scope="take-profit-close")
    return CloseDecision(should_close=False, reason="no-close-condition", error_scope=None)


def decide_signal_action(signal_action: str, signal_reason: str, has_open_position: bool) -> SignalDecision:
    if signal_action == "HOLD":
        return SignalDecision(action="ignore", should_log_signal=False, reason="hold-signal")
    if signal_action == "SELL":
        if has_open_position:
            return SignalDecision(action="close-position", should_log_signal=True, reason=signal_reason)
        return SignalDecision(
            action="ignore",
            should_log_signal=True,
            reason="sell-without-open-position",
        )
    if signal_action == "BUY":
        return SignalDecision(action="evaluate-buy", should_log_signal=True, reason=signal_reason)
    return SignalDecision(action="ignore", should_log_signal=False, reason="unsupported-signal-action")