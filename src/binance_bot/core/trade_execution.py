from __future__ import annotations

from dataclasses import dataclass

from binance_bot.core.models import Position


@dataclass(slots=True)
class OpenPositionResult:
    symbol: str
    position: Position
    average_price: float
    quantity: float
    stop_loss: float
    take_profit: float
    fee_paid_quote: float


@dataclass(slots=True)
class ClosePositionResult:
    symbol: str
    reason: str
    average_price: float
    executed_quantity: float
    exit_fee_quote: float
    pnl_quote: float
    halt_reason: str | None


def build_open_position_result(
    *,
    symbol: str,
    quantity: float,
    average_price: float,
    stop_loss_pct: float,
    take_profit_pct: float,
    opened_at: str,
    order_id: int,
    mode: str,
    quote_spent: float,
    fee_paid_quote: float,
) -> OpenPositionResult:
    stop_loss = average_price * (1 - stop_loss_pct)
    take_profit = average_price * (1 + take_profit_pct)
    position = Position(
        symbol=symbol,
        quantity=quantity,
        entry_price=average_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        opened_at=opened_at,
        order_id=order_id,
        mode=mode,
        quote_spent=quote_spent,
        fee_paid_quote=fee_paid_quote,
    )
    return OpenPositionResult(
        symbol=symbol,
        position=position,
        average_price=average_price,
        quantity=quantity,
        stop_loss=stop_loss,
        take_profit=take_profit,
        fee_paid_quote=fee_paid_quote,
    )


def calculate_close_result(
    *,
    symbol: str,
    reason: str,
    position: Position,
    average_price: float,
    executed_quantity: float,
    quote_received: float,
    exit_fee_quote: float,
    halt_reason: str | None,
) -> ClosePositionResult:
    pnl_quote = quote_received - position.quote_spent - position.fee_paid_quote - exit_fee_quote
    return ClosePositionResult(
        symbol=symbol,
        reason=reason,
        average_price=average_price,
        executed_quantity=executed_quantity,
        exit_fee_quote=exit_fee_quote,
        pnl_quote=pnl_quote,
        halt_reason=halt_reason,
    )