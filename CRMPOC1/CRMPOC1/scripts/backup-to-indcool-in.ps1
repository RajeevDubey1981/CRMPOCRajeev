<#
.SYNOPSIS
  Takes a backup of the INDcool CRM databases from the CRM server and stores it on the indcool.in server.

.DESCRIPTION
  Runs on your Windows PC (Windows PowerShell 5.1 or newer, with the built-in OpenSSH client: ssh and scp).

    1. logs in to the CRM server and dumps the database(s): `indcool` (the CRM) and `indcool_sales` (Sales),
       each into its own compressed file (.sql.gz), in the server's /tmp folder;
    2. downloads each file to a temporary folder on this PC and checks it (it must open as a gzip file, and its
       size and SHA-256 must match what the server made);
    3. uploads the files to the indcool.in server and checks them there too (SHA-256);
    4. only then removes its own temporary files, and deletes backups on indcool.in that are older than -KeepDays.

  Nothing is changed in the databases. No password is written anywhere by this script. Use an SSH key so that it
  does not ask for a password (see "SSH keys" below), or type the password when ssh asks for it.

.PARAMETER TargetHost
  The indcool.in server (name or address). Asked for once, then remembered in %USERPROFILE%\.indcool-backup.json.
.PARAMETER TargetUser
  The login on the indcool.in server.
.PARAMETER TargetPath
  The folder on the indcool.in server that keeps the backups. Default: ~/db-backups (made if missing).
.PARAMETER Only
  both (default), crm (only the CRM database) or sales (only the Sales database).
.PARAMETER KeepDays
  Backups on indcool.in older than this many days are deleted after a good run. Default 30. Use 0 to delete nothing.
.PARAMETER SshKey
  Path to a private key file, if you use one.
.PARAMETER DryRun
  Shows every step and command without connecting to anything.
.PARAMETER SaveSettings
  Saves the host, user, folder, ports and key in %USERPROFILE%\.indcool-backup.json (no passwords).

.EXAMPLE
  .\backup-to-indcool-in.ps1 -TargetHost indcool.in -TargetUser backupuser -SaveSettings
  .\backup-to-indcool-in.ps1                      # later runs use the saved settings
  .\backup-to-indcool-in.ps1 -DryRun              # see what it would do

.NOTES
  SSH keys (so that nobody has to type a password, needed if you want to run it on a schedule):
    ssh-keygen -t ed25519 -f $env:USERPROFILE\.ssh\indcool_backup
    then add the .pub file to ~/.ssh/authorized_keys of the CRM server user and of the indcool.in user.
    Run the script with -SshKey $env:USERPROFILE\.ssh\indcool_backup.

  To run it every night with Windows Task Scheduler (after the key works), for example at 02:30:
    schtasks /Create /SC DAILY /ST 02:30 /TN "INDcool DB backup" /TR "powershell -NoProfile -ExecutionPolicy Bypass -File \"<full path>\backup-to-indcool-in.ps1\""

  To restore (do this only on purpose, it overwrites the database):
    CRM:   gunzip -c indcool-crm-<time>.sql.gz   | sudo mysql indcool
    Sales: gunzip -c indcool-sales-<time>.sql.gz | sudo mysql indcool_sales
