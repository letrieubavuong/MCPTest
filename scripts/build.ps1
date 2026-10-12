#requires -Version 5.1
param([string]$PythonPath, [switch]$PackageRelease)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'python-runtime.ps1')
. (Join-Path $PSScriptRoot 'build-artifacts.ps1')
$previewData = Join-Path $root 'src/latex_question_studio/preview/data'
Copy-Item -LiteralPath (Join-Path $root 'docs/Class/MAPClass.cls') -Destination (Join-Path $previewData 'Class/MAPClass.cls') -Force
Copy-Item -LiteralPath (Join-Path $root 'docs/Packages/ex_test.sty') -Destination (Join-Path $previewData 'Packages/ex_test.sty') -Force
$catalogData = Join-Path $root 'src/latex_question_studio/domain/data'
$iconData = Join-Path $root 'src/latex_question_studio/ui/assets'
$python = Get-StudioPython -Root $root -RequestedPath $PythonPath
$previousConfigDirectory = $env:PYINSTALLER_CONFIG_DIR
$env:PYINSTALLER_CONFIG_DIR = Join-Path $root '.runtime/pyinstaller-cache'
Push-Location -LiteralPath $root
$stage = $null
$buildVerified = $false
try {
    $version = & $python -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])"
    if ($LASTEXITCODE -ne 0) { throw 'Unable to read project version.' }
    if ($version -notmatch '^\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?$') { throw 'Invalid build version' }
    $stage = Join-Path $root ('.runtime/build-stage-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $stage | Out-Null
    $distPath = Join-Path $stage 'dist'
    $workPath = Join-Path $stage 'work'
    $bundle = Join-Path $distPath 'LaTeXQuestionStudio'
    $pyz = Join-Path $workPath 'LaTeXQuestionStudio/PYZ-00.pyz'
    $testXml = Join-Path $stage 'tests.xml'
    & $python scripts/generate_app_icon.py
    if ($LASTEXITCODE -ne 0) { throw 'Icon generation failed.' }
    & $python -m pytest -q --junitxml $testXml --basetemp (Join-Path $stage 'tests')
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed; build stopped.' }
    [xml]$testResults = Get-Content -LiteralPath $testXml -Raw -Encoding UTF8
    $testCount = 0
    foreach ($suite in $testResults.testsuites.testsuite) { $testCount += [int]$suite.tests - [int]$suite.skipped }
    & $python -m PyInstaller --noconfirm --clean --onedir --windowed --icon (Join-Path $iconData 'mcptest.ico') --name LaTeXQuestionStudio --paths src --add-data "$catalogData;latex_question_studio/domain/data" --add-data "$previewData;latex_question_studio/preview/data" --add-data "$iconData;latex_question_studio/ui/assets" --collect-all pymupdf --copy-metadata PyMuPDF --distpath $distPath --workpath $workPath --specpath $workPath src/latex_question_studio/__main__.py
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed.' }
    & $python scripts/verify_ui_package.py --dist-dir $bundle --pyz $pyz --output-dir artifacts/build-current
    if ($LASTEXITCODE -ne 0) { throw 'Packaged application smoke test failed.' }
    if ($PackageRelease) {
        $releaseStage = Join-Path $stage 'release'
        & $python scripts/package_release.py --dist-dir $bundle --output-dir $releaseStage --test-count $testCount
        if ($LASTEXITCODE -ne 0) { throw 'Release packaging failed.' }
        $zipName = "LaTeXQuestionStudio-$version-win64.zip"
        & $python scripts/verify_ui_package.py --zip (Join-Path $releaseStage $zipName) --pyz $pyz --output-dir artifacts/build-current
        if ($LASTEXITCODE -ne 0) { throw 'Release ZIP smoke test failed.' }
    }
    $buildVerified = $true
    Copy-Item -LiteralPath $testXml -Destination (Join-Path $root 'artifacts/build-current/tests.xml') -Force
    foreach ($appProcess in Get-Process LaTeXQuestionStudio -ErrorAction SilentlyContinue) {
        if ($appProcess.Path -and $appProcess.Path.StartsWith($root + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Close the running application before replacing this build.' }
    }
    $destDist = Join-Path $root "dist/$version"
    $destWork = Join-Path $root '.runtime/pyinstaller'
    $releaseRoot = Join-Path $root 'release'
    New-Item -ItemType Directory -Path (Join-Path $root 'dist') -Force | Out-Null
    $promotions = @(
        @{ Source = $distPath; Target = $destDist; Backup = (Join-Path $stage 'previous-dist') },
        @{ Source = $workPath; Target = $destWork; Backup = (Join-Path $stage 'previous-work') }
    )
    if ($PackageRelease) {
        New-Item -ItemType Directory -Path $releaseRoot -Force | Out-Null
        $promotions += @(
            @{ Source = (Join-Path $releaseStage $zipName); Target = (Join-Path $releaseRoot $zipName); Backup = (Join-Path $stage 'previous.zip') },
            @{ Source = (Join-Path $releaseStage "$zipName.sha256"); Target = (Join-Path $releaseRoot "$zipName.sha256"); Backup = (Join-Path $stage 'previous.zip.sha256') }
        )
    }
    if (Test-Path -LiteralPath $destDist) {
        $oldFiles = @(Get-StudioArtifactTree -Root $root -Path $destDist)
        if ($oldFiles | Where-Object { -not $_.PSIsContainer -and $_.Extension -in @('.db','.sqlite','.sqlite3') }) { throw 'Preserving a build containing a database. Move application data out of dist first.' }
    }
    Publish-StudioBuildArtifacts -Root $root -Promotions $promotions
    $reportPath = Join-Path $root 'artifacts/build-current'
    Copy-Item -LiteralPath $testXml -Destination (Join-Path $reportPath 'tests.xml') -Force
    $cleanup = @(Clear-StudioBuildArtifacts -Root $root -Version $version -KeepPaths @($stage))
    $cleanup += Remove-StudioBuildArtifact -Root $root -Path $stage -UnlinkChildren
    $cleanup | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $reportPath 'cleanup.json') -Encoding UTF8
    $freed = ($cleanup | Measure-Object Bytes -Sum).Sum
    Write-Host ("Build ready: {0}; {1} tests passed; removed {2:N1} MiB of old build files." -f $version,$testCount,($freed / 1MB))
} finally {
    if ($stage -and (Test-Path -LiteralPath $stage)) {
        $unrestored = @(Get-ChildItem -LiteralPath $stage -Force | Where-Object { $_.Name -like 'previous-*' -or $_.Name -like 'previous.zip*' })
        if ($unrestored.Count) { Write-Warning "Preserved backup artifacts after an incomplete publish: $stage" }
        elseif ($buildVerified) { Write-Warning "Preserved verified build for publishing after the application closes: $stage" }
        else { Remove-StudioBuildArtifact -Root $root -Path $stage -UnlinkChildren | Out-Null }
    }
    Pop-Location
    $env:PYINSTALLER_CONFIG_DIR = $previousConfigDirectory
}
