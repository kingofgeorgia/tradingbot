from __future__ import annotations

from datetime import UTC, datetime


def utc_now_iso() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat()


def record_api_error(errors_journal, notifier, loggers, mode: str, scope: str, symbol: str, exc: Exception) -> None:
    loggers.error.error("%s error for %s: %s", scope, symbol or "n/a", exc)
    errors_journal.write(
        {
            "timestamp_utc": utc_now_iso(),
            "scope": scope,
            "symbol": symbol,
            "error_type": type(exc).__name__,
            "message": str(exc),
            "mode": mode,
        }
    )
    notifier.send(f"[{mode}] API error in {scope} for {symbol or 'n/a'}: {exc}")