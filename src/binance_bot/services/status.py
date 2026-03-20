from __future__ import annotations

import json

from binance_bot.core.models import ManualReviewItem, RuntimeStatusReport, StartupIssue, SymbolRuntimeStatus


def build_runtime_status_report(*, settings, state) -> RuntimeStatusReport:
    symbol_statuses = _build_symbol_runtime_statuses(settings=settings, state=state)
    manual_review_queue = _build_manual_review_queue(state=state)
    return RuntimeStatusReport(
        runtime_mode=settings.runtime_mode,
        blocked_symbols=dict(state.blocked_symbols),
        suspect_positions=dict(state.suspect_positions),
        open_positions=sorted(state.open_positions),
        startup_issue_keys=[issue.issue_key for issue in state.startup_issues],
        symbol_statuses=symbol_statuses,
        manual_review_queue=manual_review_queue,
        last_reconciled_at=state.last_reconciled_at,
        last_reconciliation_status=state.last_reconciliation_status,
        last_manual_review_at=state.last_manual_review_at,
    )


def format_status_report(report: RuntimeStatusReport) -> str:
    blocked = ", ".join(sorted(report.blocked_symbols)) or "none"
    suspect = ", ".join(sorted(report.suspect_positions)) or "none"
    positions = ", ".join(report.open_positions) or "none"
    issues = ", ".join(report.startup_issue_keys) or "none"
    symbol_details = "\n".join(_format_symbol_status_line(status) for status in report.symbol_statuses) or "none"
    review_queue = format_manual_review_queue(report)
    return (
        f"Runtime mode: {report.runtime_mode}\n"
        f"Open positions: {positions}\n"
        f"Blocked symbols: {blocked}\n"
        f"Suspect positions: {suspect}\n"
        f"Startup issues: {issues}\n"
        f"Manual review queue size: {len(report.manual_review_queue)}\n"
        f"Manual review queue:\n{review_queue}\n"
        f"Per-symbol status:\n{symbol_details}\n"
        f"Last reconciled at: {report.last_reconciled_at or 'n/a'}\n"
        f"Last reconciliation status: {report.last_reconciliation_status or 'n/a'}\n"
        f"Last manual review at: {report.last_manual_review_at or 'n/a'}"
    )


def format_status_report_json(report: RuntimeStatusReport) -> str:
    return json.dumps(runtime_status_report_to_dict(report), indent=2)


def format_manual_review_queue(report: RuntimeStatusReport) -> str:
    return "\n".join(_format_manual_review_item(item) for item in report.manual_review_queue) or "none"


def format_manual_review_queue_json(report: RuntimeStatusReport) -> str:
    return json.dumps(manual_review_queue_to_dict(report), indent=2)


def format_runtime_health_notification(*, app_mode: str, report: RuntimeStatusReport, cycle_number: int) -> str:
    blocked = ", ".join(sorted(report.blocked_symbols)) or "none"
    positions = ", ".join(report.open_positions) or "none"
    issues = ", ".join(report.startup_issue_keys) or "none"
    return (
        f"[{app_mode}] Runtime heartbeat\n"
        f"Cycle: {cycle_number}\n"
        f"Runtime mode: {report.runtime_mode}\n"
        f"Open positions: {positions}\n"
        f"Blocked symbols: {blocked}\n"
        f"Startup issues: {issues}\n"
        f"Last reconciliation status: {report.last_reconciliation_status or 'n/a'}"
    )

def format_startup_summary_notification(*, app_mode: str, report: RuntimeStatusReport) -> str:
    blocked = ", ".join(sorted(report.blocked_symbols)) or "none"
    suspect = ", ".join(sorted(report.suspect_positions)) or "none"
    positions = ", ".join(report.open_positions) or "none"
    issues = ", ".join(report.startup_issue_keys) or "none"
    return (
        f"[{app_mode}] Startup summary\n"
        f"Runtime mode: {report.runtime_mode}\n"
        f"Open positions: {positions}\n"
        f"Blocked symbols: {blocked}\n"
        f"Suspect positions: {suspect}\n"
        f"Startup issues: {issues}\n"
        f"Last reconciliation status: {report.last_reconciliation_status or 'n/a'}"
    )


