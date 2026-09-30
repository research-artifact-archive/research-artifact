param(
    [ValidateSet('rq3','rq4_independent','rq4_travel','rq4_hub','rq4_controlled')]
    [string]$Campaign = 'rq3',
    [ValidateSet('plan','stage1','stage2','collect')]
    [string]$Stage = 'stage1',
    [string]$Python = 'python',
    [string]$Java = 'java'
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
Push-Location $PSScriptRoot
try {
    # Resolve executable paths before changing PATH; all model/JAR paths are bundle-relative.
    $PythonPath = (Get-Command $Python -ErrorAction Stop).Source
    $JavaPath = (Get-Command $Java -ErrorAction Stop).Source
    $env:PATH = (Split-Path -Parent $JavaPath) + ';' + $env:PATH
    $env:PYTHONUTF8 = '1'
    if ($Stage -ne 'plan' -and $Stage -ne 'collect') {
        $CPUName = (Get-CimInstance Win32_Processor | Select-Object -First 1).Name
        if ($CPUName -notmatch 'W-2265') { throw "Expected the fixed Xeon W-2265 host; found: $CPUName" }
    }
    $RawPath = Join-Path $PSScriptRoot ('raw\' + $Campaign)
    New-Item -ItemType Directory -Force -Path $RawPath | Out-Null
    $LogPath = Join-Path $RawPath ('launcher-' + $Stage + '-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')
    # Match run-all.ps1: native stderr is logged as text, and the native exit
    # code determines success. Windows PowerShell 5.1 would otherwise promote
    # redirected stderr to a terminating error under ErrorActionPreference=Stop.
    $PreviousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & $PythonPath -u (Join-Path $PSScriptRoot 'scripts\campaign.py') --config $Campaign --stage $Stage 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $LogPath -ErrorAction Stop | Out-Host
        $CampaignExitCode = [int]$LASTEXITCODE
    }
    finally { $ErrorActionPreference = $PreviousErrorActionPreference }
    if ($CampaignExitCode -ne 0) { throw "Campaign exited with code $CampaignExitCode. Preserve raw outputs; no failed cell is retried." }
}
finally { Pop-Location }
