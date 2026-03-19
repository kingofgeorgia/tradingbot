from __future__ import annotations

import time

from binance_bot.services.cycle import process_cycle
from binance_bot.services.error_handler import utc_now_iso
from binance_bot.services.runtime import build_runtime


def run() -> None:
    runtime = build_runtime()

    runtime.loggers.app.info(
        "Bot started in %s mode for symbols: %s",
        runtime.settings.app_mode,
        ", ".join(runtime.settings.symbols),
    )
    runtime.notifier.send(
        f"[{runtime.settings.app_mode}] Bot started for symbols: {', '.join(runtime.settings.symbols)}"
    )

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
            runtime.loggers.error.error("Fatal error in trading loop: %s", exc, exc_info=True)
            runtime.errors_journal.write(
                {
                    "timestamp_utc": utc_now_iso(),
                    "scope": "main-loop",
                    "symbol": "",
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                    "mode": runtime.settings.app_mode,
                }
            )
            runtime.notifier.send(f"[{runtime.settings.app_mode}] Fatal bot error: {exc}")
            raise

        if runtime.settings.run_once:
            runtime.loggers.app.info("RUN_ONCE enabled, stopping after one cycle.")
            break

        time.sleep(runtime.settings.loop_interval_seconds)