from __future__ import annotations

import logging

import requests


class TelegramNotifier:
    def __init__(self, bot_token: str | None, chat_id: str | None, logger: logging.Logger) -> None:
        self._bot_token = bot_token
        self._chat_id = chat_id
        self._logger = logger

    @property
    def enabled(self) -> bool:
        return bool(self._bot_token and self._chat_id)

    def send(self, message: str) -> None:
        if not self.enabled:
            return
        try:
            response = requests.post(
                f"https://api.telegram.org/bot{self._bot_token}/sendMessage",
                data={"chat_id": self._chat_id, "text": message},
                timeout=10,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            self._logger.error("Telegram notification failed: %s", exc)
