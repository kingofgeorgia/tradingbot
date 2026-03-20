# Operator Testnet PowerShell Runbook

Готовый Windows PowerShell runbook для ручного testnet-прогона сценариев `NEXT-15`, `NEXT-16`, `NEXT-17`.

## Scope

- Использовать только с `APP_MODE=demo`.
- Запускать из корня репозитория.
- Перед любыми manual repair actions убедиться, что бот не запущен в другом окне.
- Перед запуском сценария свериться с `docs/architecture/operator-testnet-manual-execution-order.md`, чтобы не пропустить baseline capture и exit gates между `NEXT-15`, `NEXT-16`, `NEXT-17`.

## Session setup

```powershell
Set-Location "C:\Users\kingofgeorgia\Documents\GitHub\tradingbot"
$Python = "C:/Users/kingofgeorgia/Documents/GitHub/tradingbot/.venv/Scripts/python.exe"
$RunStamp = Get-Date -Format "yyyyMMdd-HHmmss"
$Scenario = "NEXT-15"
$Symbol = "BTCUSDT"
$EvidenceRoot = Join-Path $PWD "artifacts\manual-testnet"
$EvidenceDir = Join-Path $EvidenceRoot "$RunStamp-$Scenario-$Symbol"
New-Item -ItemType Directory -Force -Path $EvidenceDir | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $EvidenceDir "before") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $EvidenceDir "after") | Out-Null
```

## Pre-flight snapshot

```powershell
$ArtifactsToCopy = @(
    "data/state.json",
    "data/signals.csv",
    "data/trades.csv",
    "data/errors.csv",
    "data/reconciliation.csv",
    "data/repair.csv",
    "logs/app.log",
    "logs/errors.log"
)

foreach ($RelativePath in $ArtifactsToCopy) {
    if (Test-Path $RelativePath) {
        $Destination = Join-Path $EvidenceDir "before\$(Split-Path $RelativePath -Leaf)"
        Copy-Item $RelativePath $Destination -Force
    }
}

& $Python main.py inspect --json | Tee-Object -FilePath (Join-Path $EvidenceDir "before\inspect-before.json")
```

## Optional dry-run checks

```powershell
& $Python main.py repair $Symbol restore-from-exchange --dry-run | Tee-Object -FilePath (Join-Path $EvidenceDir "before\repair-restore-dry-run.txt")
& $Python main.py repair $Symbol drop-local-state --dry-run | Tee-Object -FilePath (Join-Path $EvidenceDir "before\repair-drop-dry-run.txt")
& $Python main.py unblock $Symbol --dry-run | Tee-Object -FilePath (Join-Path $EvidenceDir "before\unblock-dry-run.txt")
```

## Startup-check-only run

```powershell
$env:RUNTIME_MODE = "startup-check-only"
& $Python main.py 2>&1 | Tee-Object -FilePath (Join-Path $EvidenceDir "startup-check-only.txt")
Remove-Item Env:RUNTIME_MODE -ErrorAction SilentlyContinue
```

## Post-run snapshot

```powershell
& $Python main.py inspect | Tee-Object -FilePath (Join-Path $EvidenceDir "after\inspect-after.txt")
& $Python main.py inspect --json | Tee-Object -FilePath (Join-Path $EvidenceDir "after\inspect-after.json")

foreach ($RelativePath in $ArtifactsToCopy) {
    if (Test-Path $RelativePath) {
        $Destination = Join-Path $EvidenceDir "after\$(Split-Path $RelativePath -Leaf)"
        Copy-Item $RelativePath $Destination -Force
    }
}
```

## NEXT-15 commands

Use when local state has an open position, but Binance testnet shows no position.

```powershell
$Scenario = "NEXT-15"
$Symbol = "BTCUSDT"

& $Python main.py inspect | Tee-Object -FilePath (Join-Path $EvidenceDir "after\next15-inspect.txt")
& $Python main.py inspect --json | Tee-Object -FilePath (Join-Path $EvidenceDir "after\next15-inspect.json")

# Only if phantom local state is confirmed:
& $Python main.py repair $Symbol drop-local-state --dry-run | Tee-Object -FilePath (Join-Path $EvidenceDir "after\next15-drop-dry-run.txt")
# & $Python main.py repair $Symbol drop-local-state | Tee-Object -FilePath (Join-Path $EvidenceDir "after\next15-drop-live.txt")
```

Expected evidence:

- blocked symbol in `inspect`
- startup issue `local-position-missing-on-exchange`
- new row in copied `reconciliation.csv`
- startup reconciliation record in copied `errors.csv`
- no new row in `repair.csv` before a real manual repair

## NEXT-16 commands

Use when Binance testnet has a real position, while local state has none.

```powershell
$Scenario = "NEXT-16"
$Symbol = "BTCUSDT"

& $Python main.py inspect | Tee-Object -FilePath (Join-Path $EvidenceDir "after\next16-inspect.txt")
& $Python main.py inspect --json | Tee-Object -FilePath (Join-Path $EvidenceDir "after\next16-inspect.json")
& $Python main.py repair $Symbol restore-from-exchange --dry-run | Tee-Object -FilePath (Join-Path $EvidenceDir "after\next16-restore-dry-run.txt")
```

Expected evidence:

- reconciliation status `recovered-with-adjustments` or `clean`
- symbol present in `open_positions`
- restore path visible in copied `reconciliation.csv`
- no new fatal/execution error for this scenario in copied `errors.csv`

## NEXT-17 long-runtime run

Preferred mode is demo trade. If execution must stay suppressed, use `observe-only`.

```powershell
$Scenario = "NEXT-17"
$Symbol = "BTCUSDT"
$env:RUNTIME_MODE = "observe-only"
$env:RUN_ONCE = "false"

& $Python main.py 2>&1 | Tee-Object -FilePath (Join-Path $EvidenceDir "long-runtime.txt")

Remove-Item Env:RUNTIME_MODE -ErrorAction SilentlyContinue
Remove-Item Env:RUN_ONCE -ErrorAction SilentlyContinue
```

Checkpoint helper:

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

## End-of-run archive hint

```powershell
Compress-Archive -Path $EvidenceDir -DestinationPath "$EvidenceDir.zip" -Force
```

## Operator note

After the run, fill the report template in `docs/architecture/testnet-evidence-report-template.md`, attach paths to the collected evidence directory and update the matching scenario sheet from `docs/architecture/operator-testnet-manual-execution-order.md`.