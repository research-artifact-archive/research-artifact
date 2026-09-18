<#
.SYNOPSIS
  One-command, resumable driver for the FG-DUCS Xeon campaigns.

.DESCRIPTION
  Place this file next to run-windows.ps1 inside the extracted bundle folder
  (e.g. C:\fgducs\fg-ducs-xeon-campaign\run-all.ps1) and run:

      powershell -NoProfile -ExecutionPolicy Bypass -File .\run-all.ps1

  For each campaign, in order, it runs  stage1 -> stage2 (if the campaign has
  repetitions) -> collect  by invoking scripts\campaign.py exactly like
  run-windows.ps1 does (same PATH/PYTHONUTF8 handling, same host check).
  Everything is serial (one JVM at a time). Re-running the same command resumes:
  finished, timed-out, OOM and crashed cells are never re-executed (README).

  Differences from calling run-windows.ps1 by hand:
    * native stderr does not abort the driver (Windows PowerShell 5.1 turns
      redirected stderr lines into errors when $ErrorActionPreference = 'Stop');
    * the machine is kept awake while the driver runs;
    * a transcript of the whole run is written to raw\run-all-<timestamp>.log.

.PARAMETER Campaigns
  Ordered list. Default: rq3, rq4_controlled, rq4_independent, rq4_travel, rq4_hub.
.PARAMETER Stage1Only
  Run only stage1 + collect for every selected campaign (no extra repetitions).
.PARAMETER SkipHostCheck
  Skip the "CPU name contains W-2265" check (only if the CPU string is formatted
  differently on the same Xeon host; the campaign must still run on that host).
#>
param(
    [string[]]$Campaigns = @('rq3','rq4_controlled','rq4_independent','rq4_travel','rq4_hub'),
    [string]$Python = 'python',
    [string]$Java = 'java',
    [switch]$Stage1Only,
    [switch]$SkipHostCheck
)

Set-StrictMode -Version Latest
# "-Campaigns rq3,rq4_hub" arrives as ONE string when the script is started with -File; split it.
$Campaigns = @($Campaigns | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ })
# Native programs (java, python) write to stderr legitimately. With 'Stop' Windows
# PowerShell 5.1 would abort the run on the first such line, so keep 'Continue' and
# check $LASTEXITCODE explicitly instead.
$ErrorActionPreference = 'Continue'

Push-Location $PSScriptRoot
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
New-Item -ItemType Directory -Force -Path (Join-Path $PSScriptRoot 'raw') | Out-Null
$transcript = Join-Path $PSScriptRoot ('raw\run-all-' + $stamp + '.log')
Start-Transcript -Path $transcript -Append | Out-Null

function Fail([string]$Message) {
    Write-Host ''
    Write-Host ('ERROR: ' + $Message) -ForegroundColor Red
    try { Stop-Transcript | Out-Null } catch {}
    Pop-Location
    exit 2
}

# ---------------------------------------------------------------- executables
$pythonCmd = Get-Command $Python -ErrorAction SilentlyContinue
if ($null -eq $pythonCmd) { Fail ('Python not found: ' + $Python + '  (install 64-bit Python 3.10+ from python.org with "Add to PATH", or pass -Python C:\path\python.exe)') }
$javaCmd = Get-Command $Java -ErrorAction SilentlyContinue
if ($null -eq $javaCmd) { Fail ('Java not found: ' + $Java + '  (install 64-bit JDK 17 from adoptium.net, or pass -Java C:\path\java.exe)') }
$PythonPath = $pythonCmd.Source
$JavaPath = $javaCmd.Source
$env:PATH = (Split-Path -Parent $JavaPath) + ';' + $env:PATH
$env:PYTHONUTF8 = '1'

$pyVersion = (& $PythonPath --version 2>&1 | Out-String).Trim()
if ($pyVersion -notmatch 'Python 3\.(1[0-9]|[2-9][0-9])') {
    Fail ('Need Python 3.10 or newer, found: "' + $pyVersion + '". If this is the Microsoft Store alias, install Python from python.org and pass -Python <full path>.')
}
$javaVersion = (& $JavaPath -version 2>&1 | Out-String)
if ($javaVersion -notmatch 'version "17\.') {
    Fail ('Need JDK 17 (the campaign refuses other majors). java -version reported: ' + $javaVersion.Trim())
}
$javac = Join-Path (Split-Path -Parent $JavaPath) 'javac.exe'
if (-not (Test-Path $javac)) {
    Write-Warning 'javac.exe not found next to java.exe: this looks like a JRE. The startup probe needs a JDK 17. Install a JDK if the probe fails.'
}

# ---------------------------------------------------------------- host check
$cpuName = ''
try { $cpuName = (Get-CimInstance Win32_Processor | Select-Object -First 1).Name } catch {}
if (-not $SkipHostCheck) {
    if ($cpuName -notmatch 'W-2265') { Fail ('Expected the fixed Xeon W-2265 host; found: "' + $cpuName + '". Use -SkipHostCheck only if this IS the Xeon and the CPU string merely differs.') }
}

