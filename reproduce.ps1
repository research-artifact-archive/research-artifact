$ErrorActionPreference = "Stop"
$Mode = if ($args.Count -gt 0) { $args[0] } else { "portable" }
Set-Location $PSScriptRoot
python -I -S -B tools/verify.py $Mode
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
