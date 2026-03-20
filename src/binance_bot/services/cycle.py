from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from binance_bot.core.decisions import decide_risk_entry, decide_signal_action
from binance_bot.core.exchange import ExchangeAPIError, ExchangeRuntimePort
from binance_bot.services.alerts import send_alert_with_cooldown
from binance_bot.services.error_handler import record_api_error
from binance_bot.services.position_monitor import manage_open_positions


@dataclass(slots=True)
class PortfolioSnapshot:
    total_equity: float | None
    free_quote_balance: float | None

    @property
    def can_open_new_positions(self) -> bool:
        return self.total_equity is not None and self.free_quote_balance is not None


def process_cycle(
    *,
    settings,
    client: ExchangeRuntimePort,
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
        state=state,
        state_store=state_store,
        errors_journal=errors_journal,
        notifier=notifier,
        loggers=loggers,
    )
    if portfolio_snapshot.total_equity is not None:
        risk_manager.refresh_trading_day(state, current_day, portfolio_snapshot.total_equity)
        state_store.save(state)
    else:
        loggers.app.info(
            "Graceful degradation active: skipping trading-day refresh because portfolio equity is unavailable."
        )

    if not portfolio_snapshot.can_open_new_positions:
        loggers.app.info(
            "Graceful degradation active: new BUY entries are disabled for this cycle due to partial portfolio snapshot failure."
        )

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
        block_reason = state.blocked_symbols.get(symbol)
        if block_reason:
            loggers.app.info("Skipping %s: symbol blocked by startup reconciliation (%s)", symbol, block_reason)
            continue

        symbol_runtime_mode = settings.get_effective_symbol_runtime_mode(symbol)

        try:
            candles = client.get_klines(symbol, settings.timeframe, settings.candle_limit)
            last_processed_candle = state.last_processed_candle.get(symbol)
            signal = strategy.evaluate(symbol, candles, last_processed_candle)
        except ExchangeAPIError as exc:
            record_api_error(
                errors_journal,
                notifier,
                loggers,
                settings.app_mode,
                "market-data",
                symbol,
                exc,
                settings=settings,
                state=state,
                state_store=state_store,
            )
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
                symbol_runtime_mode=symbol_runtime_mode,
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
            symbol_runtime_mode=symbol_runtime_mode,
            state=state,
            current_day=current_day,
            portfolio_snapshot=portfolio_snapshot,
            client=client,
            risk_manager=risk_manager,
            order_manager=order_manager,
            state_store=state_store,
            settings=settings,
            errors_journal=errors_journal,
            notifier=notifier,
            loggers=loggers,
        )


def _load_portfolio_snapshot(
    *, client: ExchangeRuntimePort, settings, state, state_store, errors_journal, notifier, loggers
) -> PortfolioSnapshot:
    total_equity: float | None = None
    free_quote_balance: float | None = None

    try:
        total_equity = client.get_portfolio_value(settings.symbols, settings.quote_asset)
    except ExchangeAPIError as exc:
        record_api_error(
            errors_journal,
            notifier,
            loggers,
            settings.app_mode,
            "portfolio",
            "",
            exc,
            settings=settings,
            state=state,
            state_store=state_store,
        )

    try:
        free_quote_balance = client.get_asset_free_balance(settings.quote_asset)
    except ExchangeAPIError as exc:
        record_api_error(
            errors_journal,
            notifier,
            loggers,
            settings.app_mode,
            "portfolio",
            settings.quote_asset,
            exc,
            settings=settings,
            state=state,
            state_store=state_store,
        )

    return PortfolioSnapshot(total_equity=total_equity, free_quote_balance=free_quote_balance)


def _handle_sell_signal(
    *,
    symbol,
    reason,
    symbol_runtime_mode,
    state,
    state_store,
    order_manager,
    settings,
    errors_journal,
    notifier,
    loggers,
) -> None:
    if symbol_runtime_mode == "observe-only":
        loggers.app.info("Skipping SELL execution for %s because effective_runtime_mode=observe-only", symbol)
        return

    try:
        halt_reason = order_manager.close_position(symbol, reason, state)
        state_store.save(state)
        _notify_halt_reason(
            halt_reason,
            settings=settings,
            state=state,
            state_store=state_store,
            notifier=notifier,
        )
    except ExchangeAPIError as exc:
        record_api_error(
            errors_journal,
            notifier,
            loggers,
            settings.app_mode,
            "close-position",
            symbol,
            exc,
            settings=settings,
            state=state,
            state_store=state_store,
        )


def _handle_buy_signal(
    *,
    symbol,
    signal,
    symbol_runtime_mode,
    state,
    current_day,
    portfolio_snapshot,
    client,
    risk_manager,
    order_manager,
    state_store,
    settings,
    errors_journal,
    notifier,
    loggers,
) -> None:
    if symbol_runtime_mode == "observe-only":
        loggers.app.info("Skipping BUY execution for %s because effective_runtime_mode=observe-only", symbol)
        return
    if symbol_runtime_mode == "no-new-entries":
        loggers.app.info("Skipping BUY execution for %s because effective_runtime_mode=no-new-entries", symbol)
        return
    if not portfolio_snapshot.can_open_new_positions:
        loggers.app.info(
            "Skipping BUY execution for %s because graceful degradation disabled new entries for this cycle",
            symbol,
        )
        return

    can_open, reason = risk_manager.can_open_position(symbol, state, current_day)
    risk_decision = decide_risk_entry(can_open, reason)
    if not risk_decision.allowed:
        loggers.app.info("Skipping BUY for %s: %s", symbol, risk_decision.reason)
        return

    try:
        filters = client.get_symbol_filters(symbol)
        order_manager.open_long(
            signal,
            filters,
            state,
            portfolio_snapshot.total_equity,
            portfolio_snapshot.free_quote_balance,
        )
        state_store.save(state)
    except (ExchangeAPIError, ValueError) as exc:
        record_api_error(
            errors_journal,
            notifier,
            loggers,
            settings.app_mode,
            "open-position",
            symbol,
            exc,
            settings=settings,
            state=state,
            state_store=state_store,
        )


def _notify_halt_reason(halt_reason: str | None, *, settings, state, state_store, notifier) -> None:
    if halt_reason == "daily-loss-limit-reached":
        send_alert_with_cooldown(
            settings=settings,
            state=state,
            state_store=state_store,
            notifier=notifier,
            alert_key="runtime-halt:daily-loss-limit-reached",
            message=f"[{settings.app_mode}] Daily loss limit reached.\nNew entries are blocked until next day.",
        )
    elif halt_reason == "max-consecutive-losses-reached":
        send_alert_with_cooldown(
            settings=settings,
            state=state,
            state_store=state_store,
            notifier=notifier,
            alert_key="runtime-halt:max-consecutive-losses-reached",
            message=f"[{settings.app_mode}] Three consecutive losses reached.\nNew entries are blocked until next day.",
        )