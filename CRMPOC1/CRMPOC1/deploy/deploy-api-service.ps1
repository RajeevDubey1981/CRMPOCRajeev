$ErrorActionPreference = "Stop"

function Copy-FolderContent {
  param(
    [Parameter(Mandatory = $true)][string]$Source,
    [Parameter(Mandatory = $true)][string]$Destination
  )

  if (Test-Path $Destination) {
    Remove-Item -LiteralPath $Destination -Recurse -Force
  }

  New-Item -ItemType Directory -Path $Destination | Out-Null

  $robocopyArgs = @(
    $Source,
    $Destination,
    "/E",
    "/XD", "venv", "__pycache__", ".pytest_cache", ".mypy_cache", "tests", "uploads",
    "/XF", "*.pyc", "*.pyo", "*.log", "*.sql", "tmp_*", "_gst_probe*", "dump_local.py"
  )

  & robocopy @robocopyArgs | Out-Null
  $exitCode = $LASTEXITCODE
  if ($exitCode -ge 8) {
    throw "Failed to copy API files. Robocopy exit code: $exitCode"
  }
}

$root = Split-Path -Parent $PSScriptRoot
$apiSourceDir = Join-Path $root "api"
$publishRoot = Join-Path $root "publish"
$apiPublishDir = Join-Path $publishRoot "api"
$uploadsDir = Join-Path $publishRoot "uploads"
$venvDir = Join-Path $apiPublishDir "venv"
$pythonExe = Join-Path $venvDir "Scripts\python.exe"
$pipExe = Join-Path $venvDir "Scripts\pip.exe"
$envTemplate = Join-Path $PSScriptRoot "api.env.example"
$envTarget = Join-Path $apiPublishDir ".env"
$runCmd = Join-Path $apiPublishDir "run-api.cmd"
$installTaskCmd = Join-Path $apiPublishDir "install-api-task.cmd"
$startTaskCmd = Join-Path $apiPublishDir "start-api-task.cmd"
$stopTaskCmd = Join-Path $apiPublishDir "stop-api-task.cmd"
$removeTaskCmd = Join-Path $apiPublishDir "remove-api-task.cmd"
$taskName = "Indcool CRM API"

Write-Host "Preparing API publish folder..." -ForegroundColor Cyan

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  throw "python is not installed or not available in PATH."
}

Copy-FolderContent -Source $apiSourceDir -Destination $apiPublishDir

if (-not (Test-Path $uploadsDir)) {
  New-Item -ItemType Directory -Path $uploadsDir | Out-Null
}

Push-Location $apiPublishDir
try {
  python -m venv venv
  if ($LASTEXITCODE -ne 0) {
    throw "python -m venv failed."
  }

  & $pipExe install --upgrade pip
  if ($LASTEXITCODE -ne 0) {
    throw "pip upgrade failed."
  }

  & $pipExe install -r requirements.txt
  if ($LASTEXITCODE -ne 0) {
    throw "pip install -r requirements.txt failed."
  }

  if (-not (Test-Path $envTarget)) {
    Copy-Item -LiteralPath $envTemplate -Destination $envTarget -Force
  }
}
finally {
  Pop-Location
}

$runCmdContent = @"
@echo off
cd /d "$apiPublishDir"
call "$venvDir\Scripts\activate.bat"
set PYTHONUNBUFFERED=1
"$pythonExe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
"@

Set-Content -LiteralPath $runCmd -Value $runCmdContent -Encoding ASCII

$installTaskContent = @"
@echo off
schtasks /Create /F /SC ONSTART /RL HIGHEST /RU SYSTEM /TN "$taskName" /TR "\"$runCmd\""
echo.
echo Scheduled task created: $taskName
pause
"@
Set-Content -LiteralPath $installTaskCmd -Value $installTaskContent -Encoding ASCII

$startTaskContent = @"
@echo off
schtasks /Run /TN "$taskName"
pause
"@
Set-Content -LiteralPath $startTaskCmd -Value $startTaskContent -Encoding ASCII

$stopTaskContent = @"
@echo off
schtasks /End /TN "$taskName"
pause
"@
Set-Content -LiteralPath $stopTaskCmd -Value $stopTaskContent -Encoding ASCII

$removeTaskContent = @"
@echo off
schtasks /Delete /F /TN "$taskName"
pause
"@
Set-Content -LiteralPath $removeTaskCmd -Value $removeTaskContent -Encoding ASCII

Write-Host ""
Write-Host "API publish folder created:" -ForegroundColor Green
Write-Host $apiPublishDir
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Edit $envTarget"
Write-Host "2. Run alembic upgrade head from the API publish folder"
Write-Host "3. Run python -m app.seed from the API publish folder"
Write-Host "4. Double-click install-api-task.cmd as Administrator"
Write-Host "5. Double-click start-api-task.cmd"
