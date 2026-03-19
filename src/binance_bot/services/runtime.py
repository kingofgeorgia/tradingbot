from __future__ import annotations

from dataclasses import dataclass

from binance_bot.clients.binance_client import BinanceSpotClient
from binance_bot.config import Settings, ensure_runtime_directories, load_settings
from binance_bot.core.journal import CsvJournal
from binance_bot.core.logging_setup import Loggers, configure_logging
from binance_bot.core.state import StateStore
from binance_bot.notify.telegram import TelegramNotifier
from binance_bot.orders.manager import OrderManager
from binance_bot.risk.manager import RiskManager
from binance_bot.strategy.ema_cross import EmaCrossStrategy


@dataclass(slots=True)
class AppRuntime:
    settings: Settings
    loggers: Loggers
    signals_journal: CsvJournal
    trades_journal: CsvJournal
    errors_journal: CsvJournal
    notifier: TelegramNotifier
    client: BinanceSpotClient
    state_store: StateStore
    strategy: EmaCrossStrategy
    risk_manager: RiskManager
    order_manager: OrderManager


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
        ["timestamp_utc", "symbol", "side", "reason", "price", "quantity", "stop_loss", "take_profit", "fee_quote", "pnl_quote", "mode"],
    )
    errors_journal = CsvJournal(
        settings.errors_journal_file,
        ["timestamp_utc", "scope", "symbol", "error_type", "message", "mode"],
    )

    notifier = TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id, loggers.error)
    client = BinanceSpotClient(settings)
    state_store = StateStore(settings.state_file)
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
        notifier=notifier,
        client=client,
        state_store=state_store,
        strategy=strategy,
        risk_manager=risk_manager,
        order_manager=order_manager,
    )