def runtime_status_report_to_dict(report: RuntimeStatusReport) -> dict[str, object]:
    return {
        "runtime_mode": report.runtime_mode,
        "open_positions": list(report.open_positions),
        "blocked_symbols": dict(report.blocked_symbols),
        "suspect_positions": dict(report.suspect_positions),
        "startup_issue_keys": list(report.startup_issue_keys),
        "symbol_statuses": [_symbol_status_to_dict(status) for status in report.symbol_statuses],
        "last_reconciled_at": report.last_reconciled_at,
        "last_reconciliation_status": report.last_reconciliation_status,
        "last_manual_review_at": report.last_manual_review_at,
        "manual_review_queue": [_manual_review_item_to_dict(item) for item in report.manual_review_queue],
    }


def manual_review_queue_to_dict(report: RuntimeStatusReport) -> dict[str, object]:
    return {
        "runtime_mode": report.runtime_mode,
        "queue_size": len(report.manual_review_queue),
        "manual_review_queue": [_manual_review_item_to_dict(item) for item in report.manual_review_queue],
        "last_reconciled_at": report.last_reconciled_at,
        "last_reconciliation_status": report.last_reconciliation_status,
        "last_manual_review_at": report.last_manual_review_at,
    }


def _build_symbol_runtime_statuses(*, settings, state) -> list[SymbolRuntimeStatus]:
    issues_by_symbol: dict[str, StartupIssue] = {issue.symbol: issue for issue in state.startup_issues}
    acknowledged_issue_keys = set(state.acknowledged_startup_issues)
    statuses: list[SymbolRuntimeStatus] = []

    for symbol in settings.symbols:
        issue = issues_by_symbol.get(symbol)
        issue_key = issue.issue_key if issue is not None else None
        blocked_reason = state.blocked_symbols.get(symbol)
        suspect_reason = state.suspect_positions.get(symbol)
        has_open_position = symbol in state.open_positions

        if blocked_reason is not None:
            status = "blocked"
            reason = blocked_reason
        elif suspect_reason is not None:
            status = "suspect"
            reason = suspect_reason
        elif has_open_position:
            status = "position-open"
            reason = "local-position-active"
        else:
            status = "ready"
            reason = "state-aligned"

        statuses.append(
            SymbolRuntimeStatus(
                symbol=symbol,
                status=status,
                blocked=blocked_reason is not None,
                suspect_position=suspect_reason is not None,
                reason=reason,
                effective_runtime_mode=settings.get_effective_symbol_runtime_mode(symbol),
                has_open_position=has_open_position,
                startup_issue_key=issue_key,
                issue_acknowledged=bool(issue_key and issue_key in acknowledged_issue_keys),
                last_manual_action=state.last_manual_action_by_symbol.get(symbol),
            )
        )

    return statuses


