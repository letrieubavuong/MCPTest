ï»¿#requires -Version 5.1
param([string]$PythonPath)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'python-runtime.ps1')
$python = Get-StudioPython -Root $root -RequestedPath $PythonPath
Push-Location -LiteralPath $root
try {
    & $python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed; build stopped.' }
    & $python -m PyInstaller --noconfirm --clean --onedir --console --name LaTeXQuestionStudio --paths src --distpath dist --workpath .runtime/pyinstaller --specpath .runtime/pyinstaller src/latex_question_studio/__main__.py
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed.' }
    & $python -m pip download --no-deps --no-cache-dir --dest .runtime/wheels PyInstaller==6.21.0
    if ($LASTEXITCODE -ne 0) { throw 'Bootloader wheel download failed.' }
    & $python scripts/finalize_windows_build.py
    if ($LASTEXITCODE -ne 0) { throw 'Build finalization failed.' }
    & (Join-Path $root 'dist/LaTeXQuestionStudio/LaTeXQuestionStudio.exe') --smoke-test --data-dir (Join-Path $root '.runtime/build-smoke')
    if ($LASTEXITCODE -ne 0) { throw 'Packaged application smoke test failed.' }
} finally { Pop-Location }
