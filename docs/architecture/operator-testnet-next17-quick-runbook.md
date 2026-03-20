# Operator Testnet Quick Runbook: NEXT-17

Сокращенный PowerShell runbook для `NEXT-17`: длительная ревизия CSV/log behavior и выбор practical rotation policy.

## Scope

- `APP_MODE=demo`
- controlled runtime observation
- focus on file growth, semantics and operator-manageable rotation threshold

## Quick session

```powershell
Set-Location "C:\Users\kingofgeorgia\Documents\GitHub\tradingbot"
$Python = "C:/Users/kingofgeorgia/Documents/GitHub/tradingbot/.venv/Scripts/python.exe"
$RunStamp = Get-Date -Format "yyyyMMdd-HHmmss"
$EvidenceDir = Join-Path $PWD "artifacts\manual-testnet\next17-$RunStamp"
New-Item -ItemType Directory -Force -Path $EvidenceDir | Out-Null

& $Python main.py inspect --json | Tee-Object -FilePath (Join-Path $EvidenceDir "inspect-before.json")

$env:RUNTIME_MODE = "observe-only"
$env:RUN_ONCE = "false"
& $Python main.py 2>&1 | Tee-Object -FilePath (Join-Path $EvidenceDir "long-runtime.txt")
Remove-Item Env:RUNTIME_MODE -ErrorAction SilentlyContinue
Remove-Item Env:RUN_ONCE -ErrorAction SilentlyContinue

& $Python main.py inspect --json | Tee-Object -FilePath (Join-Path $EvidenceDir "inspect-after.json")
```

## Checkpoint metrics

```powershell
$FilesToMeasure = @(
    "data/signals.csv",
    "data/trades.csv",
    "data/errors.csv",
    "data/reconciliation.csv",
    "data/repair.csv",
    "logs/app.log",
    "logs/errors.log"
)

$Measurements = foreach ($RelativePath in $FilesToMeasure) {
    if (Test-Path $RelativePath) {
        $File = Get-Item $RelativePath
        $Rows = if ($File.Extension -eq ".csv") { (Get-Content $RelativePath).Count } else { $null }
        [PSCustomObject]@{
            Path = $RelativePath
            SizeBytes = $File.Length
            Rows = $Rows
            CollectedAt = Get-Date -Format o
        }
    }
}

$Measurements | ConvertTo-Json -Depth 3 | Set-Content -Encoding utf8 (Join-Path $EvidenceDir "checkpoint-metrics.json")
$Measurements | Format-Table -AutoSize | Out-String | Tee-Object -FilePath (Join-Path $EvidenceDir "checkpoint-metrics.txt")
```

## Expected review points

- `signals.csv` grows with logged signals
- `trades.csv` stays quiet in `observe-only` unless there was real execution outside the scenario
- `errors.csv` contains only actual runtime/API failures
- `reconciliation.csv` changes on startup reconciliation, not every cycle
- `repair.csv` changes only on manual repair/unblock or state recovery actions

## Final step

Fill `docs/architecture/testnet-evidence-report-btcusdt-next17.md` with actual runtime duration, file growth and chosen rotation threshold.