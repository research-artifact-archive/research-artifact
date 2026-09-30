<#
.SYNOPSIS
  Optional E2 timing campaign after ext5 finishes: 27 cells, 64g, 1200 s, one trial.
  Uses a separately identified JAR and writes only ablation_20260928/raw.
#>
param(
    [string]$Python = 'python',
    [string]$Java = 'java',
    [switch]$DryRun
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$PythonPath = (Get-Command $Python -ErrorAction Stop).Source
$JavaPath = (Get-Command $Java -ErrorAction Stop).Source
$env:PATH = (Split-Path -Parent $JavaPath) + ';' + $env:PATH
$env:PYTHONUTF8 = '1'
$runner = Join-Path $PSScriptRoot 'ablation_20260928\scripts\run_ablation.py'
$config = Join-Path $PSScriptRoot 'configs\abl_e2_ucpruned.json'
if (-not (Test-Path $runner)) { throw 'Copy the separate ablation_20260928 folder beside configs first (see XEON_RUNBOOK_ABL_JA.md).' }
if (-not $DryRun) {
    $cpu = (Get-CimInstance Win32_Processor | Select-Object -First 1).Name
    if ($cpu -notmatch 'W-2265') { throw ('Expected Xeon W-2265; found ' + $cpu) }
    $memory = (Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory
    if ($memory / 1GB -lt 240) { throw 'At least 240 GiB physical memory is required on the timing host.' }
    # Windows PowerShell 5.1 treats redirected native stderr as ErrorRecords.
    $ErrorActionPreference = 'Continue'
    $javaVersion = (& $JavaPath -version 2>&1 | Out-String)
    $javaExit = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    if ($javaExit -ne 0) { throw 'Java version probe failed.' }
    if ($javaVersion -notmatch 'version "17\.') { throw 'JDK 17 is required.' }
    # Do not overlap with the pre-existing ext/primary timing campaigns.
    $activeJava = @(Get-Process -Name java -ErrorAction SilentlyContinue)
    if ($activeJava.Count -gt 0) { throw 'A Java process is already running. Run this only after ext5 and all synthesis JVMs finish.' }
}
$raw = Join-Path $PSScriptRoot 'ablation_20260928\raw'
New-Item -ItemType Directory -Force -Path $raw | Out-Null
$log = Join-Path $raw ('e2-xeon-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')
$runnerArgs = @('-u', $runner, '--config', $config, '--root', $PSScriptRoot)
if ($DryRun) { $runnerArgs += '--dry-run' }
try {
    if (-not $DryRun) {
        Add-Type -Namespace FgDucsAblation -Name Power -MemberDefinition @'
[System.Runtime.InteropServices.DllImport("kernel32.dll", SetLastError = true)]
public static extern uint SetThreadExecutionState(uint esFlags);
'@
        [void][FgDucsAblation.Power]::SetThreadExecutionState([uint32]2147483649)
    }
    $ErrorActionPreference = 'Continue'
    & $PythonPath @runnerArgs 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $log | Out-Host
    $result = $LASTEXITCODE
} finally {
    if (-not $DryRun) { [void][FgDucsAblation.Power]::SetThreadExecutionState([uint32]2147483648) }
}
exit $result
