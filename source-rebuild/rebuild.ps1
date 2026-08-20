param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$RemainingArgs
)

$ErrorActionPreference = "Stop"
if (-not $env:JAVA_HOME) {
    throw "JAVA_HOME must point to JDK 17."
}
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }
& $Python "$ScriptDir/rebuild.py" --java-home "$env:JAVA_HOME" @RemainingArgs
exit $LASTEXITCODE
