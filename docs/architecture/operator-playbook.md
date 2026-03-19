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