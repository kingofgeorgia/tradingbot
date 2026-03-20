# Operator Testnet Quick Runbook

Короткий one-page runbook для сценариев `NEXT-15` и `NEXT-16` на `BTCUSDT` под Windows PowerShell.

## Scope

- Только `APP_MODE=demo`
- Только `BTCUSDT`
- Только быстрый evidence run для startup reconciliation scenarios

## Session bootstrap

```powershell
Set-Location "C:\Users\kingofgeorgia\Documents\GitHub\tradingbot"
$Python = "C:/Users/kingofgeorgia/Documents/GitHub/tradingbot/.venv/Scripts/python.exe"
$Symbol = "BTCUSDT"
$Scenario = "NEXT-15"
$RunStamp = Get-Date -Format "yyyyMMdd-HHmmss"
$EvidenceDir = Join-Path $PWD "artifacts\manual-testnet\quick-$RunStamp-$Scenario-$Symbol"
New-Item -ItemType Directory -Force -Path $EvidenceDir | Out-Null
```

## Baseline capture

```powershell
& $Python main.py inspect --json | Tee-Object -FilePath (Join-Path $EvidenceDir "inspect-before.json")
& $Python main.py repair $Symbol restore-from-exchange --dry-run | Tee-Object -FilePath (Join-Path $EvidenceDir "restore-dry-run.txt")
& $Python main.py repair $Symbol drop-local-state --dry-run | Tee-Object -FilePath (Join-Path $EvidenceDir "drop-dry-run.txt")
```

## Common reconciliation run

```powershell
$env:RUNTIME_MODE = "startup-check-only"
& $Python main.py 2>&1 | Tee-Object -FilePath (Join-Path $EvidenceDir "startup-check-only.txt")
Remove-Item Env:RUNTIME_MODE -ErrorAction SilentlyContinue

& $Python main.py inspect | Tee-Object -FilePath (Join-Path $EvidenceDir "inspect-after.txt")
& $Python main.py inspect --json | Tee-Object -FilePath (Join-Path $EvidenceDir "inspect-after.json")
```

## NEXT-15 quick path

Use this when local state contains a BTCUSDT open position but testnet has zero BTCUSDT quantity.

```powershell
$Scenario = "NEXT-15"
& $Python main.py inspect | Tee-Object -FilePath (Join-Path $EvidenceDir "next15-inspect.txt")
& $Python main.py repair $Symbol drop-local-state --dry-run | Tee-Object -FilePath (Join-Path $EvidenceDir "next15-drop-dry-run.txt")
# Only if phantom local state is confirmed:
# & $Python main.py repair $Symbol drop-local-state | Tee-Object -FilePath (Join-Path $EvidenceDir "next15-drop-live.txt")
```

Expected outcome:

- `inspect` shows `BTCUSDT` blocked
- startup issue is `local-position-missing-on-exchange`
- `drop-local-state --dry-run` is available before live action

## NEXT-16 quick path

Use this when testnet has a real BTCUSDT position but local state has none.

```powershell
$Scenario = "NEXT-16"
& $Python main.py inspect | Tee-Object -FilePath (Join-Path $EvidenceDir "next16-inspect.txt")
& $Python main.py inspect --json | Tee-Object -FilePath (Join-Path $EvidenceDir "next16-inspect.json")
& $Python main.py repair $Symbol restore-from-exchange --dry-run | Tee-Object -FilePath (Join-Path $EvidenceDir "next16-restore-dry-run.txt")
```

Expected outcome:

- reconciliation restores or cleanly reports BTCUSDT state
- `open_positions` includes `BTCUSDT` after successful restore path
- no unexpected fatal/execution error appears in startup evidence

## Final step

Fill `docs/architecture/testnet-evidence-report-btcusdt-draft.md` with the actual evidence paths and observed results.