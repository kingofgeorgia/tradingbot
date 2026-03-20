from __future__ import annotations

from datetime import UTC, datetime


def send_alert_with_cooldown(*, settings, state, state_store, notifier, alert_key: str, message: str) -> bool:
    now = datetime.now(tz=UTC).replace(microsecond=0)
    if not should_send_alert(state=state, alert_key=alert_key, cooldown_seconds=settings.alert_cooldown_seconds, now=now):
        return False

    notifier.send(message)
    state.alert_cooldowns[alert_key] = now.isoformat()
    state_store.save(state)
    return True


def should_send_alert(*, state, alert_key: str, cooldown_seconds: int, now: datetime | None = None) -> bool:
    if cooldown_seconds <= 0:
        return True

    last_sent_at = state.alert_cooldowns.get(alert_key)
    if not last_sent_at:
        return True

    try:
        previous = datetime.fromisoformat(last_sent_at)
    except ValueError:
        return True

    if previous.tzinfo is None:
        previous = previous.replace(tzinfo=UTC)

    current = now or datetime.now(tz=UTC).replace(microsecond=0)
    return (current - previous).total_seconds() >= cooldown_seconds