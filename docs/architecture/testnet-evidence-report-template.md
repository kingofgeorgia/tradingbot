# Testnet Evidence Report Template

Шаблон для фиксации результатов ручного testnet-прогона по `NEXT-15`, `NEXT-16`, `NEXT-17`.

## Header

- Date:
- Operator:
- Branch:
- Commit SHA:
- Environment:
- Symbol:
- Evidence directory:

## Common pre-flight

- `.env` verified for `APP_MODE=demo`: yes/no
- Existing bot process stopped before run: yes/no
- Pre-run `inspect --json` captured: yes/no
- Dry-run commands captured when applicable: yes/no
- Notes:

## NEXT-15 Report

### Scenario setup

- Local state had open position before run: yes/no
- Exchange quantity was zero before run: yes/no
- Open orders checked on testnet: yes/no
- Commands executed:

### Observed outcome

- Startup reconciliation status:
- `inspect` blocked symbol status:
- Startup issue key:
- `reconciliation.csv` evidence:
- `errors.csv` evidence:
- `repair.csv` unchanged before live repair: yes/no

### Operator decision

- Phantom local state confirmed: yes/no
- Live command executed:
- Post-run `inspect --json` summary:
- Final conclusion:

## NEXT-16 Report

### Scenario setup

- Exchange had open position before run: yes/no
- Local state was empty or missing that position: yes/no
- Commands executed:

### Observed outcome

- Startup reconciliation status:
- Symbol present in `open_positions` after run: yes/no
- Restored quantity:
- Entry price source or observed value:
- `reconciliation.csv` evidence:
- `errors.csv` evidence:
- `repair.csv` unchanged before any live manual action: yes/no

### Follow-up decision

- Auto-restore matched expectation: yes/no
- If not, dry-run result:
- Unblock required: yes/no
- Final conclusion:

## NEXT-17 Report

### Runtime window

- Runtime mode:
- Start time:
- End time:
- Duration:
- Heartbeat interval:

### File growth checkpoints

| Artifact | Start size bytes | End size bytes | Row count start | Row count end | Notes |
| --- | ---: | ---: | ---: | ---: | --- |
| `data/signals.csv` |  |  |  |  |  |
| `data/trades.csv` |  |  |  |  |  |
| `data/errors.csv` |  |  |  |  |  |
| `data/reconciliation.csv` |  |  |  |  |  |
| `data/repair.csv` |  |  |  |  |  |
| `logs/app.log` |  |  | n/a | n/a |  |
| `logs/errors.log` |  |  | n/a | n/a |  |

### Semantics review

- `signals.csv` behavior:
- `trades.csv` behavior:
- `errors.csv` behavior:
- `reconciliation.csv` behavior:
- `repair.csv` behavior:
- Any unexpected growth or noise:

### Rotation policy proposal

- Operator-manageable without rotation: yes/no
- Proposed rotation threshold:
- Archive convention:
- Rotation only while process stopped: yes/no
- Final conclusion:

## Final summary

- NEXT-15 status:
- NEXT-16 status:
- NEXT-17 status:
- Matches backlog expectation overall: yes/no
- Follow-up actions: