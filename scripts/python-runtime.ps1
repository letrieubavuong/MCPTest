#requires -Version 5.1
function Get-StudioPython {
    param([Parameter(Mandatory=$true)][string]$Root, [string]$RequestedPath)
    $candidates = if ($RequestedPath) { @($RequestedPath) } else {
        @((Join-Path $Root '.venv\Scripts\python.exe'), (Join-Path $Root '.runtime\python-embed\python.exe'))
    }
    foreach ($candidate in $candidates) {
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
        try {
            $probe = @(& $candidate -c "print('LQS_RUNTIME_OK')" 2>$null)
            if ($LASTEXITCODE -eq 0 -and $probe -contains 'LQS_RUNTIME_OK') { return $candidate }
        } catch { continue }
    }
    throw 'No working Python runtime. Create .venv/install dependencies or supply -PythonPath.'
}