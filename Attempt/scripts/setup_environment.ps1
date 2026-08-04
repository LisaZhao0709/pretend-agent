param(
    [switch]$UpgradePip
)

$attemptRoot = Split-Path -Parent $PSScriptRoot
$venvPath = Join-Path $attemptRoot '.venv'

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw 'Python was not found on PATH. Install Python 3.11+ first, then run this script again.'
}

if (-not (Test-Path -LiteralPath $venvPath)) {
    python -m venv $venvPath
}

$pythonExe = Join-Path $venvPath 'Scripts\python.exe'
if ($UpgradePip) {
    & $pythonExe -m pip install --upgrade pip
}
& $pythonExe -m pip install -r (Join-Path $attemptRoot 'requirements.txt')
Write-Output "Environment ready: $venvPath"
