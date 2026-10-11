#requires -Version 5.1
param([switch]$DryRun)
$ErrorActionPreference = 'Stop'
$cleanupRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'python-runtime.ps1')
. (Join-Path $PSScriptRoot 'build-artifacts.ps1')
$cleanupPython = Get-StudioPython -Root $cleanupRoot
$cleanupVersion = & $cleanupPython -c "import sys,tomllib; print(tomllib.load(open(sys.argv[1], 'rb'))['project']['version'])" (Join-Path $cleanupRoot 'pyproject.toml')
if ($LASTEXITCODE -ne 0) { throw 'Unable to read version' }
Clear-StudioBuildArtifacts -Root $cleanupRoot -Version $cleanupVersion -DryRun:$DryRun | ConvertTo-Json -Depth 4
