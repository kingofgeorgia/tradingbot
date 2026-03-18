from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Loggers:
    app: logging.Logger
    signal: logging.Logger
    trade: logging.Logger
    error: logging.Logger


def _build_file_handler(file_path: Path, level: int) -> logging.Handler:
    handler = logging.FileHandler(file_path, encoding="utf-8")
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
    return handler


def _build_console_handler(level: int) -> logging.Handler:
    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    return handler


def _configure_logger(name: str, level: int, handlers: list[logging.Handler]) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers.clear()
    logger.propagate = False
    for handler in handlers:
        logger.addHandler(handler)
    return logger


def configure_logging(app_log_file: Path, error_log_file: Path) -> Loggers:
    app_handlers = [
        _build_console_handler(logging.INFO),
        _build_file_handler(app_log_file, logging.INFO),
    ]
    error_handlers = [
        _build_console_handler(logging.ERROR),
        _build_file_handler(error_log_file, logging.ERROR),
    ]
    return Loggers(
        app=_configure_logger("bot.app", logging.INFO, app_handlers),
        signal=_configure_logger("bot.signal", logging.INFO, app_handlers),
        trade=_configure_logger("bot.trade", logging.INFO, app_handlers),
        error=_configure_logger("bot.error", logging.ERROR, error_handlers),
    )
