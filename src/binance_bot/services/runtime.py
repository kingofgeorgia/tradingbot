from __future__ import annotations

import time
from datetime import datetime, timezone
from dataclasses import dataclass

from binance_bot.clients.binance_client import BinanceSpotClient
from binance_bot.config import Settings, ensure_runtime_directories, load_settings
from binance_bot.core.exchange import ExchangeRuntimePort
from binance_bot.core.journal import CsvJournal
from binance_bot.core.logging_setup import Loggers, configure_logging
from binance_bot.core.models import RepairRecord
from binance_bot.core.state import StateLoadError, StateStore
from binance_bot.notify.telegram import TelegramNotifier
from binance_bot.orders.manager import OrderManager
from binance_bot.risk.manager import RiskManager
from binance_bot.strategy.ema_cross import EmaCrossStrategy

from binance_bot.services.cycle import process_cycle
from binance_bot.services.error_handler import record_api_error
from binance_bot.services.reconciliation import apply_reconciliation_result, reconcile_runtime_state
from binance_bot.services.status import (
    build_runtime_status_report,
    format_runtime_health_notification,
    format_startup_summary_notification,
    format_status_report,
)


@dataclass(slots=True)
class AppRuntime:
    settings: Settings
    loggers: Loggers
    signals_journal: CsvJournal
    trades_journal: CsvJournal
    errors_journal: CsvJournal
    reconciliation_journal: CsvJournal
    repair_journal: CsvJournal
    notifier: TelegramNotifier
    client: ExchangeRuntimePort
    state_store: StateStore
    strategy: EmaCrossStrategy
    risk_manager: RiskManager
    order_manager: OrderManager


def ensure_runtime_state_file(
    *,
    settings: Settings,
    state_store: StateStore,
    repair_journal: CsvJournal,
    notifier: TelegramNotifier,
    loggers: Loggers,
) -> None:
    try:
        state_store.load()
        return
    except StateLoadError as exc:
        error_message = str(exc)
        backup_file = state_store.recover(backups_dir=settings.state_backups_dir)

    timestamp = _utc_now_iso()
    backup_label = backup_file.name if backup_file is not None else "none"
    note = f"Recovered runtime state from invalid state.json: {error_message}. Backup: {backup_label}."

    repair_journal.write(
        {
            "timestamp_utc": timestamp,
            "symbol": "__runtime__",
            "action": "recover-state-file",
            "status": "recovered",
            "note": note,
            "mode": settings.app_mode,
        }
    )

    recovered_state = state_store.load()
    recovered_state.repair_history.append(
        RepairRecord(
            symbol="__runtime__",
            action="recover-state-file",
            status="recovered",
            note=note,
            timestamp_utc=timestamp,
        )
    )
    state_store.save(recovered_state)

    loggers.error.error(note)
    notifier.send(
        f"[{settings.app_mode}] State file recovery applied\n"
        f"Reason: {error_message}\n"
        f"Backup: {backup_label}\n"
        "Runtime state reset to empty local snapshot"
    )


def build_runtime() -> AppRuntime:
    settings = load_settings()
    ensure_runtime_directories(settings)

    loggers = configure_logging(settings.app_log_file, settings.error_log_file)

    signals_journal = CsvJournal(
        settings.signals_journal_file,
        ["timestamp_utc", "symbol", "action", "reason", "price", "ema_fast", "ema_slow", "mode"],
    )
    trades_journal = CsvJournal(
        settings.trades_journal_file,
        [
            "timestamp_utc",
            "symbol",
            "side",
            "reason",
            "price",
            "quantity",
            "stop_loss",
            "take_profit",
            "fee_quote",
            "pnl_quote",
            "mode",
        ],
    )
    errors_journal = CsvJournal(
        settings.errors_journal_file,
        ["timestamp_utc", "scope", "symbol", "error_type", "message", "mode"],
    )
    reconciliation_journal = CsvJournal(
        settings.reconciliation_journal_file,
        ["timestamp_utc", "symbol", "issue_type", "local_qty", "exchange_qty", "action", "status", "mode"],
    )
    repair_journal = CsvJournal(
        settings.repair_journal_file,
        ["timestamp_utc", "symbol", "action", "status", "note", "mode"],
    )

    notifier = TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id, loggers.error)
    client: ExchangeRuntimePort = BinanceSpotClient(settings)
    state_store = StateStore(settings.state_file)
    ensure_runtime_state_file(
        settings=settings,
        state_store=state_store,
        repair_journal=repair_journal,
        notifier=notifier,
        loggers=loggers,
    )

    strategy = EmaCrossStrategy(
        fast_period=settings.fast_ema_period,
        slow_period=settings.slow_ema_period,
        interval=settings.timeframe,
        stale_data_multiplier=settings.stale_data_multiplier,
    )
    risk_manager = RiskManager(settings)
    order_manager = OrderManager(
        settings=settings,
        client=client,
        risk_manager=risk_manager,
        state_store=state_store,
        loggers=loggers,
        notifier=notifier,
        signals_journal=signals_journal,
        trades_journal=trades_journal,
    )

    client.sync_time()

    return AppRuntime(
        settings=settings,
        loggers=loggers,
        signals_journal=signals_journal,
        trades_journal=trades_journal,
        errors_journal=errors_journal,
        reconciliation_journal=reconciliation_journal,
        repair_journal=repair_journal,
        notifier=notifier,
        client=client,
        state_store=state_store,
        strategy=strategy,
        risk_manager=risk_manager,
        order_manager=order_manager,
    )


