from __future__ import annotations

from binance_bot.core.models import RuntimeStatusReport, StartupIssue, SymbolRuntimeStatus


def build_runtime_status_report(*, settings, state) -> RuntimeStatusReport:
    symbol_statuses = _build_symbol_runtime_statuses(settings=settings, state=state)
    return RuntimeStatusReport(
        runtime_mode=settings.runtime_mode,
        blocked_symbols=dict(state.blocked_symbols),
        suspect_positions=dict(state.suspect_positions),
        open_positions=sorted(state.open_positions),
        startup_issue_keys=[issue.issue_key for issue in state.startup_issues],
        symbol_statuses=symbol_statuses,
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
    return (
        f"Runtime mode: {report.runtime_mode}\n"
        f"Open positions: {positions}\n"
        f"Blocked symbols: {blocked}\n"
        f"Suspect positions: {suspect}\n"
        f"Startup issues: {issues}\n"
        f"Per-symbol status:\n{symbol_details}\n"
        f"Last reconciled at: {report.last_reconciled_at or 'n/a'}\n"
        f"Last reconciliation status: {report.last_reconciliation_status or 'n/a'}\n"
        f"Last manual review at: {report.last_manual_review_at or 'n/a'}"
    )


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