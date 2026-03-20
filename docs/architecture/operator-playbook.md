# Operator Playbook

## Startup mismatch types

- `local-position-missing-on-exchange`:
  - keep symbol blocked
  - inspect recent exchange orders/trades
  - use `repair <SYMBOL> drop-local-state` only after confirming the local state is phantom
- `exchange-position-without-local-state`:
  - inspect current exchange snapshot
  - if exchange data is sufficient, use `repair <SYMBOL> restore-from-exchange`
  - unblock only after reconciliation is clean
- `quantity-mismatch`:
  - do not unblock immediately
  - inspect balances and recent trades
  - repair or keep blocked until mismatch disappears

## Operator commands

- `python main.py inspect`
- `python main.py acknowledge BTCUSDT`
- `python main.py repair BTCUSDT restore-from-exchange`
- `python main.py repair BTCUSDT drop-local-state`
- `python main.py unblock BTCUSDT`

## Runtime modes

- `RUNTIME_MODE=trade` — normal execution
- `RUNTIME_MODE=startup-check-only` — reconciliation only, no trading loop
- `RUNTIME_MODE=observe-only` — no BUY/SELL execution, no position monitoring closes
- `RUNTIME_MODE=no-new-entries` — no new BUY entries, existing risk handling still runs

## Manual testnet checklist for NEXT-15..17

This checklist is for `APP_MODE=demo` only. The goal is to collect operator evidence for blocked backlog items without improvising on live-like state changes.

### Pre-flight

1. Confirm `.env` uses `APP_MODE=demo` and a dedicated test symbol set.
2. Stop any long-running bot process before changing `data/state.json` or running manual repair commands.
3. Snapshot current artifacts before the run:
  - copy `data/state.json`
  - copy `data/signals.csv`, `data/trades.csv`, `data/errors.csv`, `data/reconciliation.csv`, `data/repair.csv`
  - copy `logs/app.log` and `logs/errors.log`
4. Run `python main.py inspect --json` and save the full output as the pre-run baseline.
5. If a manual action may be needed, first run the dry-run command:
  - `python main.py repair <SYMBOL> restore-from-exchange --dry-run`
  - `python main.py repair <SYMBOL> drop-local-state --dry-run`
  - `python main.py unblock <SYMBOL> --dry-run`

### NEXT-15: local position missing on exchange

Target scenario: local state contains an open position, but Binance testnet reports zero quantity.

1. Start from a known local open position in `data/state.json` for the target symbol.
2. Verify on testnet that the exchange position is fully closed and no relevant open orders remain.
3. Run `python main.py` with `RUNTIME_MODE=startup-check-only`.
4. Capture the startup summary notification or console output.
5. Run `python main.py inspect` immediately after startup reconciliation.
6. Verify expected evidence:
  - symbol is blocked
  - startup issue is `local-position-missing-on-exchange`
  - `data/reconciliation.csv` contains an entry for that symbol
  - `data/errors.csv` contains the startup reconciliation record
  - `data/repair.csv` is unchanged before any manual repair
7. Record the exact operator decision:
  - if local state is confirmed phantom, run `python main.py repair <SYMBOL> drop-local-state`
  - otherwise leave the symbol blocked
8. Save the post-run `inspect --json` payload and note whether the actual outcome matches the expected blocked/manual-review path.

### NEXT-16: exchange position restored into local state

Target scenario: exchange has a real open position, while local state does not.

1. Ensure testnet holds a real position for the target symbol with a known quantity.
2. Remove the corresponding local position from `data/state.json` or start from an empty local state.
3. Run `python main.py` with `RUNTIME_MODE=startup-check-only`.
4. Capture the startup summary notification or console output.
5. Run `python main.py inspect` and `python main.py inspect --json`.
6. Verify expected evidence:
  - reconciliation status is `recovered-with-adjustments` or `clean` after restore
  - the symbol appears in `open_positions`
  - `data/reconciliation.csv` records the restore path
  - `data/errors.csv` does not contain a new fatal/execution error for this scenario
  - `data/repair.csv` is unchanged unless a manual repair was explicitly executed later
7. If the symbol stayed blocked instead of restoring automatically, run `python main.py repair <SYMBOL> restore-from-exchange --dry-run` and record why the decision path rejected or allowed it.
8. Save the final `inspect --json` payload and update the operator notes with the actual restored quantity, entry price source and whether unblock was required.

### NEXT-17: long runtime journal review and rotation policy

Target scenario: observe CSV/log behavior during a longer demo runtime and document when manual rotation is needed.

1. Start from clean artifacts or move the previous CSV/log files aside.
2. Run the bot on testnet in a controlled mode for an extended window:
  - preferred: normal `RUNTIME_MODE=trade` in demo
  - fallback: `RUN_ONCE=false` with `RUNTIME_MODE=observe-only` if execution risk must stay suppressed
3. Let the process run long enough to produce repeated cycles, heartbeats and at least one reconciliation/startup summary.
4. At fixed checkpoints record file sizes and row counts for:
  - `data/signals.csv`
  - `data/trades.csv`
  - `data/errors.csv`
  - `data/reconciliation.csv`
  - `data/repair.csv`
  - `logs/app.log`
  - `logs/errors.log`
5. Verify journal semantics:
  - `signals.csv` grows per logged signal
  - `trades.csv` grows only on real execution events
  - `errors.csv` contains only actual runtime/API failures
  - `reconciliation.csv` changes on startup reconciliation, not every cycle
  - `repair.csv` changes only for manual repair/unblock actions or state recovery actions
6. Record whether file growth remains operator-manageable without rotation.
7. Document a practical rotation threshold from observed sizes, for example:
  - rotate CSV/log files before they exceed the team’s review comfort threshold
  - archive artifacts together with the matching `state.json` snapshot
  - rotate only while the bot process is stopped
8. Save the final observation in the backlog follow-up note with actual runtime duration, row counts and chosen rotation threshold.

### Evidence package

For each manual run, keep:

- pre-run `inspect --json`
- post-run `inspect --json`
- relevant startup summary or console transcript
- copied CSV/log artifacts
- exact command line used
- operator conclusion: matched expectation, partial mismatch, or unexpected behavior