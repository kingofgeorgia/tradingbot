# BTCUSDT Evidence Report: NEXT-17

Сценарный предзаполненный отчет для `NEXT-17`: длительная проверка CSV/log behavior и policy ротации.

## Header

- Date:
- Operator:
- Branch: `main`
- Commit SHA:
- Environment: `APP_MODE=demo`
- Symbol: `BTCUSDT`
- Scenario: `NEXT-17`
- Evidence directory:

## Runtime window

- Runtime mode:
- Start time:
- End time:
- Duration:
- Heartbeat interval:
- Why this mode was chosen:

## Commands executed

- `python main.py inspect --json`
- `python main.py` with long-running demo mode
- checkpoint measurement commands
- post-run `python main.py inspect --json`

## File growth checkpoints

| Artifact | Start size bytes | End size bytes | Row count start | Row count end | Notes |
| --- | ---: | ---: | ---: | ---: | --- |
| `data/signals.csv` |  |  |  |  |  |
| `data/trades.csv` |  |  |  |  |  |
| `data/errors.csv` |  |  |  |  |  |
| `data/reconciliation.csv` |  |  |  |  |  |
| `data/repair.csv` |  |  |  |  |  |
| `logs/app.log` |  |  | n/a | n/a |  |
| `logs/errors.log` |  |  | n/a | n/a |  |

## Semantics review

- `signals.csv` behavior:
- `trades.csv` behavior:
- `errors.csv` behavior:
- `reconciliation.csv` behavior:
- `repair.csv` behavior:
- Unexpected growth or noise:

## Rotation policy proposal

- Operator-manageable without rotation: yes/no
- Proposed rotation threshold:
- Archive convention:
- Rotate only while process stopped: yes/no
- Final conclusion: