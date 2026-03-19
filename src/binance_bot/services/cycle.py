from __future__ import annotations

from datetime import UTC, datetime

from binance_bot.clients.binance_client import BinanceAPIError
from binance_bot.core.decisions import decide_risk_entry, decide_signal_action
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

    portfolio_snapshot = _load_portfolio_snapshot(
        client=client,
        settings=settings,
        errors_journal=errors_journal,
        notifier=notifier,
        loggers=loggers,
    )
    if portfolio_snapshot is None:
        return

    total_equity, free_quote_balance = portfolio_snapshot

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

        signal_decision = decide_signal_action(
            signal_action=signal.action,
            signal_reason=signal.reason,
            has_open_position=symbol in state.open_positions,
        )

        if not signal_decision.should_log_signal:
            continue

        order_manager.log_signal(signal)

        if signal_decision.action == "close-position":
            _handle_sell_signal(
                symbol=symbol,
                reason=signal_decision.reason,
                state=state,
                state_store=state_store,
                order_manager=order_manager,
                settings=settings,
                errors_journal=errors_journal,
                notifier=notifier,
                loggers=loggers,
            )
            continue

        if signal_decision.action != "evaluate-buy":
            continue

        _handle_buy_signal(
            symbol=symbol,
            signal=signal,
            state=state,
            current_day=current_day,
            total_equity=total_equity,
            free_quote_balance=free_quote_balance,
            client=client,
            risk_manager=risk_manager,
            order_manager=order_manager,
            state_store=state_store,
            settings=settings,
            errors_journal=errors_journal,
            notifier=notifier,
            loggers=loggers,
        )


def _load_portfolio_snapshot(*, client, settings, errors_journal, notifier, loggers):
    try:
        total_equity = client.get_portfolio_value(settings.symbols, settings.quote_asset)
        free_quote_balance = client.get_asset_free_balance(settings.quote_asset)
    except BinanceAPIError as exc:
        record_api_error(errors_journal, notifier, loggers, settings.app_mode, "portfolio", "", exc)
        return None
    return total_equity, free_quote_balance


def _handle_sell_signal(*, symbol, reason, state, state_store, order_manager, settings, errors_journal, notifier, loggers) -> None:
    try:
        halt_reason = order_manager.close_position(symbol, reason, state)
        state_store.save(state)
        _notify_halt_reason(halt_reason, settings.app_mode, notifier)
    except BinanceAPIError as exc:
        record_api_error(errors_journal, notifier, loggers, settings.app_mode, "close-position", symbol, exc)


def _handle_buy_signal(
    *,
    symbol,
    signal,
    state,
    current_day,
    total_equity,
    free_quote_balance,
    client,
    risk_manager,
    order_manager,
    state_store,
    settings,
    errors_journal,
    notifier,
    loggers,
) -> None:
    can_open, reason = risk_manager.can_open_position(symbol, state, current_day)
    risk_decision = decide_risk_entry(can_open, reason)
    if not risk_decision.allowed:
        loggers.app.info("Skipping BUY for %s: %s", symbol, risk_decision.reason)
        return

    try:
        filters = client.get_symbol_filters(symbol)
        order_manager.open_long(signal, filters, state, total_equity, free_quote_balance)
        state_store.save(state)
    except (BinanceAPIError, ValueError) as exc:
        record_api_error(errors_journal, notifier, loggers, settings.app_mode, "open-position", symbol, exc)


def _notify_halt_reason(halt_reason: str | None, app_mode: str, notifier) -> None:
    if halt_reason == "daily-loss-limit-reached":
        notifier.send(f"[{app_mode}] Daily loss limit reached.\nNew entries are blocked until next day.")
    elif halt_reason == "max-consecutive-losses-reached":
        notifier.send(f"[{app_mode}] Three consecutive losses reached.\nNew entries are blocked until next day.")