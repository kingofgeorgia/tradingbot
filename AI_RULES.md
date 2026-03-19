# AI rules for tradingbot

- Python 3.11+
- Do not change live trading behavior unless explicitly requested
- Do not move API/network logic into strategy
- Do not modify risk limits without tests
- If behavior changes, update tests first
- Default target is demo safety, not feature speed
- Return concrete file-level edits only
- Keep core/decisions.py pure: no API calls, no notifier calls, no state persistence, no journal writes
- Keep services/* focused on orchestration and execution flow, not business decision ownership
- Keep use_cases/* focused on application trade flows with explicit inputs/outputs
- Keep orders/manager.py as a thin facade, not a home for growing business logic
- Keep startup reconciliation in services/reconciliation.py, not in risk, strategy, or client adapters
- Treat blocked symbols as a safety guardrail: do not open new trades until reconciliation clears them
- Keep operator repair actions in services/repair.py and never hide destructive state changes behind the normal runtime loop
- If runtime modes suppress execution, log the suppression explicitly