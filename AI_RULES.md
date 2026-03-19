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