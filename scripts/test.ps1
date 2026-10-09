#requires -Version 5.1
param([string]$PythonPath)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'python-runtime.ps1')
$python = Get-StudioPython -Root $root -RequestedPath $PythonPath
Push-Location -LiteralPath $root
try { & $python -m pytest -q; $result = $LASTEXITCODE } finally { Pop-Location }
exit $result
