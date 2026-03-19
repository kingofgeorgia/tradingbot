from __future__ import annotations

from dataclasses import dataclass

from binance_bot.core.models import ExchangePositionSnapshot, Position


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


@dataclass(slots=True)
class ReconciliationDecision:
    action: str
    issue_type: str | None
    reason: str


@dataclass(slots=True)
class SymbolBlockDecision:
    blocked: bool
    reason: str
    suspect_position: bool


@dataclass(slots=True)
class StateRepairDecision:
    action: str
    should_restore: bool
    reason: str


@dataclass(slots=True)
class ManualRepairDecision:
    allowed: bool
    action: str
    reason: str


@dataclass(slots=True)
class IssueAcknowledgementDecision:
    should_acknowledge: bool
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


def decide_state_repair(
    local_position: Position | None,
    exchange_snapshot: ExchangePositionSnapshot,
) -> StateRepairDecision:
    if local_position is not None:
        return StateRepairDecision(action="keep-local-state", should_restore=False, reason="local-state-present")
    if exchange_snapshot.exchange_quantity <= 0:
        return StateRepairDecision(action="no-repair-needed", should_restore=False, reason="no-exchange-position")
    if exchange_snapshot.average_entry_price is None or exchange_snapshot.last_order_id is None:
        return StateRepairDecision(action="manual-review-required", should_restore=False, reason="insufficient-exchange-data")
    return StateRepairDecision(action="restore-from-exchange", should_restore=True, reason="recoverable-from-exchange")


def decide_reconciliation_action(
    local_position: Position | None,
    exchange_snapshot: ExchangePositionSnapshot,
) -> ReconciliationDecision:
    quantity_tolerance = max(exchange_snapshot.step_size / 2, 1e-12)
    local_qty = local_position.quantity if local_position is not None else 0.0
    exchange_qty = exchange_snapshot.exchange_quantity

    if local_position is not None and exchange_qty <= quantity_tolerance:
        return ReconciliationDecision(
            action="mark-unrecoverable",
            issue_type="local-position-missing-on-exchange",
            reason="local-position-missing-on-exchange",
        )

    if local_position is None and exchange_qty > quantity_tolerance:
        repair_decision = decide_state_repair(local_position, exchange_snapshot)
        if repair_decision.should_restore:
            return ReconciliationDecision(
                action="restore-position",
                issue_type="exchange-position-recovered",
                reason=repair_decision.reason,
            )
        return ReconciliationDecision(
            action="block-symbol",
            issue_type="exchange-position-without-local-state",
            reason=repair_decision.reason,
        )

    if local_position is not None and abs(local_qty - exchange_qty) > quantity_tolerance:
        return ReconciliationDecision(
            action="block-symbol",
            issue_type="quantity-mismatch",
            reason="quantity-mismatch-between-local-and-exchange",
        )

    return ReconciliationDecision(action="ready", issue_type=None, reason="state-aligned")


def decide_symbol_block(action: str, reason: str) -> SymbolBlockDecision:
    if action in {"block-symbol", "mark-unrecoverable"}:
        return SymbolBlockDecision(blocked=True, reason=reason, suspect_position=True)
    return SymbolBlockDecision(blocked=False, reason=reason, suspect_position=False)


def decide_manual_repair_action(*, requested_action: str, has_open_issue: bool, can_restore: bool) -> ManualRepairDecision:
    if requested_action == "acknowledge":
        return ManualRepairDecision(allowed=has_open_issue, action=requested_action, reason="acknowledge-open-issue")
    if requested_action == "keep-blocked":
        return ManualRepairDecision(allowed=has_open_issue, action=requested_action, reason="keep-symbol-blocked")
    if requested_action == "restore-from-exchange":
        if not has_open_issue:
            return ManualRepairDecision(allowed=False, action=requested_action, reason="no-open-issue")
        if not can_restore:
            return ManualRepairDecision(allowed=False, action=requested_action, reason="restore-not-supported")
        return ManualRepairDecision(allowed=True, action=requested_action, reason="restore-approved")
    if requested_action == "drop-local-state":
        return ManualRepairDecision(allowed=has_open_issue, action=requested_action, reason="drop-local-state-approved")
    if requested_action == "unblock":
        return ManualRepairDecision(allowed=has_open_issue, action=requested_action, reason="requires-unblock-check")
    return ManualRepairDecision(allowed=False, action=requested_action, reason="unsupported-manual-action")


def decide_unblock_allowed(*, has_open_issue: bool, symbol_blocked: bool, state_aligned: bool) -> ManualRepairDecision:
    if not symbol_blocked:
        return ManualRepairDecision(allowed=False, action="unblock", reason="symbol-not-blocked")
    if has_open_issue:
        return ManualRepairDecision(allowed=False, action="unblock", reason="startup-issue-still-open")
    if not state_aligned:
        return ManualRepairDecision(allowed=False, action="unblock", reason="state-not-aligned")
    return ManualRepairDecision(allowed=True, action="unblock", reason="symbol-can-be-unblocked")


def decide_issue_acknowledgement(*, issue_key: str, acknowledged_issue_keys: list[str]) -> IssueAcknowledgementDecision:
    if not issue_key:
        return IssueAcknowledgementDecision(should_acknowledge=False, reason="missing-issue-key")
    if issue_key in acknowledged_issue_keys:
        return IssueAcknowledgementDecision(should_acknowledge=False, reason="issue-already-acknowledged")
    return IssueAcknowledgementDecision(should_acknowledge=True, reason="issue-acknowledged")