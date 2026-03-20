# Operator Testnet One-Shot Snippet

Минимальный PowerShell snippet для одного прохода: создать evidence directory, снять baseline и запустить `startup-check-only` без пошагового копирования команд.

```powershell
Set-Location "C:\Users\kingofgeorgia\Documents\GitHub\tradingbot"
$Python = "C:/Users/kingofgeorgia/Documents/GitHub/tradingbot/.venv/Scripts/python.exe"
$Symbol = "BTCUSDT"
$Scenario = "NEXT-15"
$RunStamp = Get-Date -Format "yyyyMMdd-HHmmss"
$EvidenceDir = Join-Path $PWD "artifacts\manual-testnet\oneshot-$RunStamp-$Scenario-$Symbol"

New-Item -ItemType Directory -Force -Path $EvidenceDir | Out-Null

& $Python main.py inspect --json | Tee-Object -FilePath (Join-Path $EvidenceDir "inspect-before.json")
& $Python main.py repair $Symbol restore-from-exchange --dry-run | Tee-Object -FilePath (Join-Path $EvidenceDir "restore-dry-run.txt")
& $Python main.py repair $Symbol drop-local-state --dry-run | Tee-Object -FilePath (Join-Path $EvidenceDir "drop-dry-run.txt")

$env:RUNTIME_MODE = "startup-check-only"
& $Python main.py 2>&1 | Tee-Object -FilePath (Join-Path $EvidenceDir "startup-check-only.txt")
Remove-Item Env:RUNTIME_MODE -ErrorAction SilentlyContinue

& $Python main.py inspect | Tee-Object -FilePath (Join-Path $EvidenceDir "inspect-after.txt")
& $Python main.py inspect --json | Tee-Object -FilePath (Join-Path $EvidenceDir "inspect-after.json")

Write-Host "Evidence saved to: $EvidenceDir"
```

Use:

- set `$Scenario = "NEXT-15"` for `local-position-missing-on-exchange`
- set `$Scenario = "NEXT-16"` for `exchange-position-without-local-state`

After the run, copy the observed results into one of these scenario-specific drafts:

- `docs/architecture/testnet-evidence-report-btcusdt-next15.md`
- `docs/architecture/testnet-evidence-report-btcusdt-next16.md`