# NEXT-15 BTCUSDT PowerShell Block

Готовый PowerShell block именно для `NEXT-15` без дополнительных переменных сценария.

```powershell
Set-Location "C:\Users\kingofgeorgia\Documents\GitHub\tradingbot"
$Python = "C:/Users/kingofgeorgia/Documents/GitHub/tradingbot/.venv/Scripts/python.exe"
$RunStamp = Get-Date -Format "yyyyMMdd-HHmmss"
$EvidenceDir = Join-Path $PWD "artifacts\manual-testnet\next15-btcusdt-$RunStamp"

New-Item -ItemType Directory -Force -Path $EvidenceDir | Out-Null

& $Python main.py inspect --json | Tee-Object -FilePath (Join-Path $EvidenceDir "inspect-before.json")
& $Python main.py repair BTCUSDT drop-local-state --dry-run | Tee-Object -FilePath (Join-Path $EvidenceDir "drop-dry-run.txt")

$env:RUNTIME_MODE = "startup-check-only"
& $Python main.py 2>&1 | Tee-Object -FilePath (Join-Path $EvidenceDir "startup-check-only.txt")
Remove-Item Env:RUNTIME_MODE -ErrorAction SilentlyContinue

& $Python main.py inspect | Tee-Object -FilePath (Join-Path $EvidenceDir "inspect-after.txt")
& $Python main.py inspect --json | Tee-Object -FilePath (Join-Path $EvidenceDir "inspect-after.json")

Write-Host "Evidence saved to: $EvidenceDir"
```

Expected result:

- `BTCUSDT` остается blocked до ручного решения
- startup issue: `local-position-missing-on-exchange`
- `drop-local-state --dry-run` заранее показывает допустимость manual action
- evidence сохраняется в отдельную папку под `artifacts/manual-testnet`

If phantom local state is confirmed, live command stays explicit and separate:

```powershell
c:/Users/kingofgeorgia/Documents/GitHub/tradingbot/.venv/Scripts/python.exe main.py repair BTCUSDT drop-local-state
```