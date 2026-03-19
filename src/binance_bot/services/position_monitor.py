from __future__ import annotations

from binance_bot.clients.binance_client import BinanceAPIError
from binance_bot.core.decisions import decide_position_close
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
    for symbol, position in list(state.open_positions.items()):
        try:
            current_price = client.get_latest_price(symbol)
        except BinanceAPIError as exc:
            record_api_error(errors_journal, notifier, loggers, settings.app_mode, "position-monitoring", symbol, exc)
            continue

        close_decision = decide_position_close(current_price, position.stop_loss, position.take_profit)
        if not close_decision.should_close:
            continue

        try:
            order_manager.close_position(symbol, close_decision.reason, state)
            state_store.save(state)
        except BinanceAPIError as exc:
            record_api_error(
                errors_journal,
                notifier,
                loggers,
                settings.app_mode,
                close_decision.error_scope or "position-close",
                symbol,
                exc,
            )