<#
.SYNOPSIS
  Run the five single-trial extended-budget campaigns serially and resumably.
  To omit the optional final campaign, supply -SkipOptionalExt5.
  Host checks, keep-awake and transcripts are managed by run-all.ps1.
#>
param(
    [string]$Python = 'python',
    [string]$Java = 'java',
    [switch]$SkipHostCheck,
    [switch]$SkipOptionalExt5
)
Set-StrictMode -Version Latest
$campaigns = @('ext1_travel_frontier','ext2_rq3_df_cpu','ext3_travel_next','ext4_rq3_df_heap200')
if (-not $SkipOptionalExt5) { $campaigns += 'ext5_travel_heap200' }
& (Join-Path $PSScriptRoot 'run-all.ps1') -Campaigns $campaigns -Python $Python -Java $Java -SkipHostCheck:$SkipHostCheck
exit $LASTEXITCODE
