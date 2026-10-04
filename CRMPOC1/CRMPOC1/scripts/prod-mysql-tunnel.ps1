# SSH tunnel: local 127.0.0.1:3307 -> prod MySQL 127.0.0.1:3306
# Keep this window open. In another window: netstat -ano | findstr "3307"
# Workbench: 127.0.0.1:3307, user indcool_app, schema indcool

$HostName = "97.74.83.211"
$SshUser = "indcooladmin"
$LocalBind = "127.0.0.1"
$LocalPort = 3307
$RemoteHost = "127.0.0.1"
$RemotePort = 3306
$Forward = "${LocalBind}:${LocalPort}:${RemoteHost}:${RemotePort}"

function Test-TunnelPort {
    $hits = netstat -ano | Select-String ":${LocalPort}\s+.*LISTENING"
    if ($hits) {
        Write-Host "Tunnel looks active:" -ForegroundColor Green
        $hits | ForEach-Object { Write-Host $_.Line }
        return $true
    }
    return $false
}

if (Test-TunnelPort) {
    Write-Host "Workbench: ${LocalBind} port ${LocalPort}"
    exit 0
}

Write-Host "=== Prod MySQL tunnel ===" -ForegroundColor Cyan
Write-Host "Forward: ${LocalBind}:${LocalPort} -> server ${RemoteHost}:${RemotePort}"
Write-Host "SSH user: ${SshUser}@${HostName} (server password, NOT MySQL)"
Write-Host ""
Write-Host "After login, run in a SECOND PowerShell window:"
Write-Host "  netstat -ano | findstr `"3307`""
Write-Host ""

$ssh = Get-Command ssh -ErrorAction SilentlyContinue
if ($ssh) {
    Write-Host "Using OpenSSH (recommended). Enter SSH password when prompted." -ForegroundColor Yellow
    Write-Host "Window will look idle — that is correct. Do not close it." -ForegroundColor Yellow
    Write-Host ""
    & ssh.exe -o ServerAliveInterval=30 `
        -L "${Forward}" `
        -N `
        "${SshUser}@${HostName}"
    exit $LASTEXITCODE
}

$plink = @(
    "${env:ProgramFiles}\PuTTY\plink.exe",
    "${env:ProgramFiles(x86)}\PuTTY\plink.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $plink) {
    Write-Host "Install OpenSSH Client or PuTTY." -ForegroundColor Red
    exit 1
}

Write-Host "Using plink with explicit local bind ${Forward}" -ForegroundColor Yellow
Write-Host "Enter SSH password. At 'Press Return', press Enter once." -ForegroundColor Yellow
Write-Host "You should get a Linux shell; leave this window open." -ForegroundColor Yellow
Write-Host ""

& $plink -ssh "${SshUser}@${HostName}" -L "${Forward}" -t "sleep 86400"
