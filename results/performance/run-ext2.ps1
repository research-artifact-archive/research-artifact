<#
.SYNOPSIS
  Run the optional sixth single-trial extended-budget campaign (Legacy at 200 GiB, 3,600 s):
  ext6_legacy_heap200 = the 18 Legacy (DUCS-path) conditions unresolved at 64 GiB (13 OOM, 5 CRASH).
  Serial and resumable; host checks, keep-awake and transcripts are managed by run-all.ps1.
  Do not run concurrently with run-abl.ps1 or any other Java process.
#>
param(
    [string]$Python = 'python',
    [string]$Java = 'java',
    [switch]$SkipHostCheck
)
Set-StrictMode -Version Latest
$campaigns = @('ext6_legacy_heap200')
& (Join-Path $PSScriptRoot 'run-all.ps1') -Campaigns $campaigns -Python $Python -Java $Java -SkipHostCheck:$SkipHostCheck
exit $LASTEXITCODE
