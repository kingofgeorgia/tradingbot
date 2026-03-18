from __future__ import annotations

import json
from pathlib import Path

from binance_bot.core.models import BotState


class StateStore:
    def __init__(self, state_file: Path) -> None:
        self._state_file = state_file

    def load(self) -> BotState:
        if not self._state_file.exists():
            return BotState()
        payload = json.loads(self._state_file.read_text(encoding="utf-8"))
        return BotState.from_dict(payload)

    def save(self, state: BotState) -> None:
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        self._state_file.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")
