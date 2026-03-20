from __future__ import annotations

from datetime import UTC, datetime

from binance_bot.core.errors import classify_runtime_error
from binance_bot.services.alerts import send_alert_with_cooldown


def utc_now_iso() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat()


def record_api_error(
    errors_journal,
    notifier,
    loggers,
    mode: str,
    scope: str,
    symbol: str,
    exc: Exception,
    *,
    settings=None,
    state=None,
    state_store=None,
):
    descriptor = classify_runtime_error(scope=scope, exc=exc)
    loggers.error.error("[%s/%s] %s error for %s: %s", descriptor.severity, descriptor.category, scope, symbol or "n/a", exc)
    errors_journal.write(
        {
            "timestamp_utc": utc_now_iso(),
            "scope": scope,
            "symbol": symbol,
            "error_type": type(exc).__name__,
            "message": f"[{descriptor.severity}/{descriptor.category}/{descriptor.reaction}] {exc}",
            "mode": mode,
        }
    )
    if descriptor.notify_operator:
        message = (
            f"[{mode}] {descriptor.severity.upper()} API error in {scope} for {symbol or 'n/a'}\n"
            f"Category: {descriptor.category}\n"
            f"Reaction: {descriptor.reaction}\n"
            f"Details: {exc}"
        )
        if settings is not None and state is not None and state_store is not None:
            send_alert_with_cooldown(
                settings=settings,
                state=state,
                state_store=state_store,
                notifier=notifier,
                alert_key=f"runtime-error:{scope}:{symbol or 'n/a'}:{descriptor.category}",
                message=message,
            )
        else:
            notifier.send(message)
    return descriptor