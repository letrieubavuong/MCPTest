#requires -Version 5.1
param([string]$DataDir, [switch]$SmokeTest, [string]$Screenshot, [string]$PythonPath)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'python-runtime.ps1')
$python = Get-StudioPython -Root $root -RequestedPath $PythonPath
if (-not (Test-Path -LiteralPath $python)) { throw 'Create .venv and install the project first; see README.md.' }
$arguments = @('-m','latex_question_studio')
if ($DataDir) { $arguments += @('--data-dir',$DataDir) }
if ($SmokeTest) { $arguments += '--smoke-test' }
if ($Screenshot) { $arguments += @('--screenshot',$Screenshot) }
& $python @arguments
exit $LASTEXITCODE
