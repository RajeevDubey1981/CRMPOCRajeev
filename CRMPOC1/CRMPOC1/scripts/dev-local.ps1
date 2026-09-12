# Lightweight local dev WITHOUT Docker Desktop.
# Requires: MySQL running on Windows, api\venv, ui\node_modules
#
# Usage (from repo root):
#   powershell -ExecutionPolicy Bypass -File .\scripts\dev-local.ps1
#
# Then open:
#   UI:  http://localhost:5173
#   API: http://localhost:8010/docs

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$ApiDir = Join-Path $Root "api"
$UiDir = Join-Path $Root "ui"
$Python = Join-Path $ApiDir "venv\Scripts\python.exe"

function Load-DotEnv {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return }
    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#") -or $line -notmatch "=") { return }
        $name, $value = $line.Split("=", 2)
        $name = $name.Trim()
        $value = $value.Trim()
        if ($name) {
            Set-Item -Path "env:$name" -Value $value
        }
    }
}

if (-not (Test-Path $Python)) {
    Write-Error "Missing $Python. Run: cd api; py -3 -m venv venv; .\venv\Scripts\pip install -r requirements.txt"
}
if (-not (Test-Path (Join-Path $UiDir "node_modules"))) {
    Write-Error "Missing ui\node_modules. Run: cd ui; npm install"
}

Load-DotEnv (Join-Path $Root ".env")

# Native Windows: talk to local MySQL directly (no Docker VM).
if ($env:MYSQL_DATABASE_URL) {
    $env:MYSQL_DATABASE_URL = $env:MYSQL_DATABASE_URL -replace "host\.docker\.internal", "127.0.0.1"
}

$env:DATABASE_BACKEND = if ($env:DATABASE_BACKEND) { $env:DATABASE_BACKEND } else { "mysql" }
$env:CORS_ORIGINS = if ($env:CORS_ORIGINS) { $env:CORS_ORIGINS } else { "http://localhost:5173" }
$env:APP_PUBLIC_URL = if ($env:APP_PUBLIC_URL) { $env:APP_PUBLIC_URL } else { "http://localhost:5173" }
$ApiPort = if ($env:API_PORT) { $env:API_PORT } else { "8010" }

Write-Host "=== Indcool local dev (no Docker) ===" -ForegroundColor Cyan
Write-Host "API port: $ApiPort"
Write-Host "UI:  http://localhost:5173"
Write-Host "Docs: http://localhost:${ApiPort}/docs"
Write-Host ""
Write-Host "Tip: stop Docker Desktop first to free CPU/RAM." -ForegroundColor Yellow
Write-Host ""

Push-Location $ApiDir
try {
    & $Python -m alembic -c alembic.ini upgrade head
    & $Python -m app.seed
}
finally {
    Pop-Location
}

$apiCmd = "Set-Location '$ApiDir'; `$env:MYSQL_DATABASE_URL='$($env:MYSQL_DATABASE_URL)'; `$env:DATABASE_BACKEND='$($env:DATABASE_BACKEND)'; `$env:CORS_ORIGINS='$($env:CORS_ORIGINS)'; `$env:APP_PUBLIC_URL='$($env:APP_PUBLIC_URL)'; `$env:PARTNER_AGREEMENT_OTP_CHANNEL='$($env:PARTNER_AGREEMENT_OTP_CHANNEL)'; `$env:EMAIL_ENABLED='$($env:EMAIL_ENABLED)'; `$env:SMTP_HOST='$($env:SMTP_HOST)'; `$env:SMTP_PORT='$($env:SMTP_PORT)'; `$env:SMTP_USER='$($env:SMTP_USER)'; `$env:SMTP_PASSWORD='$($env:SMTP_PASSWORD)'; `$env:SMTP_FROM='$($env:SMTP_FROM)'; `$env:SMTP_FROM_NAME='$($env:SMTP_FROM_NAME)'; `$env:SMTP_USE_TLS='$($env:SMTP_USE_TLS)'; `$env:SMTP_USE_AUTH='$($env:SMTP_USE_AUTH)'; `$env:WHATSAPP_ENABLED='$($env:WHATSAPP_ENABLED)'; `$env:WA_PHONE_NUMBER_ID='$($env:WA_PHONE_NUMBER_ID)'; `$env:WA_ACCESS_TOKEN='$($env:WA_ACCESS_TOKEN)'; `$env:WA_VERIFY_TOKEN='$($env:WA_VERIFY_TOKEN)'; `$env:WA_TEMPLATE_NAME='$($env:WA_TEMPLATE_NAME)'; `$env:WA_TEMPLATE_LANGUAGE='$($env:WA_TEMPLATE_LANGUAGE)'; `$env:GST_LOOKUP_ENABLED='true'; `$env:GST_PROVIDER_URL='$($env:GST_PROVIDER_URL)'; `$env:GST_PROVIDER_API_KEY='$($env:GST_PROVIDER_API_KEY)'; `$env:GST_PROVIDER_API_SECRET='$($env:GST_PROVIDER_API_SECRET)'; `$env:GST_PROVIDER_AUTHORIZATION='$($env:GST_PROVIDER_AUTHORIZATION)'; & '$Python' -m uvicorn app.main:app --reload --host 127.0.0.1 --port $ApiPort"
$uiCmd = "Set-Location '$UiDir'; `$env:VITE_API_BASE_URL='http://localhost:$ApiPort'; npm run dev -- --host 127.0.0.1 --port 5173"

Start-Process powershell -ArgumentList "-NoExit", "-Command", $apiCmd | Out-Null
Start-Sleep -Seconds 2
Start-Process powershell -ArgumentList "-NoExit", "-Command", $uiCmd | Out-Null

Write-Host "Started API and UI in separate windows." -ForegroundColor Green
