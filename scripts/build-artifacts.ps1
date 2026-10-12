#requires -Version 5.1

function Assert-StudioArtifactPath {
    param([string]$Root, [string]$Path)
    $artifactRoot = [IO.Path]::GetFullPath($Root).TrimEnd('\')
    $artifactPath = [IO.Path]::GetFullPath($Path).TrimEnd('\')
    $allowed = $false
    foreach ($area in @('dist', 'release', '.runtime')) {
        $prefix = (Join-Path $artifactRoot $area) + '\'
        if ($artifactPath.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) { $allowed = $true }
    }
    if (-not $allowed) { throw "Refusing to remove outside generated artifact folders: $artifactPath" }
    $ancestor = $artifactPath
    while ($ancestor.Length -ge $artifactRoot.Length) {
        if (Test-Path -LiteralPath $ancestor) {
            $item = Get-Item -LiteralPath $ancestor -Force
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Refusing linked artifact path: $ancestor" }
        }
        if ($ancestor -eq $artifactRoot) { break }
        $ancestor = Split-Path -Parent $ancestor
    }
    return $artifactPath
}

function Get-StudioArtifactTree {
    param([string]$Root, [string]$Path, [switch]$UnlinkChildren)
    $artifactPath = Assert-StudioArtifactPath -Root $Root -Path $Path
    if (-not (Test-Path -LiteralPath $artifactPath)) { return }
    $pending = New-Object 'System.Collections.Generic.Stack[string]'
    $pending.Push($artifactPath)
    while ($pending.Count) {
        $item = Get-Item -LiteralPath $pending.Pop() -Force
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            if (-not $UnlinkChildren) { throw "Refusing linked artifact: $($item.FullName)" }
            $item
            continue
        }
        $item
        if ($item.PSIsContainer) {
            foreach ($child in Get-ChildItem -LiteralPath $item.FullName -Force) { $pending.Push($child.FullName) }
        }
    }
}

function Remove-StudioBuildArtifact {
    param([string]$Root, [string]$Path, [switch]$DryRun, [switch]$UnlinkChildren)
    $artifactPath = Assert-StudioArtifactPath -Root $Root -Path $Path
    $items = @(Get-StudioArtifactTree -Root $Root -Path $artifactPath -UnlinkChildren:$UnlinkChildren)
    if (-not $items.Count) { return }
    $bytes = ($items | Where-Object { -not $_.PSIsContainer } | Measure-Object Length -Sum).Sum
    if (-not $DryRun) {
        foreach ($link in $items | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }) {
            if ($link.PSIsContainer) { [IO.Directory]::Delete($link.FullName) } else { [IO.File]::Delete($link.FullName) }
        }
        Remove-Item -LiteralPath $artifactPath -Recurse -Force -ErrorAction Stop
    }
    [PSCustomObject]@{ Path = $artifactPath; Bytes = [long]$bytes; Deleted = -not $DryRun }
}

function Move-StudioBuildArtifact {
    param([string]$Root, [string]$Source, [string]$Destination)
    $sourcePath = Assert-StudioArtifactPath -Root $Root -Path $Source
    $destinationPath = Assert-StudioArtifactPath -Root $Root -Path $Destination
    if (Test-Path -LiteralPath $destinationPath) { throw "Artifact destination already exists: $destinationPath" }
    $item = Get-Item -LiteralPath $sourcePath -Force
    $tree = @(Get-StudioArtifactTree -Root $Root -Path $sourcePath -UnlinkChildren)
    foreach ($entry in $tree) {
        $attributes = $entry.Attributes -band (-bnot [IO.FileAttributes]::ReadOnly) -band (-bnot [IO.FileAttributes]::System)
        if ($entry.Attributes -ne $attributes) { $entry.Attributes = $attributes }
    }
    $parent = Get-Item -LiteralPath (Split-Path -Parent $destinationPath) -Force
    if ($parent.Attributes -band [IO.FileAttributes]::ReadOnly) { $parent.Attributes = $parent.Attributes -band (-bnot [IO.FileAttributes]::ReadOnly) }
    # Rename on the same volume; never fall back to copying part of a tree.
    Move-Item -LiteralPath $sourcePath -Destination $destinationPath -Force -ErrorAction Stop
}

