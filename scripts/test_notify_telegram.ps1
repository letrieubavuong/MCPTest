#requires -Version 5.1
$ErrorActionPreference = 'Stop'
$scriptPath = Join-Path $PSScriptRoot 'notify-telegram.ps1'
$parseTokens = $parseErrors = $null
[void][Management.Automation.Language.Parser]::ParseFile($scriptPath,[ref]$parseTokens,[ref]$parseErrors)
if ($parseErrors.Count) { throw 'Syntax check failed' }
$testRoot = Join-Path $env:TEMP ('Tikz Telegram test ' + [Guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($testRoot)
$image = Join-Path $testRoot 'ảnh preview có khoảng trắng.png'
$global:tgTestBytes = [Convert]::FromBase64String('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jZ1kAAAAASUVORK5CYII=')
[IO.File]::WriteAllBytes($image,$global:tgTestBytes)
$fakeToken = '123456:TEST_ONLY_NOT_A_REAL_TOKEN'
$encrypted = ConvertFrom-SecureString (ConvertTo-SecureString $fakeToken -AsPlainText -Force)
$global:tgTestConfig = @{Token=$encrypted;ChatId='123'} | ConvertTo-Json
$global:tgTestCaption = 'Ảnh thử tiếng Việt: giao diện — kết quả kiểm tra'
$global:tgTestRequests = 0
$global:tgTestMode = 'text'
function Get-Content { param($LiteralPath,[switch]$Raw,$Encoding) return $global:tgTestConfig }
function Invoke-RestMethod {
    param($Uri,$Method,$Body,$ContentType,$TimeoutSec,$MaximumRedirection,$ErrorAction,[switch]$Verbose,[switch]$Debug)
    $global:tgTestRequests++
    if ($Method -ne 'Post' -or $TimeoutSec -ne 15 -or $MaximumRedirection -ne 0) { throw 'Request options invalid' }
    $decoded = [Text.Encoding]::UTF8.GetString($Body)
    if ($global:tgTestMode -eq 'text') {
        if (-not $Uri.EndsWith('/sendMessage') -or $ContentType -ne 'application/json; charset=utf-8') { throw 'Text request invalid' }
        $payload = $decoded | ConvertFrom-Json
        if ($payload.chat_id -ne '123' -or -not $payload.text.Contains($global:tgTestCaption)) { throw 'Text payload invalid' }
    } else {
        $endpoint = if ($global:tgTestMode -eq 'document') { '/sendDocument' } else { '/sendPhoto' }
        $field = if ($global:tgTestMode -eq 'document') { 'document' } else { 'photo' }
        if (-not $Uri.EndsWith($endpoint) -or $ContentType -notmatch '^multipart/form-data; boundary=(.+)$') { throw 'Upload endpoint invalid' }
        $boundary = $Matches[1]
        if (-not $decoded.Contains('name="' + $field + '"') -or -not $decoded.Contains('name="chat_id"') -or
            -not $decoded.Contains('name="caption"') -or -not $decoded.Contains($global:tgTestCaption) -or
            -not $decoded.Contains('Dự án: Tikz Manager') -or -not $decoded.Contains('Phase: TEST')) { throw 'Multipart fields invalid' }
        $latin = [Text.Encoding]::GetEncoding(28591)
        if (-not $latin.GetString($Body).Contains($latin.GetString($global:tgTestBytes))) { throw 'File bytes corrupted' }
        if (-not $decoded.EndsWith("--$boundary--`r`n") -or $decoded.Contains('Tikz Telegram test')) { throw 'Multipart framing/path privacy invalid' }
    }
    if ($global:tgTestMode -eq 'throw') { throw "Simulated secret error $Uri" }
    return @{ok=($global:tgTestMode -ne 'rejected')}
}
try {
    foreach ($mode in @('text','photo','document','missing','rejected','throw')) {
        $global:tgTestMode = $mode
        $arguments = @{Project='Tikz Manager';Phase='TEST';Status='testing';Summary=$global:tgTestCaption}
        if ($mode -ne 'text') {
            $arguments.ImagePath = if ($mode -eq 'missing') { Join-Path $testRoot 'missing.png' } else { $image }
            $arguments.Caption = $global:tgTestCaption
        }
        if ($mode -eq 'document') { $arguments.AsDocument = $true }
        $output = (& $scriptPath @arguments 3>&1 | Out-String)
        if ($output.Contains($fakeToken) -or $output.Contains($encrypted) -or $output.Contains('api.telegram.org')) { throw 'Secret was logged' }
        if ($mode -in @('text','photo','document')) {
            if ($output -notmatch 'API ok=true') { throw "Expected successful mock delivery: $mode" }
        } elseif ($output -match 'API ok=true' -or $output -notmatch 'not sent') { throw 'Failure was not handled safely' }
    }
    if ($global:tgTestRequests -ne 5) { throw 'Missing file was sent or request count invalid' }
    Write-Output 'PASS: text, photo/document multipart, Unicode/spaced path and caption, exact bytes, timeout, missing file, API rejection, redacted failure and continuation (no real network).'
} finally {
    Remove-Item -LiteralPath $image -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $testRoot -Force -ErrorAction SilentlyContinue
    Remove-Variable tgTestBytes,tgTestConfig,tgTestCaption,tgTestRequests,tgTestMode -Scope Global
}