def reconcile_startup(runtime: AppRuntime) -> None:
    state = runtime.state_store.load()
    result = reconcile_runtime_state(
        settings=runtime.settings,
        client=runtime.client,
        state=state,
    )
    apply_reconciliation_result(
        settings=runtime.settings,
        state=state,
        state_store=runtime.state_store,
        order_manager=runtime.order_manager,
        result=result,
        reconciliation_journal=runtime.reconciliation_journal,
        errors_journal=runtime.errors_journal,
        notifier=runtime.notifier,
        loggers=runtime.loggers,
    )
    refreshed_state = runtime.state_store.load()
    report = build_runtime_status_report(
        settings=runtime.settings,
        state=refreshed_state,
    )
    runtime.loggers.app.info("Startup status summary:\n%s", format_status_report(report))
    runtime.notifier.send(format_startup_summary_notification(app_mode=runtime.settings.app_mode, report=report))


def run_loop(runtime: AppRuntime) -> None:
    if runtime.settings.runtime_mode == "startup-check-only":
        runtime.loggers.app.info("RUNTIME_MODE=startup-check-only, skipping trading loop.")
        return

    runtime.loggers.app.info(
        "Bot started in %s mode for symbols: %s | runtime_mode=%s",
        runtime.settings.app_mode,
        ", ".join(runtime.settings.symbols),
        runtime.settings.runtime_mode,
    )
    runtime.notifier.send(
        f"[{runtime.settings.app_mode}] Bot started for symbols: {', '.join(runtime.settings.symbols)}\n"
        f"Runtime mode: {runtime.settings.runtime_mode}"
    )

    cycle_number = 0

    while True:
        state = runtime.state_store.load()

        try:
            process_cycle(
                settings=runtime.settings,
                client=runtime.client,
                state=state,
                state_store=runtime.state_store,
                strategy=runtime.strategy,
                risk_manager=runtime.risk_manager,
                order_manager=runtime.order_manager,
                errors_journal=runtime.errors_journal,
                notifier=runtime.notifier,
                loggers=runtime.loggers,
            )
        except Exception as exc:
            record_api_error(
                runtime.errors_journal,
                runtime.notifier,
                runtime.loggers,
                runtime.settings.app_mode,
                "main-loop",
                "",
                exc,
            )
            raise

        current_state = runtime.state_store.load()
        cycle_number += 1
        runtime.loggers.app.info(
            "Cycle summary | open_positions=%s blocked_symbols=%s startup_issues=%s",
            len(current_state.open_positions),
            len(current_state.blocked_symbols),
            len(current_state.startup_issues),
        )

        if runtime.settings.heartbeat_interval_cycles > 0 and cycle_number % runtime.settings.heartbeat_interval_cycles == 0:
            report = build_runtime_status_report(settings=runtime.settings, state=current_state)
            runtime.notifier.send(
                format_runtime_health_notification(
                    app_mode=runtime.settings.app_mode,
                    report=report,
                    cycle_number=cycle_number,
                )
            )

        if runtime.settings.run_once:
            runtime.loggers.app.info("RUN_ONCE enabled, stopping after one cycle.")
            break

        time.sleep(runtime.settings.loop_interval_seconds)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()