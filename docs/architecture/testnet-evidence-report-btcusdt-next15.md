# BTCUSDT Evidence Report: NEXT-15

Сценарный предзаполненный отчет для `NEXT-15`: `local-position-missing-on-exchange`.

## Header

- Date:
- Operator:
- Branch: `main`
- Commit SHA:
- Environment: `APP_MODE=demo`
- Symbol: `BTCUSDT`
- Scenario: `NEXT-15`
- Evidence directory:

## Preconditions

- Local state had open `BTCUSDT` position before run: yes/no
- Exchange `BTCUSDT` quantity was zero before run: yes/no
- No relevant open orders remained on testnet: yes/no
- Pre-run `inspect --json` saved: yes/no

## Commands executed

- `python main.py inspect --json`
- `python main.py repair BTCUSDT drop-local-state --dry-run`
- `python main.py` with `RUNTIME_MODE=startup-check-only`
- `python main.py inspect`
- Live repair command, if executed:

## Observed evidence

- Startup reconciliation status:
- `inspect` blocked status for `BTCUSDT`:
- Startup issue key:
- `reconciliation.csv` row captured: yes/no
- `errors.csv` startup reconciliation record captured: yes/no
- `repair.csv` unchanged before live repair: yes/no
- Post-run `inspect --json` path:

## Operator decision

- Phantom local state confirmed: yes/no
- Live `drop-local-state` executed: yes/no
- If not executed, why:
- Final conclusion: