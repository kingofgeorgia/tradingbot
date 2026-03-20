from __future__ import annotations

from binance_bot.core.decisions import decide_reconciliation_action, decide_symbol_block
from binance_bot.core.exchange import ExchangeAPIError, ExchangeReconciliationPort
from binance_bot.core.models import (
    BotState,
    ExchangePositionSnapshot,
    ReconciliationResult,
    StartupIssue,
    SymbolRuntimeStatus,
)
from binance_bot.services.error_handler import utc_now_iso


def load_exchange_snapshot(*, settings, client: ExchangeReconciliationPort) -> dict[str, ExchangePositionSnapshot]:
    snapshots: dict[str, ExchangePositionSnapshot] = {}
    for symbol in settings.symbols:
        snapshots[symbol] = client.get_position_snapshot(symbol, settings.quote_asset)
    return snapshots


def reconcile_symbol_state(*, symbol: str, local_position, exchange_snapshot: ExchangePositionSnapshot):
    decision = decide_reconciliation_action(local_position, exchange_snapshot)
    block_decision = decide_symbol_block(decision.action, decision.reason)

    if decision.action == "ready":
        status = SymbolRuntimeStatus(
            symbol=symbol,
            status="ready",
            blocked=False,
            suspect_position=False,
            reason=decision.reason,
        )
        return status, None, None

    local_qty = local_position.quantity if local_position is not None else 0.0
    issue_status = "resolved" if decision.action == "restore-position" else "open"
    issue = StartupIssue(
        symbol=symbol,
        issue_type=decision.issue_type or "startup-mismatch",
        local_qty=local_qty,
        exchange_qty=exchange_snapshot.exchange_quantity,
        action=decision.action,
        status=issue_status,
        message=_build_issue_message(symbol, decision.reason, local_qty, exchange_snapshot.exchange_quantity),
    )
    status = SymbolRuntimeStatus(
        symbol=symbol,
        status="recovered" if decision.action == "restore-position" else "blocked",
        blocked=block_decision.blocked,
        suspect_position=block_decision.suspect_position,
        reason=decision.reason,
    )
    restore_snapshot = exchange_snapshot if decision.action == "restore-position" else None
    return status, issue, restore_snapshot


def reconcile_runtime_state(*, settings, client: ExchangeReconciliationPort, state: BotState) -> ReconciliationResult:
    result = ReconciliationResult()

    for symbol in settings.symbols:
        local_position = state.open_positions.get(symbol)
        try:
            exchange_snapshot = client.get_position_snapshot(symbol, settings.quote_asset)
        except ExchangeAPIError as exc:
            reason = f"startup-snapshot-failed: {exc}"
            result.symbol_statuses[symbol] = SymbolRuntimeStatus(
                symbol=symbol,
                status="blocked",
                blocked=True,
                suspect_position=symbol in state.open_positions,
                reason=reason,
            )
            result.blocked_symbols[symbol] = reason
            if symbol in state.open_positions:
                result.suspect_positions[symbol] = reason
            result.issues.append(
                StartupIssue(
                    symbol=symbol,
                    issue_type="snapshot-load-failed",
                    local_qty=local_position.quantity if local_position is not None else 0.0,
                    exchange_qty=0.0,
                    action="block-symbol",
                    status="open",
                    message=reason,
                )
            )
            continue

        status, issue, restore_snapshot = reconcile_symbol_state(
            symbol=symbol,
            local_position=local_position,
            exchange_snapshot=exchange_snapshot,
        )
        result.symbol_statuses[symbol] = status
        if status.blocked:
            result.blocked_symbols[symbol] = status.reason
        if status.suspect_position:
            result.suspect_positions[symbol] = status.reason
        if issue is not None:
            result.issues.append(issue)
        if restore_snapshot is not None:
            result.restored_snapshots[symbol] = restore_snapshot

    if result.blocked_symbols:
        result.status = "blocked-symbols-present"
    elif result.issues:
        result.status = "recovered-with-adjustments"
    else:
        result.status = "clean"
    return result


