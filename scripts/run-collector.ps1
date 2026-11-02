$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $repoRoot
$pythonExe = Join-Path $repoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) { throw 'Crie .venv e instale o coletor primeiro.' }
$logDir = Join-Path $repoRoot 'data\logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logFile = Join-Path $logDir ((Get-Date -Format 'yyyy-MM-dd') + '.log')
# Environment ALUGAI_DATABASE_URL is inherited from the scheduled task user.
& $pythonExe -m alugai discover --limit 50 --max-pages 1 *>> $logFile
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $pythonExe -m alugai refresh --limit 50 --stale-hours 24 *>> $logFile
exit $LASTEXITCODE
