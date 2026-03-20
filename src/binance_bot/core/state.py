from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from binance_bot.core.models import BotState, CURRENT_STATE_SCHEMA_VERSION


class StateLoadError(ValueError):
    pass


def migrate_state_payload(payload: dict[str, object]) -> dict[str, object]:
    schema_version = int(payload.get("schema_version", 0))

    if schema_version > CURRENT_STATE_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported state schema_version={schema_version}; expected <= {CURRENT_STATE_SCHEMA_VERSION}."
        )

    migrated_payload = dict(payload)

    if schema_version == 0:
        migrated_payload["schema_version"] = CURRENT_STATE_SCHEMA_VERSION
        schema_version = CURRENT_STATE_SCHEMA_VERSION

    if schema_version != CURRENT_STATE_SCHEMA_VERSION:
        raise ValueError(
            f"Unhandled state schema_version={schema_version}; expected {CURRENT_STATE_SCHEMA_VERSION}."
        )

    return migrated_payload


class StateStore:
    def __init__(self, state_file: Path) -> None:
        self._state_file = state_file

    def load(self) -> BotState:
        if not self._state_file.exists():
            return BotState()

        try:
            payload = json.loads(self._state_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise StateLoadError(f"State file is unreadable: {exc}") from exc

        if not isinstance(payload, dict):
            raise StateLoadError("State file must contain a JSON object.")

        try:
            return BotState.from_dict(migrate_state_payload(payload))
        except (TypeError, ValueError) as exc:
            raise StateLoadError(str(exc)) from exc

    def recover(self, *, backups_dir: Path) -> Path | None:
        backup_file: Path | None = None
        if self._state_file.exists():
            backups_dir.mkdir(parents=True, exist_ok=True)
            backup_file = backups_dir / f"{_backup_timestamp()}__runtime__state-load-recovery.json"
            self._state_file.replace(backup_file)

        self.save(BotState())
        return backup_file

    def save(self, state: BotState) -> None:
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        self._state_file.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")


def _backup_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace(":", "-")
