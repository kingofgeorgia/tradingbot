from __future__ import annotations

import json

from binance_bot.core.decisions import decide_issue_acknowledgement, decide_manual_repair_action, decide_unblock_allowed
from binance_bot.core.models import RepairRecord
from binance_bot.services.error_handler import utc_now_iso
from binance_bot.services.reconciliation import reconcile_runtime_state
from binance_bot.services.status import build_runtime_status_report, format_status_report, format_status_report_json


def inspect_runtime_issues(*, settings, client, state, as_json: bool = False) -> str:
    _ = client
    report = build_runtime_status_report(settings=settings, state=state)
    if as_json:
        return format_status_report_json(report)
    return format_status_report(report)


def acknowledge_issue(*, symbol: str, state, state_store, repair_journal, loggers, settings) -> str:
    issue = next((item for item in state.startup_issues if item.symbol == symbol), None)
    if issue is None:
        return f"No open startup issue for {symbol}."

    decision = decide_issue_acknowledgement(
        issue_key=issue.issue_key,
        acknowledged_issue_keys=state.acknowledged_startup_issues,
    )
    if not decision.should_acknowledge:
        return f"{symbol}: {decision.reason}"

    state.acknowledged_startup_issues.append(issue.issue_key)
    state.last_manual_review_at = utc_now_iso()
    state.last_manual_action_by_symbol[symbol] = "acknowledge"
    _record_repair_action(
        settings=settings,
        state=state,
        repair_journal=repair_journal,
        symbol=symbol,
        action="acknowledge",
        status="ok",
        note=decision.reason,
    )
    state_store.save(state)
    loggers.app.info("Acknowledged startup issue for %s", symbol)
    return f"Acknowledged startup issue for {symbol}."


def repair_symbol_state(*, settings, client, state, state_store, order_manager, repair_journal, loggers, symbol: str, action: str) -> str:
    issue = next((item for item in state.startup_issues if item.symbol == symbol), None)
    result = reconcile_runtime_state(settings=settings, client=client, state=state)
    snapshot = result.restored_snapshots.get(symbol)
    has_open_issue = issue is not None
    decision = decide_manual_repair_action(
        requested_action=action,
        has_open_issue=has_open_issue,
        can_restore=snapshot is not None,
    )
    if not decision.allowed:
        return f"{symbol}: {decision.reason}"

    _backup_state_before_manual_action(settings=settings, state=state, symbol=symbol, action=action)

    if action == "restore-from-exchange":
        order_manager.restore_position_from_exchange(snapshot, state)
        _resolve_issue_for_symbol(state, symbol)
    elif action == "drop-local-state":
        order_manager.drop_local_position(symbol, state)
        _resolve_issue_for_symbol(state, symbol)
    elif action == "keep-blocked":
        pass
    else:
        return f"{symbol}: unsupported repair action {action}"

    state.last_manual_review_at = utc_now_iso()
    state.last_manual_action_by_symbol[symbol] = action
    _record_repair_action(
        settings=settings,
        state=state,
        repair_journal=repair_journal,
        symbol=symbol,
        action=action,
        status="ok",
        note=decision.reason,
    )
    state_store.save(state)
    loggers.app.info("Applied manual repair for %s: %s", symbol, action)
    return f"Applied manual repair for {symbol}: {action}."


def unblock_symbol(*, settings, client, state, state_store, repair_journal, loggers, symbol: str) -> str:
    result = reconcile_runtime_state(settings=settings, client=client, state=state)
    has_open_issue = any(issue.symbol == symbol for issue in state.startup_issues)
    symbol_blocked = symbol in state.blocked_symbols
    state_aligned = symbol not in result.blocked_symbols and symbol not in result.suspect_positions
    decision = decide_unblock_allowed(
        has_open_issue=has_open_issue,
        symbol_blocked=symbol_blocked,
        state_aligned=state_aligned,
    )
    if not decision.allowed:
        return f"{symbol}: {decision.reason}"

    _backup_state_before_manual_action(settings=settings, state=state, symbol=symbol, action="unblock")

    state.blocked_symbols.pop(symbol, None)
    state.suspect_positions.pop(symbol, None)
    _resolve_issue_for_symbol(state, symbol)
    state.last_manual_review_at = utc_now_iso()
    state.last_manual_action_by_symbol[symbol] = "unblock"
    _record_repair_action(
        settings=settings,
        state=state,
        repair_journal=repair_journal,
        symbol=symbol,
        action="unblock",
        status="ok",
        note=decision.reason,
    )
    state_store.save(state)
    loggers.app.info("Unblocked symbol %s", symbol)
    return f"Unblocked {symbol}."


def _resolve_issue_for_symbol(state, symbol: str) -> None:
    resolved_issue_keys = {issue.issue_key for issue in state.startup_issues if issue.symbol == symbol}
    state.startup_issues = [issue for issue in state.startup_issues if issue.symbol != symbol]
    state.acknowledged_startup_issues = [
        issue_key for issue_key in state.acknowledged_startup_issues if issue_key not in resolved_issue_keys
    ]
    state.alerted_startup_issues = [
        issue_key for issue_key in state.alerted_startup_issues if issue_key not in resolved_issue_keys
    ]
    state.alert_cooldowns = {
        key: value
        for key, value in state.alert_cooldowns.items()
        if not key.startswith("startup-issue:") or key.removeprefix("startup-issue:") not in resolved_issue_keys
    }


def _record_repair_action(*, settings, state, repair_journal, symbol: str, action: str, status: str, note: str) -> None:
    timestamp = utc_now_iso()
    repair_journal.write(
        {
            "timestamp_utc": timestamp,
            "symbol": symbol,
            "action": action,
            "status": status,
            "note": note,
            "mode": settings.app_mode,
        }
    )
    state.repair_history.append(
        RepairRecord(
            symbol=symbol,
            action=action,
            status=status,
            note=note,
            timestamp_utc=timestamp,
        )
    )


def _backup_state_before_manual_action(*, settings, state, symbol: str, action: str) -> None:
    settings.state_backups_dir.mkdir(parents=True, exist_ok=True)
    timestamp = utc_now_iso().replace(":", "-")
    backup_file = settings.state_backups_dir / f"{timestamp}__{symbol}__{action}.json"
    backup_file.write_text(json.dumps(state.to_dict(), ensure_ascii=True, indent=2), encoding="utf-8")