def _build_manual_review_queue(*, state) -> list[ManualReviewItem]:
    issue_by_symbol = {issue.symbol: issue for issue in state.startup_issues}
    acknowledged_issue_keys = set(state.acknowledged_startup_issues)
    symbols = sorted(set(issue_by_symbol) | set(state.blocked_symbols) | set(state.suspect_positions))
    queue: list[ManualReviewItem] = []

    for symbol in symbols:
        issue = issue_by_symbol.get(symbol)
        blocked_reason = state.blocked_symbols.get(symbol)
        suspect_reason = state.suspect_positions.get(symbol)
        last_manual_action = state.last_manual_action_by_symbol.get(symbol)

        if issue is not None:
            acknowledged = issue.issue_key in acknowledged_issue_keys
            queue.append(
                ManualReviewItem(
                    queue_key=issue.issue_key,
                    symbol=symbol,
                    category="startup-issue",
                    priority="high" if not acknowledged else "medium",
                    reason=issue.message or issue.issue_type,
                    recommended_action=_recommend_action_for_issue(issue=issue, acknowledged=acknowledged),
                    startup_issue_key=issue.issue_key,
                    issue_acknowledged=acknowledged,
                    last_manual_action=last_manual_action,
                )
            )
            continue

        if blocked_reason is not None:
            queue.append(
                ManualReviewItem(
                    queue_key=f"{symbol}:blocked-symbol",
                    symbol=symbol,
                    category="blocked-symbol",
                    priority="medium",
                    reason=blocked_reason,
                    recommended_action="inspect -> unblock when aligned",
                    last_manual_action=last_manual_action,
                )
            )
            continue

        if suspect_reason is not None:
            queue.append(
                ManualReviewItem(
                    queue_key=f"{symbol}:suspect-position",
                    symbol=symbol,
                    category="suspect-position",
                    priority="medium",
                    reason=suspect_reason,
                    recommended_action="inspect -> review position state",
                    last_manual_action=last_manual_action,
                )
            )

    return queue


def _format_symbol_status_line(status: SymbolRuntimeStatus) -> str:
    open_position = "yes" if status.has_open_position else "no"
    blocked = "yes" if status.blocked else "no"
    suspect = "yes" if status.suspect_position else "no"
    issue = status.startup_issue_key or "none"
    acknowledged = "yes" if status.issue_acknowledged else "no"
    last_manual_action = status.last_manual_action or "none"
    return (
        f"- {status.symbol}: category={status.status}; effective_mode={status.effective_runtime_mode}; "
        f"open_position={open_position}; blocked={blocked}; suspect={suspect}; issue={issue}; "
        f"acknowledged={acknowledged}; last_manual_action={last_manual_action}; reason={status.reason}"
    )


def _format_manual_review_item(item: ManualReviewItem) -> str:
    issue = item.startup_issue_key or "none"
    acknowledged = "yes" if item.issue_acknowledged else "no"
    last_manual_action = item.last_manual_action or "none"
    return (
        f"- {item.symbol}: priority={item.priority}; category={item.category}; issue={issue}; "
        f"acknowledged={acknowledged}; last_manual_action={last_manual_action}; "
        f"recommended_action={item.recommended_action}; reason={item.reason}"
    )


def _symbol_status_to_dict(status: SymbolRuntimeStatus) -> dict[str, object]:
    return {
        "symbol": status.symbol,
        "category": status.status,
        "effective_runtime_mode": status.effective_runtime_mode,
        "has_open_position": status.has_open_position,
        "blocked": status.blocked,
        "suspect_position": status.suspect_position,
        "startup_issue_key": status.startup_issue_key,
        "issue_acknowledged": status.issue_acknowledged,
        "last_manual_action": status.last_manual_action,
        "reason": status.reason,
    }


def _manual_review_item_to_dict(item: ManualReviewItem) -> dict[str, object]:
    return {
        "queue_key": item.queue_key,
        "symbol": item.symbol,
        "category": item.category,
        "priority": item.priority,
        "startup_issue_key": item.startup_issue_key,
        "issue_acknowledged": item.issue_acknowledged,
        "last_manual_action": item.last_manual_action,
        "recommended_action": item.recommended_action,
        "reason": item.reason,
    }


def _recommend_action_for_issue(*, issue: StartupIssue, acknowledged: bool) -> str:
    repair_action = _repair_action_for_issue(issue)
    if not acknowledged and repair_action is not None:
        return f"acknowledge -> {repair_action}"
    if not acknowledged:
        return "acknowledge"
    if repair_action is not None:
        return repair_action
    return "inspect"


def _repair_action_for_issue(issue: StartupIssue) -> str | None:
    if issue.issue_type == "exchange-position-without-local-state":
        return "repair restore-from-exchange"
    if issue.issue_type == "local-position-missing-on-exchange":
        return "repair drop-local-state"
    return None