function Publish-StudioBuildArtifacts {
    param([string]$Root, [object[]]$Promotions)
    foreach ($promotion in $Promotions) {
        foreach ($path in @($promotion.Source,$promotion.Target,$promotion.Backup)) { Assert-StudioArtifactPath -Root $Root -Path $path | Out-Null }
        if (-not (Test-Path -LiteralPath $promotion.Source)) { throw 'Missing candidate artifact' }
        if (Test-Path -LiteralPath $promotion.Backup) { throw 'Backup destination already exists' }
    }
    $journal = New-Object System.Collections.ArrayList
    try {
        foreach ($promotion in $Promotions) {
            $entry = @{ Promotion = $promotion; OldMoved = $false; NewMoved = $false }
            $journal.Add($entry) | Out-Null
            if (Test-Path -LiteralPath $promotion.Target) {
                Move-StudioBuildArtifact -Root $Root -Source $promotion.Target -Destination $promotion.Backup
                $entry.OldMoved = $true
            }
            Move-StudioBuildArtifact -Root $Root -Source $promotion.Source -Destination $promotion.Target
            $entry.NewMoved = $true
        }
    } catch {
        for ($index = $journal.Count - 1; $index -ge 0; $index--) {
            $entry = $journal[$index];$promotion = $entry.Promotion
            if ($entry.NewMoved) { Remove-StudioBuildArtifact -Root $Root -Path $promotion.Target | Out-Null }
            if ($entry.OldMoved) { Move-StudioBuildArtifact -Root $Root -Source $promotion.Backup -Destination $promotion.Target }
        }
        throw
    }
}

function Clear-StudioBuildArtifacts {
    param([string]$Root, [string]$Version, [string[]]$KeepPaths = @(), [switch]$DryRun)
    if ($Version -notmatch '^\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?$') { throw 'Invalid build version' }
    $artifactRoot = [IO.Path]::GetFullPath($Root).TrimEnd('\')
    $candidates = @()
    $dist = Join-Path $artifactRoot 'dist'
    if (Test-Path -LiteralPath $dist) {
        $candidates += Get-ChildItem -LiteralPath $dist -Force | Where-Object {
            ($_.Name -match '^\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?$' -and $_.Name -ne $Version) -or $_.Name -eq 'LaTeXQuestionStudio'
        }
    }
    $release = Join-Path $artifactRoot 'release'
    if (Test-Path -LiteralPath $release) {
        $current = "LaTeXQuestionStudio-$Version-win64.zip"
        $candidates += Get-ChildItem -LiteralPath $release -Force | Where-Object {
            $_.Name -like 'LaTeXQuestionStudio-*' -and $_.Name -ne $current -and $_.Name -ne "$current.sha256"
        }
    }
    $runtime = Join-Path $artifactRoot '.runtime'
    if (Test-Path -LiteralPath $runtime) {
        $candidates += Get-ChildItem -LiteralPath $runtime -Force | Where-Object {
            $_.Name -match '^(bundle-before-|pyinstaller-before-|pyinstaller-retry-|ui-zip-|ui-smoke-|pytest-|build-stage-|formula-bundle-|wysiwyg-bundle-|windowed-render-)'
        }
    }
    $kept = @($KeepPaths | ForEach-Object { [IO.Path]::GetFullPath($_).TrimEnd('\') })
    $candidates = @($candidates | Where-Object { $_.FullName.TrimEnd('\') -notin $kept })
    # Validate the entire selection before deleting any directory.
    foreach ($candidate in $candidates) {
        $unlink = $candidate.Name -match '^(pytest-|build-stage-)'
        $items = @(Get-StudioArtifactTree -Root $artifactRoot -Path $candidate.FullName -UnlinkChildren:$unlink)
        if ($candidate.FullName.StartsWith($dist + '\') -or $candidate.Name -like 'bundle-before-*') {
            if ($items | Where-Object { -not $_.PSIsContainer -and $_.Extension -in @('.db','.sqlite','.sqlite3') }) {
                throw "Preserving a bundle containing a database: $($candidate.FullName)"
            }
        }
    }
    foreach ($candidate in $candidates) {
        $unlink = $candidate.Name -match '^(pytest-|build-stage-)'
        Remove-StudioBuildArtifact -Root $artifactRoot -Path $candidate.FullName -DryRun:$DryRun -UnlinkChildren:$unlink
    }
}
