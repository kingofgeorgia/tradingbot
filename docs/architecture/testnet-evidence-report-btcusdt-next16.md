# BTCUSDT Evidence Report: NEXT-16

Сценарный предзаполненный отчет для `NEXT-16`: `exchange-position-without-local-state`.

## Header

- Date:
- Operator:
- Branch: `main`
- Commit SHA:
- Environment: `APP_MODE=demo`
- Symbol: `BTCUSDT`
- Scenario: `NEXT-16`
- Evidence directory:

## Preconditions

- Exchange had open `BTCUSDT` position before run: yes/no
- Local state was empty or missing `BTCUSDT`: yes/no
- Pre-run `inspect --json` saved: yes/no

## Commands executed

- `python main.py inspect --json`
- `python main.py repair BTCUSDT restore-from-exchange --dry-run`
- `python main.py` with `RUNTIME_MODE=startup-check-only`
- `python main.py inspect`
- Live repair command, if executed:

## Observed evidence

- Startup reconciliation status:
- `BTCUSDT` present in `open_positions` after run: yes/no
- Restored quantity:
- Entry price source or observed value:
- `reconciliation.csv` restore row captured: yes/no
- `errors.csv` fatal/execution errors absent for this scenario: yes/no
- `repair.csv` unchanged before live repair: yes/no
- Post-run `inspect --json` path:

## Operator decision

- Auto-restore matched expectation: yes/no
- Live `restore-from-exchange` executed: yes/no
- If not executed, why:
- Unblock required: yes/no
- Final conclusion: