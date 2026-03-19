from __future__ import annotations

from datetime import UTC, datetime

from binance_bot.clients.binance_client import BinanceAPIError
from binance_bot.services.error_handler import record_api_error
from binance_bot.services.position_monitor import manage_open_positions


def process_cycle(
    *,
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
        record_api_error(errors_journal, notifier, loggers, settings.app_mode, "portfolio", "", exc)
        return

    risk_manager.refresh_trading_day(state, current_day, total_equity)
    state_store.save(state)

    manage_open_positions(
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
            record_api_error(errors_journal, notifier, loggers, settings.app_mode, "market-data", symbol, exc)
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
                    notifier.send(
                        f"[{settings.app_mode}] Daily loss limit reached.\n"
                        "New entries are blocked until next day."
                    )
                elif halt_reason == "max-consecutive-losses-reached":
                    notifier.send(
                        f"[{settings.app_mode}] Three consecutive losses reached.\n"
                        "New entries are blocked until next day."
                    )
            except BinanceAPIError as exc:
                record_api_error(errors_journal, notifier, loggers, settings.app_mode, "close-position", symbol, exc)
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
            record_api_error(errors_journal, notifier, loggers, settings.app_mode, "open-position", symbol, exc)