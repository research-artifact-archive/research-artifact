<#
.SYNOPSIS
  PC2-Rolling (E6 application-plant witness) on the Xeon: rerun the two cells that timed out on the Mac at 1,200 s/32g
  with a 200 GiB heap and a 7,200 s whole-JVM limit, plus the fine cell for same-host reference. One trial per cell, serial,
  resumable (a cell with completion.json is skipped). Uses the read-only E1 JAR and the frozen Pc2DiagnosticRunner class.
  Do not run concurrently with run-all.ps1 / run-ext*.ps1 / run-abl.ps1 or any other Java process.
#>
param(
    [string]$Java = 'java',
    [string]$Heap = '200g',
    [int]$TimeoutSeconds = 7200,
    [string[]]$Cells = @('lazy_transfers','direct_full_none','lazy_none'),
    [switch]$DryRun
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$jar = Join-Path $root 'ablation_20260928\jars\e1.jar'
$classes = Join-Path $root 'pc2_rolling_xeon\classes'
$lts = Join-Path $root 'pc2_rolling_xeon\inputs\ProductionCell_Arms2_Calibration.lts'
$rawRoot = Join-Path $root 'pc2_rolling_xeon\raw'
$expectedJar = 'FF1E6B176F004EA85F1E99690A90388A6A4D24F44CD8D8E636FCD9337DCF67D5'
$expectedLts = 'EF731FF57935D5A880FB23CDEF264C034378BF4954C1345D6B2FB5431C866A86'
foreach ($f in @($jar, $lts, (Join-Path $classes 'ltsa\updatingControllers\cli\Pc2DiagnosticRunner.class'))) {
    if (-not (Test-Path $f)) { throw ('Missing file: ' + $f) }
}
if ((Get-FileHash $jar -Algorithm SHA256).Hash -ne $expectedJar) { throw 'E1 JAR SHA-256 mismatch; refusing to run.' }
if ((Get-FileHash $lts -Algorithm SHA256).Hash -ne $expectedLts) { throw 'PC2-Rolling LTS SHA-256 mismatch; refusing to run.' }
$JavaPath = (Get-Command $Java -ErrorAction Stop).Source
$specs = @{
    'lazy_transfers'   = @{ solver = 'otf';         merge = 'transfers'; lazy = 'true'  }
    'direct_full_none' = @{ solver = 'direct_full'; merge = 'none';      lazy = 'false' }
    'lazy_none'        = @{ solver = 'otf';         merge = 'none';      lazy = 'true'  }
}
New-Item -ItemType Directory -Force -Path $rawRoot | Out-Null
$ErrorActionPreference = 'Continue'
$javaVersion = (& $JavaPath -version 2>&1 | Out-String)
$ErrorActionPreference = 'Stop'
if ($javaVersion -notmatch 'version "17\.') { throw 'JDK 17 is required.' }
if (-not $DryRun) {
    $active = @(Get-Process -Name java -ErrorAction SilentlyContinue)
    if ($active.Count -gt 0) { throw 'A Java process is already running; wait for the other campaign to finish.' }
    $mem = (Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory
    if ($mem / 1GB -lt 240) { throw 'At least 240 GiB physical memory is required for a 200 GiB heap.' }
    Add-Type -Namespace FgDucsPc2 -Name Power -MemberDefinition @'
[System.Runtime.InteropServices.DllImport("kernel32.dll", SetLastError = true)]
public static extern uint SetThreadExecutionState(uint esFlags);
'@
    [void][FgDucsPc2.Power]::SetThreadExecutionState([uint32]2147483649)
}
@{ java_version = $javaVersion.Trim(); heap = $Heap; timeout_seconds = $TimeoutSeconds; captured = (Get-Date).ToString('o');
   cpu = (Get-CimInstance Win32_Processor | Select-Object -First 1).Name; jar_sha256 = $expectedJar; lts_sha256 = $expectedLts } |
   ConvertTo-Json | Set-Content -Path (Join-Path $rawRoot 'environment.json') -Encoding UTF8
try {
    foreach ($cell in $Cells) {
        if (-not $specs.ContainsKey($cell)) { Write-Warning ('Unknown cell skipped: ' + $cell); continue }
        $spec = $specs[$cell]
        $dir = Join-Path $rawRoot $cell
        if (Test-Path (Join-Path $dir 'completion.json')) { Write-Host ('[skip] ' + $cell + ' already has completion.json'); continue }
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
        $jvmArgs = @("-Xmx$Heap", '-Djava.awt.headless=true',
            ('-Dmtsa.revised.otf.solver=' + $spec.solver), ('-Dmtsa.otf.contractMerge=' + $spec.merge),
            ('-Dmtsa.otf.lazyControllableBuckets=' + $spec.lazy), '-Dmtsa.otf.guidedStateLimit=0', '-Dmtsa.otf.guidedQueryLimit=0',
            '-Dmtsa.otf.controllableActionOrder=endpoint_guided', '-cp', ($classes + ';' + $jar),
            'ltsa.updatingControllers.cli.Pc2DiagnosticRunner', '--lts', $lts, '--target', 'UPDATE_CONTROLLER_PC2_CAL',
            '--output', (Join-Path $dir 'output.txt'), '--transitions', (Join-Path $dir 'transitions.txt'), '--transition-output', 'summary',
            '--diagnostic-output', (Join-Path $dir 'certificate_summary.json'))
        @{ at = (Get-Date).ToString('o'); cell = $cell; heap = $Heap; timeout_seconds = $TimeoutSeconds; timeout_scope = 'whole JVM';
           solver = $spec.solver; merge = $spec.merge; input_sha256 = $expectedLts; jar_sha256 = $expectedJar; host = 'xeon';
           command = (@($JavaPath) + $jvmArgs) } | ConvertTo-Json -Depth 4 | Set-Content -Path (Join-Path $dir 'invocation.json') -Encoding UTF8
        Write-Host ('=== ' + $cell + ' started ' + (Get-Date).ToString('yyyy-MM-dd HH:mm:ss') + ' (' + $Heap + ', ' + $TimeoutSeconds + ' s) ===') -ForegroundColor Cyan
        if ($DryRun) { Write-Host ('  ' + ($jvmArgs -join ' ')); continue }
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        $p = Start-Process -FilePath $JavaPath -ArgumentList $jvmArgs -RedirectStandardOutput (Join-Path $dir 'stdout.log') `
             -RedirectStandardError (Join-Path $dir 'stderr.log') -PassThru -NoNewWindow
        $peak = [int64]0; $timedOut = $false
        while (-not $p.HasExited) {
            try { $p.Refresh(); if ($p.WorkingSet64 -gt $peak) { $peak = $p.WorkingSet64 } } catch {}
            if ($sw.Elapsed.TotalSeconds -gt $TimeoutSeconds) { $timedOut = $true; try { Stop-Process -Id $p.Id -Force } catch {}; break }
            Start-Sleep -Milliseconds 500
        }
        $p.WaitForExit()
        $sw.Stop()
        $exit = $p.ExitCode
        @{ at = (Get-Date).ToString('o'); cell = $cell; exit_code = $exit; timed_out = $timedOut; wall_seconds = [math]::Round($sw.Elapsed.TotalSeconds, 3);
           peak_rss_bytes = $peak; peak_rss_gib = [math]::Round($peak / 1GB, 2); heap = $Heap; timeout_seconds = $TimeoutSeconds } |
           ConvertTo-Json | Set-Content -Path (Join-Path $dir 'completion.json') -Encoding UTF8
        $status = if ($timedOut) { 'TIMEOUT' } else { 'exit ' + $exit }
        Write-Host ('=== ' + $cell + ' finished: ' + $status + ' after ' + [math]::Round($sw.Elapsed.TotalSeconds) + ' s, peak RSS ' + [math]::Round($peak / 1GB, 1) + ' GiB ===') -ForegroundColor Green
    }
} finally {
    if (-not $DryRun) { [void][FgDucsPc2.Power]::SetThreadExecutionState([uint32]2147483648) }
}
Write-Host 'Next: zip pc2_rolling_xeon\raw as xeon-raw-pc2rolling-<ts>.zip and copy it to the Mac (experiments/witness_20260929/e6/pc2_rolling/).'