def apply_reconciliation_result(
    *,
    settings,
    state: BotState,
    state_store,
    order_manager,
    result: ReconciliationResult,
    reconciliation_journal,
    errors_journal,
    notifier,
    loggers,
) -> None:
    previous_issue_keys = {issue.issue_key for issue in state.startup_issues}
    state.blocked_symbols = {}
    state.suspect_positions = {}

    for symbol, snapshot in result.restored_snapshots.items():
        order_manager.restore_position_from_exchange(snapshot, state)

    for symbol, reason in result.suspect_positions.items():
        order_manager.mark_position_unrecoverable(symbol, reason, state)

    state.blocked_symbols.update(result.blocked_symbols)
    state.suspect_positions.update(result.suspect_positions)
    state.startup_issues = [issue for issue in result.issues if issue.status != "resolved"]
    current_issue_keys = {issue.issue_key for issue in state.startup_issues}
    state.acknowledged_startup_issues = [
        issue_key for issue_key in state.acknowledged_startup_issues if issue_key in current_issue_keys
    ]
    state.alerted_startup_issues = [
        issue_key for issue_key in state.alerted_startup_issues if issue_key in current_issue_keys
    ]
    state.last_reconciled_at = utc_now_iso()
    state.last_reconciliation_status = result.status

    for issue in result.issues:
        _record_reconciliation_issue(
            settings=settings,
            issue=issue,
            reconciliation_journal=reconciliation_journal,
            errors_journal=errors_journal,
            notifier=notifier,
            loggers=loggers,
            state=state,
            previous_issue_keys=previous_issue_keys,
        )

    state_store.save(state)

    if result.status == "clean":
        loggers.app.info("Startup reconciliation passed for %s symbols.", len(result.symbol_statuses))
    else:
        loggers.app.info(
            "Startup reconciliation finished with status %s. Blocked symbols: %s",
            result.status,
            ", ".join(sorted(result.blocked_symbols)) or "none",
        )


def _record_reconciliation_issue(
    *,
    settings,
    issue: StartupIssue,
    reconciliation_journal,
    errors_journal,
    notifier,
    loggers,
    state,
    previous_issue_keys: set[str],
) -> None:
    reconciliation_journal.write(
        {
            "timestamp_utc": utc_now_iso(),
            "symbol": issue.symbol,
            "issue_type": issue.issue_type,
            "local_qty": issue.local_qty,
            "exchange_qty": issue.exchange_qty,
            "action": issue.action,
            "status": issue.status,
            "mode": settings.app_mode,
        }
    )

    if issue.status == "resolved":
        loggers.app.info("Recovered %s from exchange snapshot.", issue.symbol)
        notifier.send(
            f"[{settings.app_mode}] Recovered from exchange for {issue.symbol}\n"
            f"Action: {issue.action}\n"
            f"Local qty: {issue.local_qty:.8f}\n"
            f"Exchange qty: {issue.exchange_qty:.8f}"
        )
        return

    loggers.error.error("Startup reconciliation issue for %s: %s", issue.symbol, issue.message)
    errors_journal.write(
        {
            "timestamp_utc": utc_now_iso(),
            "scope": "startup-reconciliation",
            "symbol": issue.symbol,
            "error_type": issue.issue_type,
            "message": issue.message,
            "mode": settings.app_mode,
        }
    )
    if issue.issue_key in state.acknowledged_startup_issues:
        return
    if issue.issue_key in state.alerted_startup_issues:
        return
    if issue.issue_key not in previous_issue_keys:
        state.alerted_startup_issues.append(issue.issue_key)
    notifier.send(
        f"[{settings.app_mode}] Startup mismatch for {issue.symbol}\n"
        f"Issue: {issue.issue_type}\n"
        f"Action: {issue.action}\n"
        f"Manual intervention required."
    )


def _build_issue_message(symbol: str, reason: str, local_qty: float, exchange_qty: float) -> str:
    return (
        f"{symbol}: {reason} | local_qty={local_qty:.8f} | exchange_qty={exchange_qty:.8f}"
    )