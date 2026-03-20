from __future__ import annotations

from binance_bot.core.decisions import decide_position_close
from binance_bot.core.exchange import ExchangeAPIError
from binance_bot.services.error_handler import record_api_error


def manage_open_positions(
    *,
    settings,
    client,
    state,
    state_store,
    order_manager,
    errors_journal,
    notifier,
    loggers,
) -> None:
    if settings.runtime_mode == "observe-only":
        loggers.app.info("Skipping position monitor execution because runtime_mode=observe-only")
        return

    for symbol, position in list(state.open_positions.items()):
        if settings.get_effective_symbol_runtime_mode(symbol) == "observe-only":
            loggers.app.info("Skipping position monitor for %s because effective_runtime_mode=observe-only", symbol)
            continue

        if symbol in state.suspect_positions:
            loggers.app.info("Skipping suspect position for %s: %s", symbol, state.suspect_positions[symbol])
            continue

        try:
            current_price = client.get_latest_price(symbol)
        except ExchangeAPIError as exc:
            record_api_error(errors_journal, notifier, loggers, settings.app_mode, "position-monitoring", symbol, exc)
            continue

        close_decision = decide_position_close(current_price, position.stop_loss, position.take_profit)
        if not close_decision.should_close:
            continue

        try:
            order_manager.close_position(symbol, close_decision.reason, state)
            state_store.save(state)
        except ExchangeAPIError as exc:
            record_api_error(
                errors_journal,
                notifier,
                loggers,
                settings.app_mode,
                close_decision.error_scope or "position-close",
                symbol,
                exc,
            )