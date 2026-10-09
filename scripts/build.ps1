#requires -Version 5.1
param([string]$PythonPath)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'python-runtime.ps1')
$previewData = Join-Path $root 'src/latex_question_studio/preview/data'
Copy-Item -LiteralPath (Join-Path $root 'docs/Class/MAPClass.cls') -Destination (Join-Path $previewData 'Class/MAPClass.cls') -Force
Copy-Item -LiteralPath (Join-Path $root 'docs/Packages/ex_test.sty') -Destination (Join-Path $previewData 'Packages/ex_test.sty') -Force
$catalogData = Join-Path $root 'src/latex_question_studio/domain/data'
$python = Get-StudioPython -Root $root -RequestedPath $PythonPath
Push-Location -LiteralPath $root
try {
    & $python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed; build stopped.' }
    & $python -m PyInstaller --noconfirm --clean --onedir --console --name LaTeXQuestionStudio --paths src --add-data "$catalogData;latex_question_studio/domain/data" --add-data "$previewData;latex_question_studio/preview/data" --distpath dist/0.5.2 --workpath .runtime/pyinstaller --specpath .runtime/pyinstaller src/latex_question_studio/__main__.py
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed.' }
    if (-not (Test-Path -LiteralPath (Join-Path $root '.runtime/wheels/pyinstaller-6.21.0-py3-none-win_amd64.whl'))) {
        & $python -m pip download --no-deps --no-cache-dir --dest .runtime/wheels PyInstaller==6.21.0
        if ($LASTEXITCODE -ne 0) { throw 'Bootloader wheel download failed.' }
    }
    & $python scripts/finalize_windows_build.py --dist-dir dist/0.5.2/LaTeXQuestionStudio
    if ($LASTEXITCODE -ne 0) { throw 'Build finalization failed.' }
    & (Join-Path $root 'dist/0.5.2/LaTeXQuestionStudio/LaTeXQuestionStudio.exe') --smoke-test --data-dir (Join-Path $root '.runtime/build-smoke')
    if ($LASTEXITCODE -ne 0) { throw 'Packaged application smoke test failed.' }
} finally { Pop-Location }
