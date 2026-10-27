<#
.SYNOPSIS
  Takes a daily backup of the INDcool CRM (database + uploaded files) and stores it in your Google
  Workspace Shared Drive.

.DESCRIPTION
  Runs on your Windows PC (Windows PowerShell 5.1 or newer, with the built-in OpenSSH client: ssh and scp,
  and rclone -- see "One-time setup" below).

    1. logs in to the CRM server and dumps the databases that exist there -- `indcool` (the CRM) always,
       `indcool_sales` and `indcool_marketing` only if those modules are switched on -- each into its own
       compressed file (.sql.gz), and tars the uploaded-files folder (bank statements, Aadhaar/PAN scans,
       signed agreements...), all in the server's /tmp folder;
    2. downloads each file to a temporary folder on this PC and checks it (a dump must open as a complete
       gzip file, and its size and SHA-256 must match what the server made; the files archive must open as
       a complete tar.gz);
    3. uploads the files to your Google Drive Shared Drive with rclone, and checks each one is there with
       the right size afterwards;
    4. only then removes its own temporary files and the server's, and deletes backups on the Shared Drive
       older than -KeepDays.

  Nothing is changed in the databases or in the uploads folder on the server. No password and no Google
  credential is written anywhere by this script -- rclone keeps its own Google sign-in in its own config
  file (see "One-time setup"), and SSH uses a key or asks for a password like the other backup script does.

.PARAMETER RcloneRemote
  The rclone remote name you set up in "One-time setup" below, plus the Shared Drive folder. For example
  "indcool-gdrive:CRM-Backups". Asked for once, then remembered in %USERPROFILE%\.indcool-backup.json.
.PARAMETER Only
  all (default), crm, sales, marketing, or files (only the uploads folder, no database).
.PARAMETER KeepDays
  Backups on the Shared Drive older than this many days are deleted after a good run. Default 30. Use 0 to
  delete nothing.
.PARAMETER SourceHost / SourceUser / SourcePort / SshKey
  The CRM server. Defaults match the production server already used by scripts/deploy.py.
.PARAMETER DryRun
  Shows every step and command without connecting to anything or uploading anything.
.PARAMETER SaveSettings
  Saves the rclone remote, keep-days and source server in %USERPROFILE%\.indcool-backup.json (no
  passwords, no Google credentials -- those live only in rclone's own config).

.EXAMPLE
  .\backup-to-google-drive.ps1 -RcloneRemote "indcool-gdrive:CRM-Backups" -SaveSettings
  .\backup-to-google-drive.ps1                      # later runs use the saved settings
  .\backup-to-google-drive.ps1 -DryRun              # see what it would do
  .\backup-to-google-drive.ps1 -Only crm            # just the CRM database, skip Sales/Marketing/files

.NOTES
  ===================================================================================================
  ONE-TIME SETUP (do this once, before the first real run)
  ===================================================================================================

  1. Install rclone (one .exe, no admin rights needed):
       https://rclone.org/downloads/  ->  "Windows" -> download, unzip, note where rclone.exe ended up
     Either put that folder on your PATH, or always call this script's rclone by its full path -- the
     script looks for rclone.exe on PATH first, then in %USERPROFILE%\.indcool-backup\rclone\rclone.exe.

  2. In Google Drive (as whichever Workspace account should own these backups), create a Shared Drive,
     e.g. named "INDcool CRM Backups". A Shared Drive -- not a folder in My Drive -- so it survives if
     that person's account ever changes, and its membership is managed like a team resource. Add anyone
     else at INDcool who legitimately needs to see these backups (bank statements and KYC documents are
     in here) as a member; keep that list short and deliberate.

  3. Connect rclone to your Google account (one time, opens a browser to log in and click Allow):
       rclone config
         n) New remote
         name> indcool-gdrive
         Storage> drive            (search "drive" in the list, pick "Google Drive")
         client_id>                (leave blank -- press Enter)
         client_secret>            (leave blank -- press Enter)
         scope> 1                  (Full access)
         root_folder_id>           (leave blank -- press Enter)
         service_account_file>     (leave blank -- press Enter)
         Edit advanced config?> n
         Use auto config?> y       (opens your browser -- log in with the Workspace account from step 2)
         Configure this as a Shared Drive?> y
         (pick "INDcool CRM Backups" from the list it shows)
         y) Yes this is OK
     This saves a token in rclone's own config file (%USERPROFILE%\AppData\Roaming\rclone\rclone.conf on
     Windows) -- nobody needs to type a Google password again after this, including for the scheduled run.

  4. Check it worked:
       rclone lsd indcool-gdrive:
     should list the Shared Drive with no error.

  5. Run once by hand to make sure the whole pipeline works end to end:
       .\backup-to-google-drive.ps1 -RcloneRemote "indcool-gdrive:CRM-Backups" -SaveSettings
     then check the files actually appear in the Shared Drive in your browser.

  ===================================================================================================
  DAILY SCHEDULE (after the one-time setup above works)
  ===================================================================================================
  Windows Task Scheduler, for example at 02:30 every night:
    schtasks /Create /SC DAILY /ST 02:30 /TN "INDcool CRM backup to Google Drive" /TR "powershell -NoProfile -ExecutionPolicy Bypass -File \"<full path>\backup-to-google-drive.ps1\""
  This only works if the PC is on (even if locked/logged out) at that time -- check "Run whether user is
  logged on or not" in the Task Scheduler GUI if you want it to run while nobody is signed in.

  ===================================================================================================
  RESTORE (do this only on purpose -- it overwrites data)
  ===================================================================================================
  Download the file you need from the Shared Drive (or: rclone copy indcool-gdrive:CRM-Backups/<file> .),
  then:
    CRM database:       gunzip -c indcool-crm-<time>.sql.gz       | sudo mysql indcool
    Sales database:     gunzip -c indcool-sales-<time>.sql.gz     | sudo mysql indcool_sales
    Marketing database: gunzip -c indcool-marketing-<time>.sql.gz | sudo mysql indcool_marketing
    Uploaded files:     tar -xzf indcool-files-<time>.tar.gz -C <upload dir, e.g. /var/www/indcool/uploads>
