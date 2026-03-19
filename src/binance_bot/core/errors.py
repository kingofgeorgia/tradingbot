from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ErrorDescriptor:
    category: str
    severity: str


def classify_runtime_error(*, scope: str, exc: Exception) -> ErrorDescriptor:
    name = type(exc).__name__
    if "timeout" in str(exc).lower() or "Timeout" in name:
        return ErrorDescriptor(category="transient-network", severity="warning")
    if scope in {"startup-reconciliation", "portfolio", "market-data", "position-monitoring"}:
        return ErrorDescriptor(category="runtime-io", severity="warning")
    if scope in {"open-position", "close-position", "stop-loss-close", "take-profit-close"}:
        return ErrorDescriptor(category="execution", severity="critical")
    if scope == "main-loop":
        return ErrorDescriptor(category="fatal-loop", severity="critical")
    return ErrorDescriptor(category="unknown", severity="warning")