from __future__ import annotations

import time
from datetime import UTC, datetime

from binance_bot.clients.binance_client import BinanceAPIError, BinanceSpotClient
from binance_bot.config import ensure_runtime_directories, load_settings
from binance_bot.core.journal import CsvJournal
from binance_bot.core.logging_setup import configure_logging
from binance_bot.core.state import StateStore
from binance_bot.notify.telegram import TelegramNotifier
from binance_bot.orders.manager import OrderManager
from binance_bot.risk.manager import RiskManager
from binance_bot.strategy.ema_cross import EmaCrossStrategy


def run() -> None:
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
    state = state_store.load()
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
    loggers.app.info("Bot started in %s mode for symbols: %s", settings.app_mode, ", ".join(settings.symbols))
    notifier.send(f"[{settings.app_mode}] Bot started for symbols: {', '.join(settings.symbols)}")

    while True:
        state = state_store.load()
        try:
            process_cycle(
                settings=settings,
                client=client,
                state=state,
                state_store=state_store,
                strategy=strategy,
                risk_manager=risk_manager,
                order_manager=order_manager,
                errors_journal=errors_journal,
                notifier=notifier,
                loggers=loggers,
            )
        except Exception as exc:
            loggers.error.error("Fatal error in trading loop: %s", exc, exc_info=True)
            errors_journal.write(
                {
                    "timestamp_utc": utc_now_iso(),
                    "scope": "main-loop",
                    "symbol": "",
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                    "mode": settings.app_mode,
                }
            )
            notifier.send(f"[{settings.app_mode}] Fatal bot error: {exc}")
            raise

        if settings.run_once:
            loggers.app.info("RUN_ONCE enabled, stopping after one cycle.")
            break
        time.sleep(settings.loop_interval_seconds)


def process_cycle(
    settings,
    client,
    state,
    state_store,
    strategy,
    risk_manager,
    order_manager,
    errors_journal,
    notifier,
    loggers,
) -> None:
    current_day = datetime.now(tz=UTC).date().isoformat()

    try:
        total_equity = client.get_portfolio_value(settings.symbols, settings.quote_asset)
        free_quote_balance = client.get_asset_free_balance(settings.quote_asset)
    except BinanceAPIError as exc:
        _record_api_error(errors_journal, notifier, loggers, settings.app_mode, "portfolio", "", exc)
        return

    risk_manager.refresh_trading_day(state, current_day, total_equity)
    state_store.save(state)

    _manage_open_positions(
        settings=settings,
        client=client,
        state=state,
        state_store=state_store,
        order_manager=order_manager,
        errors_journal=errors_journal,
        notifier=notifier,
        loggers=loggers,
    )

    for symbol in settings.symbols:
        try:
            candles = client.get_klines(symbol, settings.timeframe, settings.candle_limit)
            last_processed_candle = state.last_processed_candle.get(symbol)
            signal = strategy.evaluate(symbol, candles, last_processed_candle)
        except BinanceAPIError as exc:
            _record_api_error(errors_journal, notifier, loggers, settings.app_mode, "market-data", symbol, exc)
            continue

        if signal.candle_close_time:
            state.last_processed_candle[symbol] = signal.candle_close_time
            state_store.save(state)

        if signal.action == "HOLD":
            continue

        order_manager.log_signal(signal)

        if signal.action == "SELL" and symbol in state.open_positions:
            try:
                halt_reason = order_manager.close_position(symbol, signal.reason, state)
                state_store.save(state)
                if halt_reason == "daily-loss-limit-reached":
                    notifier.send(f"[{settings.app_mode}] Daily loss limit reached. New entries are blocked until next day.")
                elif halt_reason == "max-consecutive-losses-reached":
                    notifier.send(f"[{settings.app_mode}] Three consecutive losses reached. New entries are blocked until next day.")
            except BinanceAPIError as exc:
                _record_api_error(errors_journal, notifier, loggers, settings.app_mode, "close-position", symbol, exc)
            continue

        if signal.action != "BUY":
            continue

        can_open, reason = risk_manager.can_open_position(symbol, state, current_day)
        if not can_open:
            loggers.app.info("Skipping BUY for %s: %s", symbol, reason)
            continue

        try:
            filters = client.get_symbol_filters(symbol)
            order_manager.open_long(signal, filters, state, total_equity, free_quote_balance)
            state_store.save(state)
        except (BinanceAPIError, ValueError) as exc:
            _record_api_error(errors_journal, notifier, loggers, settings.app_mode, "open-position", symbol, exc)


def _manage_open_positions(
    settings,
    client,
    state,
    state_store,
    order_manager,
    errors_journal,
    notifier,
    loggers,
) -> None:
    for symbol, position in list(state.open_positions.items()):
        try:
            current_price = client.get_latest_price(symbol)
        except BinanceAPIError as exc:
            _record_api_error(errors_journal, notifier, loggers, settings.app_mode, "position-monitoring", symbol, exc)
            continue

        if current_price <= position.stop_loss:
            try:
                order_manager.close_position(symbol, "stop-loss-hit", state)
                state_store.save(state)
            except BinanceAPIError as exc:
                _record_api_error(errors_journal, notifier, loggers, settings.app_mode, "stop-loss-close", symbol, exc)
            continue

        if current_price >= position.take_profit:
            try:
                order_manager.close_position(symbol, "take-profit-hit", state)
                state_store.save(state)
            except BinanceAPIError as exc:
                _record_api_error(errors_journal, notifier, loggers, settings.app_mode, "take-profit-close", symbol, exc)


def _record_api_error(errors_journal, notifier, loggers, mode: str, scope: str, symbol: str, exc: Exception) -> None:
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


def utc_now_iso() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat()
