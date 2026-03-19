from __future__ import annotations

from binance_bot.core.models import RuntimeStatusReport


def build_runtime_status_report(*, settings, state) -> RuntimeStatusReport:
    return RuntimeStatusReport(
        runtime_mode=settings.runtime_mode,
        blocked_symbols=dict(state.blocked_symbols),
        suspect_positions=dict(state.suspect_positions),
        open_positions=sorted(state.open_positions),
        startup_issue_keys=[issue.issue_key for issue in state.startup_issues],
        last_reconciled_at=state.last_reconciled_at,
        last_reconciliation_status=state.last_reconciliation_status,
        last_manual_review_at=state.last_manual_review_at,
    )


def format_status_report(report: RuntimeStatusReport) -> str:
    blocked = ", ".join(sorted(report.blocked_symbols)) or "none"
    suspect = ", ".join(sorted(report.suspect_positions)) or "none"
    positions = ", ".join(report.open_positions) or "none"
    issues = ", ".join(report.startup_issue_keys) or "none"
    return (
        f"Runtime mode: {report.runtime_mode}\n"
        f"Open positions: {positions}\n"
        f"Blocked symbols: {blocked}\n"
        f"Suspect positions: {suspect}\n"
        f"Startup issues: {issues}\n"
        f"Last reconciled at: {report.last_reconciled_at or 'n/a'}\n"
        f"Last reconciliation status: {report.last_reconciliation_status or 'n/a'}\n"
        f"Last manual review at: {report.last_manual_review_at or 'n/a'}"
    )