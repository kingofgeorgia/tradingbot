from dataclasses import dataclass

@dataclass(slots=True)
class RiskDecision:
    allowed: bool
    reason: str

@dataclass(slots=True)
class CloseDecision:
    should_close: bool
    reason: str