#>
[CmdletBinding()]
param(
    [string]$SourceHost = "97.74.83.211",
    [string]$SourceUser = "indcooladmin",
    [int]$SourcePort = 22,
    [string]$RcloneRemote = "",
    [ValidateSet("all", "crm", "sales", "marketing", "files")][string]$Only = "all",
    [int]$KeepDays = -1,
    [string]$SshKey = "",
    [switch]$DryRun,
    [switch]$SaveSettings
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version 2

$SettingsFile = Join-Path $env:USERPROFILE ".indcool-backup.json"
$Databases = @{ crm = "indcool"; sales = "indcool_sales"; marketing = "indcool_marketing" }

function Say([string]$text) { Write-Host $text }
function Step([string]$text) { Write-Host ""; Write-Host "== $text" -ForegroundColor Cyan }

function Get-Settings {
    $s = @{ RcloneRemote = ""; KeepDays = 30; SourceHost = ""; SourceUser = ""; SourcePort = 0; SshKey = "" }
    if (Test-Path $SettingsFile) {
        $saved = Get-Content $SettingsFile -Raw | ConvertFrom-Json
        foreach ($name in @($s.Keys)) {
            if ($saved.PSObject.Properties.Name -contains $name -and $null -ne $saved.$name -and "$($saved.$name)" -ne "") { $s[$name] = $saved.$name }
        }
    }
    return $s
}

function Find-Rclone {
    $onPath = Get-Command rclone -ErrorAction SilentlyContinue
    if ($onPath) { return $onPath.Source }
    $local = Join-Path $env:USERPROFILE ".indcool-backup\rclone\rclone.exe"
    if (Test-Path $local) { return $local }
    throw "rclone.exe was not found on PATH or at $local. See the ONE-TIME SETUP notes at the top of this script (Get-Help .\backup-to-google-drive.ps1 -Full)."
}

function Test-GzipFile([string]$path) {
    $in = [System.IO.File]::OpenRead($path)
    try {
        $gz = New-Object System.IO.Compression.GZipStream($in, [System.IO.Compression.CompressionMode]::Decompress)
        $buffer = New-Object byte[] 262144
        [long]$total = 0
        while (($n = $gz.Read($buffer, 0, $buffer.Length)) -gt 0) { $total += $n }
    }
    finally { $in.Dispose() }
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

function Invoke-Rclone([string]$rclone, [string[]]$rcArgs) {
    if ($DryRun) { Say "   [dry run] rclone $($rcArgs -join ' ')"; return "" }
    $out = & $rclone @rcArgs 2>&1
    if ($LASTEXITCODE -ne 0) { throw "rclone $($rcArgs[0]) failed (exit $LASTEXITCODE): $out" }
    return ($out -join "`n")
}

function Invoke-Backup {
    $saved = Get-Settings
    if (-not $RcloneRemote) { $script:RcloneRemote = $saved.RcloneRemote }
    if ($KeepDays -lt 0) { $script:KeepDays = [int]$saved.KeepDays }
    if (-not $PSBoundParameters.ContainsKey("SourceHost") -and $saved.SourceHost) { $script:SourceHost = $saved.SourceHost }
    if (-not $PSBoundParameters.ContainsKey("SourceUser") -and $saved.SourceUser) { $script:SourceUser = $saved.SourceUser }
    if (-not $PSBoundParameters.ContainsKey("SourcePort") -and $saved.SourcePort) { $script:SourcePort = [int]$saved.SourcePort }
    if (-not $SshKey) { $script:SshKey = $saved.SshKey }

    if (-not $DryRun -and -not $RcloneRemote) { $script:RcloneRemote = (Read-Host "rclone remote and folder (e.g. indcool-gdrive:CRM-Backups)").Trim() }
    if (-not $RcloneRemote) { if ($DryRun) { $script:RcloneRemote = "<rclone remote>:<folder>" } else { throw "The rclone remote (e.g. indcool-gdrive:CRM-Backups) is needed." } }
    if ($KeepDays -gt 0 -and $KeepDays -lt 7) { throw "-KeepDays must be 7 or more (or 0 to delete nothing)." }
    if (-not $DryRun) {
        foreach ($tool in "ssh", "scp") { if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) { throw "$tool was not found. Turn on 'OpenSSH Client' in Windows, Settings, Optional features." } }
    }
    $rclone = if ($DryRun) { "rclone" } else { Find-Rclone }

    if ($SaveSettings -and -not $DryRun) {
        @{ RcloneRemote = $RcloneRemote; KeepDays = $KeepDays; SourceHost = $SourceHost; SourceUser = $SourceUser; SourcePort = $SourcePort; SshKey = $SshKey } |
            ConvertTo-Json | Set-Content -Path $SettingsFile -Encoding UTF8
        Say "Settings saved in $SettingsFile (no passwords, no Google credentials)."
    }

    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $dbKeys = switch ($Only) {
        "crm" { @("crm") }
        "sales" { @("sales") }
        "marketing" { @("marketing") }
        "files" { @() }
        default { @("crm", "sales", "marketing") }
    }
    $includeFiles = ($Only -eq "all" -or $Only -eq "files")
    $tmp = Join-Path $env:TEMP "indcool-backup-$stamp"
    $remoteTmpFiles = @()
    $done = @()

    Step "Backup $stamp : $(($dbKeys + $(if ($includeFiles) { @('files') } else { @() })) -join ', ')   from $SourceUser@$SourceHost   to $RcloneRemote"
    if (-not $DryRun) { New-Item -ItemType Directory -Path $tmp | Out-Null }

    try {
        # ---- databases that actually exist on this server, dumped + downloaded + checked ----
        foreach ($k in $dbKeys) {
            $db = $Databases[$k]
            $exists = Invoke-Remote $SourceUser $SourceHost $SourcePort $SshKey "sudo mysql -N -e `"SHOW DATABASES LIKE '$db'`" | wc -l"
            if (-not $DryRun -and $exists.Trim() -ne "1") { Say "   $db : not on this server, skipped"; continue }

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

        # ---- the uploads folder (bank statements, id proofs, agreements...), tarred + downloaded + checked ----
        if ($includeFiles) {
            $name = "indcool-files-$stamp.tar.gz"
            $remoteTmp = "/tmp/indcool-bk-$stamp-files.tar.gz"
            $remoteTmpFiles += $remoteTmp
            $local = Join-Path $tmp $name

            Step "Archive the uploads folder"
            $tarCmd = "set -e; ( umask 077; UP=`$(sudo grep -i '^UPLOAD_DIR=' /var/www/indcool/api/.env | cut -d= -f2); UP=`${UP:-/var/www/indcool/uploads}; sudo tar -czf $remoteTmp -C `"`$UP`" . ); " +
                      "sudo chown `$(id -un) $remoteTmp; gzip -t $remoteTmp; echo `$(stat -c %s $remoteTmp) `$(sha256sum $remoteTmp | cut -d' ' -f1)"
            $info = Invoke-Remote $SourceUser $SourceHost $SourcePort $SshKey $tarCmd
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
                Say "   downloaded and checked: $size bytes packed, $unpacked bytes unpacked, checksum matches"
            }
            $done += [pscustomobject]@{ Name = $name; Local = $local; Hash = $remoteHash; Size = $remoteSize }
        }

        # ---- upload to the Shared Drive, check each one landed with the right size ----
        Step "Upload to $RcloneRemote"
        foreach ($f in $done) {
            [void](Invoke-Rclone $rclone @("copyto", $f.Local, "$RcloneRemote/$($f.Name)", "--checksum"))
            if (-not $DryRun) {
                $remoteInfo = Invoke-Rclone $rclone @("lsjson", "$RcloneRemote/$($f.Name)")
                $parsed = $remoteInfo | ConvertFrom-Json
                if (-not $parsed -or $parsed[0].Size -ne $f.Size) { throw "$($f.Name) : not found on the Shared Drive after upload, or the size does not match. The backup there must not be trusted." }
                Say "   uploaded and checked: $($f.Name)"
            }
        }

        # ---- old backups on the Shared Drive ----
        if ($KeepDays -gt 0) {
            Step "Backups older than $KeepDays days on $RcloneRemote"
            $gone = Invoke-Rclone $rclone @("delete", $RcloneRemote, "--min-age", "${KeepDays}d", "--include", "indcool-*-*.sql.gz", "-v")
            $gone2 = Invoke-Rclone $rclone @("delete", $RcloneRemote, "--min-age", "${KeepDays}d", "--include", "indcool-files-*.tar.gz", "-v")
            if (-not $DryRun) { Say "   cleanup done" }
        }

        Step "Finished"
        if ($DryRun) { Say "Dry run only: nothing was connected to, uploaded, or changed." }
        else { Say "The backup is on $RcloneRemote :"; $done | ForEach-Object { Say "   $($_.Name)  ($($_.Size) bytes)" } }
    }
    finally {
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
