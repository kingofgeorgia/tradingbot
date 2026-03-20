# Operator Testnet Manual Execution Order

Единый coordination-sheet для фактического ручного прогона `NEXT-15`, `NEXT-16`, `NEXT-17` по уже подготовленным runbook-ам.

## Purpose

- Не придумывать порядок шагов на ходу.
- Пройти `NEXT-15..17` в безопасной последовательности от коротких startup scenarios к длинному runtime observation.
- Собирать evidence в совместимом формате, чтобы потом сразу обновить backlog и operator docs по фактическому поведению.

## Source docs

- `docs/architecture/operator-playbook.md`
- `docs/architecture/operator-testnet-powershell-runbook.md`
- `docs/architecture/operator-testnet-quick-runbook.md`
- `docs/architecture/operator-testnet-next15-btcusdt-snippet.md`
- `docs/architecture/operator-testnet-next17-quick-runbook.md`
- `docs/architecture/testnet-evidence-report-template.md`
- `docs/architecture/testnet-evidence-report-btcusdt-next15.md`
- `docs/architecture/testnet-evidence-report-btcusdt-next16.md`
- `docs/architecture/testnet-evidence-report-btcusdt-next17.md`

## Recommended run order

1. `NEXT-15` on `BTCUSDT`
2. `NEXT-16` on `BTCUSDT`
3. `NEXT-17` after both startup scenarios are archived

Reasoning:

- `NEXT-15` and `NEXT-16` are short `startup-check-only` validations and quickly confirm whether reconciliation behavior matches the documented repair paths.
- `NEXT-17` should run last, because it is a long observation window and should not be interrupted by scenario setup churn from the first two checks.

## Global go/no-go gates

Proceed only if all are true:

- `.env` is confirmed with `APP_MODE=demo`
- no other bot process is running
- current branch and commit SHA are recorded in the evidence report
- pre-run `inspect --json` baseline is captured
- dry-run operator commands are captured before any live repair action

Stop and do not continue to the next scenario if any of these happen:

- unexpected live execution in a startup-only scenario
- fatal or execution error that is not part of the expected scenario
- evidence directory is incomplete or was mixed with an older run
- the symbol remains in an unexplained blocked state after the scenario outcome is recorded

## Scenario 1: NEXT-15

Goal:

- validate `local-position-missing-on-exchange`
- confirm blocked/manual-review path and only then decide whether live `drop-local-state` is justified

Primary doc:

- `docs/architecture/operator-testnet-next15-btcusdt-snippet.md`

Fallback docs:

- `docs/architecture/operator-testnet-quick-runbook.md`
- `docs/architecture/operator-testnet-powershell-runbook.md`

Required evidence:

- `inspect-before.json`
- startup output from `RUNTIME_MODE=startup-check-only`
- `inspect-after.txt`
- `inspect-after.json`
- `next15-drop-dry-run.txt`
- copied `reconciliation.csv`, `errors.csv`, `repair.csv`
- filled `docs/architecture/testnet-evidence-report-btcusdt-next15.md`

Exit condition before moving on:

- actual issue key is captured
- operator decision is explicit: `leave blocked` or `drop-local-state`
- post-run state is archived

## Scenario 2: NEXT-16

Goal:

- validate `exchange-position-without-local-state`
- confirm auto-restore path or record why restore stayed manual

Primary doc:

- `docs/architecture/operator-testnet-quick-runbook.md`

Fallback doc:

- `docs/architecture/operator-testnet-powershell-runbook.md`

Required evidence:

- `inspect-before.json`
- startup output from `RUNTIME_MODE=startup-check-only`
- `inspect-after.txt`
- `inspect-after.json`
- `next16-restore-dry-run.txt`
- copied `reconciliation.csv`, `errors.csv`, `repair.csv`
- filled `docs/architecture/testnet-evidence-report-btcusdt-next16.md`

Exit condition before moving on:

- restored quantity or failed restore path is explicitly recorded
- reconciliation status is recorded as observed, not assumed
- it is clear whether unblock was needed

## Scenario 3: NEXT-17

Goal:

- observe long-running CSV/log growth
- choose a practical manual rotation threshold based on actual evidence

Primary doc:

- `docs/architecture/operator-testnet-next17-quick-runbook.md`

Fallback doc:

- `docs/architecture/operator-testnet-powershell-runbook.md`

Required evidence:

- `inspect-before.json`
- long runtime transcript
- `inspect-after.json`
- `checkpoint-metrics.json`
- `checkpoint-metrics.txt`
- copied CSV/log artifacts from the end of the run
- filled `docs/architecture/testnet-evidence-report-btcusdt-next17.md`

Exit condition:

- runtime duration is recorded
- growth of each CSV/log artifact is recorded
- proposed rotation threshold is explicit and operator-usable

## Evidence directory convention

- Root: `artifacts/manual-testnet/`
- Scenario folders:
  - `quick-<timestamp>-NEXT-15-BTCUSDT`
  - `quick-<timestamp>-NEXT-16-BTCUSDT`
  - `next17-<timestamp>`

Keep each scenario in a separate directory. Do not reuse a previous evidence folder for the next run.

## What to report back after each scenario

For `NEXT-15` and `NEXT-16`:

- exact command set used
- evidence directory path
- startup reconciliation status
- `inspect --json` delta before/after
- whether a live repair was executed
- one-line conclusion: matched expectation / partial mismatch / unexpected behavior

For `NEXT-17`:

- runtime duration
- checkpoint file path
- file growth summary for each artifact
- proposed rotation threshold
- one-line conclusion: manageable / noisy / needs code follow-up

## Backlog follow-up rule

Only close `NEXT-15`, `NEXT-16`, `NEXT-17` after the filled report and evidence directory both exist. If behavior differs from expectation, keep the item open and add the observed deviation into `docs/backlog.md` and `docs/architecture/operator-playbook.md`.