# ---------------------------------------------------------------- keep awake
try {
    Add-Type -Namespace FgDucs -Name Power -MemberDefinition @'
[System.Runtime.InteropServices.DllImport("kernel32.dll", SetLastError = true)]
public static extern uint SetThreadExecutionState(uint esFlags);
'@
    # ES_CONTINUOUS (0x80000000) | ES_SYSTEM_REQUIRED (0x00000001) = 2147483649
    [void][FgDucs.Power]::SetThreadExecutionState([uint32]2147483649)
    Write-Host 'Keep-awake enabled for this PowerShell session (sleep suppressed while the driver runs).'
} catch { Write-Warning ('Keep-awake could not be enabled: ' + $_.Exception.Message + '  -> disable sleep manually.') }

# ---------------------------------------------------------------- host summary
Write-Host '=== Host summary ==='
Write-Host ('CPU   : ' + $cpuName)
try { $mem = (Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory; Write-Host ('RAM   : {0:N1} GiB (campaign requires >= 240 GiB)' -f ($mem / 1GB)) } catch {}
try { $drive = (Get-Item $PSScriptRoot).PSDrive; Write-Host ('Disk  : {0:N1} GiB free on {1}: (campaign requires >= 50 GiB)' -f ($drive.Free / 1GB), $drive.Name) } catch {}
Write-Host ('Java  : ' + ($javaVersion -split "`r?`n")[0] + '  [' + $JavaPath + ']')
Write-Host ('Python: ' + $pyVersion + '  [' + $PythonPath + ']')
Write-Host ('Bundle: ' + $PSScriptRoot)
Write-Host ('Log   : ' + $transcript)
Write-Host ''

# ---------------------------------------------------------------- stages
$stagesFor = @{
    'legacy_fidelity_published' = @('stage1','stage2','collect')
    'legacy_fidelity_fork' = @('stage1','stage2','collect')
    'rq3'             = @('stage1','stage2','collect')
    'rq4_controlled'  = @('stage1','collect')        # structural only, no repetitions
    'rq4_independent' = @('stage1','stage2','collect')
    'rq4_travel'      = @('stage1','stage2','collect')
    'rq4_hub'         = @('stage1','stage2','collect')
}

function Invoke-Stage([string]$Campaign, [string]$Stage) {
    $rawPath = Join-Path $PSScriptRoot ('raw\' + $Campaign)
    New-Item -ItemType Directory -Force -Path $rawPath | Out-Null
    $logPath = Join-Path $rawPath ('launcher-' + $Stage + '-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')
    $script = Join-Path $PSScriptRoot 'scripts\campaign.py'
    # ForEach-Object { "$_" } turns stderr ErrorRecords into plain text before Tee-Object;
    # Out-Host keeps the console output out of the function's return value.
    & $PythonPath -u $script --config $Campaign --stage $Stage 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $logPath | Out-Host
    return [int]$LASTEXITCODE
}

$results = @()
foreach ($campaign in $Campaigns) {
    if (-not $stagesFor.ContainsKey($campaign)) { Write-Warning ('Unknown campaign skipped: ' + $campaign); continue }
    $stages = $stagesFor[$campaign]
    if ($Stage1Only) { $stages = @('stage1','collect') }
    foreach ($stage in $stages) {
        $t0 = Get-Date
        Write-Host ('=== ' + $campaign + ' / ' + $stage + ' started ' + $t0.ToString('yyyy-MM-dd HH:mm:ss') + ' ===') -ForegroundColor Cyan
        $code = 1
        try { $code = Invoke-Stage $campaign $stage } catch { Write-Warning $_.Exception.Message; $code = 1 }
        $minutes = [math]::Round(((Get-Date) - $t0).TotalMinutes, 1)
        $ok = ($code -eq 0)
        $results += [pscustomobject]@{ campaign = $campaign; stage = $stage; ok = $ok; exit_code = $code; minutes = $minutes }
        if ($ok) {
            Write-Host ('=== ' + $campaign + ' / ' + $stage + ' OK after ' + $minutes + ' min ===') -ForegroundColor Green
        } else {
            Write-Host ('=== ' + $campaign + ' / ' + $stage + ' FAILED (exit ' + $code + ') after ' + $minutes + ' min. Raw outputs preserved; remaining stages of this campaign skipped. Re-run this script to resume. ===') -ForegroundColor Yellow
            break
        }
    }
}

Write-Host ''
if ($Campaigns -contains 'legacy_fidelity_published' -or $Campaigns -contains 'legacy_fidelity_fork') {
    & $PythonPath (Join-Path $PSScriptRoot 'scripts\collect_legacy_fidelity.py') --root $PSScriptRoot
    if ($LASTEXITCODE -ne 0) { Fail 'Legacy fidelity comparison collection failed; raw preserved.' }
}
Write-Host '=== Summary ==='
$results | Format-Table -AutoSize | Out-String -Width 160 | ForEach-Object { Write-Host $_ }
Write-Host 'Next: zip the whole raw\ folder and copy it back to the Mac (see XEON_RUNBOOK_JA.md).'
try { Stop-Transcript | Out-Null } catch {}
Pop-Location
if ($results | Where-Object { -not $_.ok }) { exit 1 } else { exit 0 }
