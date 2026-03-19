from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv


AppMode = Literal["demo", "live"]
RuntimeMode = Literal["trade", "startup-check-only", "observe-only", "no-new-entries"]


@dataclass(slots=True)
class Settings:
    app_mode: AppMode
    runtime_mode: RuntimeMode
    binance_api_key: str
    binance_secret_key: str
    binance_recv_window: int
    telegram_bot_token: str | None
    telegram_chat_id: str | None
    symbols: list[str]
    timeframe: str
    candle_limit: int
    fast_ema_period: int
    slow_ema_period: int
    stop_loss_pct: float
    take_profit_pct: float
    risk_per_trade_pct: float
    max_position_pct: float
    max_open_positions_total: int
    max_open_positions_per_symbol: int
    daily_loss_limit_pct: float
    max_consecutive_losses: int
    loop_interval_seconds: int
    order_confirm_timeout_seconds: int
    request_timeout_seconds: int
    stale_data_multiplier: int
    quote_asset: str
    run_once: bool
    project_root: Path = field(repr=False)
    data_dir: Path = field(repr=False)
    logs_dir: Path = field(repr=False)

    @property
    def base_url(self) -> str:
        if self.app_mode == "demo":
            return "https://testnet.binance.vision"
        return "https://api.binance.com"

    @property
    def state_file(self) -> Path:
        return self.data_dir / "state.json"

    @property
    def signals_journal_file(self) -> Path:
        return self.data_dir / "signals.csv"

    @property
    def trades_journal_file(self) -> Path:
        return self.data_dir / "trades.csv"

    @property
    def errors_journal_file(self) -> Path:
        return self.data_dir / "errors.csv"

    @property
    def reconciliation_journal_file(self) -> Path:
        return self.data_dir / "reconciliation.csv"

    @property
    def repair_journal_file(self) -> Path:
        return self.data_dir / "repair.csv"

    @property
    def app_log_file(self) -> Path:
        return self.logs_dir / "app.log"

    @property
    def error_log_file(self) -> Path:
        return self.logs_dir / "errors.log"


def load_settings() -> Settings:
    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(project_root / ".env")

    app_mode = os.getenv("APP_MODE", "demo").strip().lower()
    if app_mode not in {"demo", "live"}:
        raise ValueError("APP_MODE must be 'demo' or 'live'.")

    runtime_mode = os.getenv("RUNTIME_MODE", "trade").strip().lower()
    if runtime_mode not in {"trade", "startup-check-only", "observe-only", "no-new-entries"}:
        raise ValueError("RUNTIME_MODE must be one of: trade, startup-check-only, observe-only, no-new-entries.")

    symbols = [item.strip().upper() for item in os.getenv("SYMBOLS", "BTCUSDT,ETHUSDT").split(",") if item.strip()]
    if not symbols:
        raise ValueError("At least one trading symbol must be configured in SYMBOLS.")

    settings = Settings(
        app_mode=app_mode,
        runtime_mode=runtime_mode,
        binance_api_key=os.getenv("BINANCE_API_KEY", "").strip(),
        binance_secret_key=os.getenv("BINANCE_SECRET_KEY", "").strip(),
        binance_recv_window=int(os.getenv("BINANCE_RECV_WINDOW", "5000")),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip() or None,
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", "").strip() or None,
        symbols=symbols,
        timeframe=os.getenv("TIMEFRAME", "15m").strip(),
        candle_limit=int(os.getenv("CANDLE_LIMIT", "120")),
        fast_ema_period=int(os.getenv("FAST_EMA_PERIOD", "20")),
        slow_ema_period=int(os.getenv("SLOW_EMA_PERIOD", "50")),
        stop_loss_pct=float(os.getenv("STOP_LOSS_PCT", "0.02")),
        take_profit_pct=float(os.getenv("TAKE_PROFIT_PCT", "0.04")),
        risk_per_trade_pct=float(os.getenv("RISK_PER_TRADE_PCT", "0.01")),
        max_position_pct=float(os.getenv("MAX_POSITION_PCT", "0.10")),
        max_open_positions_total=int(os.getenv("MAX_OPEN_POSITIONS_TOTAL", "2")),
        max_open_positions_per_symbol=int(os.getenv("MAX_OPEN_POSITIONS_PER_SYMBOL", "1")),
        daily_loss_limit_pct=float(os.getenv("DAILY_LOSS_LIMIT_PCT", "0.03")),
        max_consecutive_losses=int(os.getenv("MAX_CONSECUTIVE_LOSSES", "3")),
        loop_interval_seconds=int(os.getenv("LOOP_INTERVAL_SECONDS", "30")),
        order_confirm_timeout_seconds=int(os.getenv("ORDER_CONFIRM_TIMEOUT_SECONDS", "15")),
        request_timeout_seconds=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "15")),
        stale_data_multiplier=int(os.getenv("STALE_DATA_MULTIPLIER", "2")),
        quote_asset=os.getenv("QUOTE_ASSET", "USDT").strip().upper(),
        run_once=os.getenv("RUN_ONCE", "false").strip().lower() == "true",
        project_root=project_root,
        data_dir=project_root / "data",
        logs_dir=project_root / "logs",
    )

    if not settings.binance_api_key or not settings.binance_secret_key:
        raise ValueError("BINANCE_API_KEY and BINANCE_SECRET_KEY are required in .env.")
    if settings.timeframe != "15m":
        raise ValueError("The first version supports only TIMEFRAME=15m.")
    return settings


def ensure_runtime_directories(settings: Settings) -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.logs_dir.mkdir(parents=True, exist_ok=True)
