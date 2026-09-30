<#
.SYNOPSIS
  Run the optional seventh single-trial extended-budget campaign (Eager at 200 GiB, 7,200 s):
  ext7_eager_heap200 = the 10 application conditions where Eager (OTF + UC pruning, no lazy buckets)
  timed out at the fixed budget. Same JAR, serial, resumable; host checks and transcripts by run-all.ps1.
  Do not run concurrently with run-abl.ps1, run-ext2.ps1 or any other Java process.
#>
param(
    [string]$Python = 'python',
    [string]$Java = 'java',
    [switch]$SkipHostCheck
)
Set-StrictMode -Version Latest
$campaigns = @('ext7_eager_heap200')
& (Join-Path $PSScriptRoot 'run-all.ps1') -Campaigns $campaigns -Python $Python -Java $Java -SkipHostCheck:$SkipHostCheck
exit $LASTEXITCODE