#>
[CmdletBinding()]
param(
    [string]$SourceHost = "97.74.83.211",
    [string]$SourceUser = "indcooladmin",
    [int]$SourcePort = 22,
    [string]$TargetHost = "",
    [string]$TargetUser = "",
    [int]$TargetPort = 22,
    [string]$TargetPath = "",
    [ValidateSet("both", "crm", "sales")][string]$Only = "both",
    [int]$KeepDays = -1,
    [string]$SshKey = "",
    [switch]$DryRun,
    [switch]$SaveSettings
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version 2

$SettingsFile = Join-Path $env:USERPROFILE ".indcool-backup.json"
$Databases = @{ crm = "indcool"; sales = "indcool_sales" }

function Say([string]$text) { Write-Host $text }
function Step([string]$text) { Write-Host ""; Write-Host "== $text" -ForegroundColor Cyan }

function Get-Settings {
    $s = @{ TargetHost = ""; TargetUser = ""; TargetPath = "~/db-backups"; TargetPort = 22; SshKey = ""; KeepDays = 30; SourceHost = ""; SourceUser = ""; SourcePort = 0 }
    if (Test-Path $SettingsFile) {
        $saved = Get-Content $SettingsFile -Raw | ConvertFrom-Json
        foreach ($name in @($s.Keys)) {
            if ($saved.PSObject.Properties.Name -contains $name -and $null -ne $saved.$name -and "$($saved.$name)" -ne "") { $s[$name] = $saved.$name }
        }
    }
    return $s
}

function Remote-Path([string]$path) {
    # For a shell command on the server: ~/x becomes $HOME/x. No double quotes are used anywhere in a command sent
    # through ssh, because Windows PowerShell 5.1 mangles them. So the folder name may not contain a space.
    if ($path -match '\s') { throw "The backup folder name must not contain a space: $path" }
    if ($path -like "~/*") { return '$HOME/' + $path.Substring(2) }
    return "'" + $path.Replace("'", "'\''") + "'"
}

function Scp-Path([string]$path) {
    # for scp: a path in the home folder is written without the ~/ (scp starts in the home folder)
    if ($path -like "~/*") { return $path.Substring(2) }
    return $path
}

function Test-GzipFile([string]$path) {
    # Opens the file as gzip and reads it to the end. Returns the unpacked size. Throws if the file is damaged.
    $in = [System.IO.File]::OpenRead($path)
    try {
        $gz = New-Object System.IO.Compression.GZipStream($in, [System.IO.Compression.CompressionMode]::Decompress)
        $buffer = New-Object byte[] 262144
        [long]$total = 0
        while (($n = $gz.Read($buffer, 0, $buffer.Length)) -gt 0) { $total += $n }
    }
    finally { $in.Dispose() }
    # .NET does not complain about a gzip file that was cut short, so the end of the file is checked as well: the last
    # four bytes of a gzip file hold the unpacked size (modulo 2^32) and must agree with what was really unpacked.
    $all = [System.IO.File]::OpenRead($path)
    try {
        [void]$all.Seek(-4, [System.IO.SeekOrigin]::End)
        $tail = New-Object byte[] 4
        [void]$all.Read($tail, 0, 4)
    }
    finally { $all.Dispose() }
    [long]$declared = [System.BitConverter]::ToUInt32($tail, 0)
    if (($total % 4294967296) -ne $declared) { throw "$path is not a complete gzip file (it was cut short or is damaged)." }
    return $total
}

function Get-Sha256([string]$path) { return (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLower() }

function New-SshArgs([string]$user, [string]$hostName, [int]$port, [string]$key) {
    $a = @("-o", "ServerAliveInterval=30", "-o", "StrictHostKeyChecking=accept-new", "-p", "$port")
    if ($key) { $a += @("-i", $key) }
    return $a
}

function Invoke-Remote([string]$user, [string]$hostName, [int]$port, [string]$key, [string]$command) {
    $a = New-SshArgs $user $hostName $port $key
    if ($DryRun) { Say "   [dry run] ssh $user@$hostName : $command"; return "" }
    $out = & ssh @a "$user@$hostName" $command
    if ($LASTEXITCODE -ne 0) { throw "The command on $hostName failed (exit $LASTEXITCODE)." }
    return ($out -join "`n")
}

function Copy-Scp([string]$from, [string]$to, [int]$port, [string]$key) {
    $a = @("-o", "StrictHostKeyChecking=accept-new", "-P", "$port")
    if ($key) { $a += @("-i", $key) }
    if ($DryRun) { Say "   [dry run] scp $from  ->  $to"; return }
    & scp @a $from $to
    if ($LASTEXITCODE -ne 0) { throw "Copying failed (exit $LASTEXITCODE): $from" }
}

function Invoke-Backup {
    # ---- settings: what was typed, else what was saved, else ask ----
    $saved = Get-Settings
    if (-not $TargetHost) { $script:TargetHost = $saved.TargetHost }
    if (-not $TargetUser) { $script:TargetUser = $saved.TargetUser }
    if (-not $TargetPath) { $script:TargetPath = $saved.TargetPath }
    if (-not $SshKey) { $script:SshKey = $saved.SshKey }
    if (-not $PSBoundParameters.ContainsKey("TargetPort") -and $saved.TargetPort) { $script:TargetPort = [int]$saved.TargetPort }
    if ($KeepDays -lt 0) { $script:KeepDays = [int]$saved.KeepDays }
    if (-not $PSBoundParameters.ContainsKey("SourceHost") -and $saved.SourceHost) { $script:SourceHost = $saved.SourceHost }
    if (-not $PSBoundParameters.ContainsKey("SourceUser") -and $saved.SourceUser) { $script:SourceUser = $saved.SourceUser }
    if (-not $PSBoundParameters.ContainsKey("SourcePort") -and $saved.SourcePort) { $script:SourcePort = [int]$saved.SourcePort }

    if (-not $DryRun) {
        if (-not $TargetHost) { $script:TargetHost = (Read-Host "indcool.in server (name or address)").Trim() }
        if (-not $TargetUser) { $script:TargetUser = (Read-Host "Login name on $TargetHost").Trim() }
    } else {
        if (-not $TargetHost) { $script:TargetHost = "<indcool.in server>" }
        if (-not $TargetUser) { $script:TargetUser = "<login>" }
    }
    if (-not $TargetHost -or -not $TargetUser) { throw "The indcool.in server and the login are needed." }
    if ($KeepDays -gt 0 -and $KeepDays -lt 7) { throw "-KeepDays must be 7 or more (or 0 to delete nothing)." }
    if (-not $DryRun) {
        foreach ($tool in "ssh", "scp") { if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) { throw "$tool was not found. Turn on 'OpenSSH Client' in Windows, Settings, Optional features." } }
    }
    if ($SaveSettings -and -not $DryRun) {
        @{ TargetHost = $TargetHost; TargetUser = $TargetUser; TargetPath = $TargetPath; TargetPort = $TargetPort; SshKey = $SshKey; KeepDays = $KeepDays; SourceHost = $SourceHost; SourceUser = $SourceUser; SourcePort = $SourcePort } |
            ConvertTo-Json | Set-Content -Path $SettingsFile -Encoding UTF8
        Say "Settings saved in $SettingsFile (no passwords)."
    }

    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $keys = switch ($Only) { "crm" { @("crm") } "sales" { @("sales") } default { @("crm", "sales") } }
    $tmp = Join-Path $env:TEMP "indcool-backup-$stamp"
    $remoteTmpFiles = @()
    $done = @()

    Step "Backup $stamp : $($keys -join ' and ')   from $SourceUser@$SourceHost   to $TargetUser@${TargetHost}:$TargetPath"
    if (-not $DryRun) { New-Item -ItemType Directory -Path $tmp | Out-Null }

    try {
        # ---- 1 and 2: dump on the CRM server, download, check ----
        foreach ($k in $keys) {
            $db = $Databases[$k]
            $name = "indcool-$k-$stamp.sql.gz"
            $remoteTmp = "/tmp/indcool-bk-$stamp-$k.sql.gz"
            $remoteTmpFiles += $remoteTmp
            $local = Join-Path $tmp $name

            Step "Dump $db"
            $dump = "set -e; ( umask 077; sudo mysqldump --single-transaction --routines --triggers --no-tablespaces --default-character-set=utf8mb4 $db | gzip -c > $remoteTmp ); " +
                    "sudo chown `$(id -un) $remoteTmp; gzip -t $remoteTmp; echo `$(stat -c %s $remoteTmp) `$(sha256sum $remoteTmp | cut -d' ' -f1)"
            $info = Invoke-Remote $SourceUser $SourceHost $SourcePort $SshKey $dump
            $remoteSize = 0; $remoteHash = ""
            if (-not $DryRun) {
                $parts = ($info.Trim() -split "\s+")
                $remoteSize = [long]$parts[0]; $remoteHash = $parts[1]
                Say "   made on the server: $remoteSize bytes"
            }

            Step "Download $name"
            Copy-Scp "$SourceUser@${SourceHost}:$remoteTmp" $local $SourcePort $SshKey
            if (-not $DryRun) {
                $size = (Get-Item $local).Length
                if ($size -ne $remoteSize) { throw "$name : the downloaded size ($size) is not the size on the server ($remoteSize)." }
                $unpacked = Test-GzipFile $local
                if ((Get-Sha256 $local) -ne $remoteHash) { throw "$name : the checksum after the download does not match the server." }
                if ($unpacked -lt 1000) { throw "$name : the dump is suspiciously small ($unpacked bytes unpacked)." }
                Say "   downloaded and checked: $size bytes packed, $unpacked bytes unpacked, checksum matches"
            }
            $done += [pscustomobject]@{ Name = $name; Local = $local; Hash = $remoteHash; Size = $remoteSize }
        }

        # ---- 3: store on the indcool.in server and check there ----
        Step "Store on $TargetHost"
        $rp = Remote-Path $TargetPath
        [void](Invoke-Remote $TargetUser $TargetHost $TargetPort $SshKey "mkdir -p $rp && chmod 700 $rp")
        $dest = (Scp-Path $TargetPath)
        foreach ($f in $done) {
            Copy-Scp $f.Local "$TargetUser@${TargetHost}:$dest/$($f.Name)" $TargetPort $SshKey
            $check = Invoke-Remote $TargetUser $TargetHost $TargetPort $SshKey "cd $rp && chmod 600 '$($f.Name)' && sha256sum '$($f.Name)' | cut -d' ' -f1"
            if (-not $DryRun) {
                if ($check.Trim() -ne $f.Hash) { throw "$($f.Name) : the checksum on $TargetHost does not match. The backup there must not be trusted." }
                Say "   stored and checked: $($f.Name)"
            }
        }

        # ---- 4: old backups ----
        if ($KeepDays -gt 0) {
            Step "Backups older than $KeepDays days on $TargetHost"
            $gone = Invoke-Remote $TargetUser $TargetHost $TargetPort $SshKey "find $rp -maxdepth 1 -type f -name 'indcool-*-*.sql.gz' -mtime +$KeepDays -print -delete"
            if (-not $DryRun) { if ($gone.Trim()) { Say "   deleted:`n$gone" } else { Say "   none to delete" } }
        }

        Step "Finished"
        if ($DryRun) { Say "Dry run only: nothing was connected to or changed." }
        else { Say "The backup is on $TargetHost in $TargetPath :"; $done | ForEach-Object { Say "   $($_.Name)  ($($_.Size) bytes)" } }
    }
    finally {
        # the server's temporary files and this PC's temporary folder are always removed, good run or not
        if (-not $DryRun -and $remoteTmpFiles.Count -gt 0) {
            try { [void](Invoke-Remote $SourceUser $SourceHost $SourcePort $SshKey ("rm -f " + ($remoteTmpFiles -join " "))) } catch { Write-Warning "Could not remove the temporary files on the CRM server: $($remoteTmpFiles -join ' ')" }
        }
        if (-not $DryRun -and (Test-Path $tmp)) { Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue }
    }
}

# Run only when the script is started, not when it is loaded by a test (dot-sourced).
if ($MyInvocation.InvocationName -ne ".") {
    try { Invoke-Backup }
    catch { Write-Host ""; Write-Host "BACKUP FAILED: $($_.Exception.Message)" -ForegroundColor Red; exit 1 }
}
