from __future__ import annotations

from binance_bot.clients.binance_client import BinanceAPIError
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

        if current_price <= position.stop_loss:
            try:
                order_manager.close_position(symbol, "stop-loss-hit", state)
                state_store.save(state)
            except BinanceAPIError as exc:
                record_api_error(errors_journal, notifier, loggers, settings.app_mode, "stop-loss-close", symbol, exc)
            continue

        if current_price >= position.take_profit:
            try:
                order_manager.close_position(symbol, "take-profit-hit", state)
                state_store.save(state)
            except BinanceAPIError as exc:
                record_api_error(errors_journal, notifier, loggers, settings.app_mode, "take-profit-close", symbol, exc)