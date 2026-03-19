from __future__ import annotations

from decimal import Decimal, ROUND_DOWN


def round_down_to_step(value: float, step_size: float) -> float:
    if step_size <= 0:
        return value

    decimal_value = Decimal(str(value))
    decimal_step = Decimal(str(step_size))
    rounded = (decimal_value / decimal_step).to_integral_value(rounding=ROUND_DOWN) * decimal_step
    return float(rounded)