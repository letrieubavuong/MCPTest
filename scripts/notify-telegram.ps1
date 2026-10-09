#requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$Project,
    [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$Phase,
    [Parameter(Mandatory = $true)]
    [ValidateSet('started', 'testing', 'completed', 'failed', 'blocked')][string]$Status,
    [string]$Summary = '',
    [string]$ImagePath,
    [string]$Caption,
    [switch]$AsDocument
)

# Best effort. Never log exception details, request URIs, config or credentials.
# Review images/captions before calling; this script cannot detect all private data.
$ErrorActionPreference = 'Stop'
$VerbosePreference = 'SilentlyContinue'
$DebugPreference = 'SilentlyContinue'
$config = $secureToken = $token = $uri = $response = $body = $fileBytes = $null
$multipart = $null
$tokenPointer = [IntPtr]::Zero
$failureStage = 'input validation'
$method = 'sendMessage'
try {
    if ($AsDocument -and [string]::IsNullOrWhiteSpace($ImagePath)) {
        throw 'Document mode requires an image'
    }
    if (-not [string]::IsNullOrWhiteSpace($ImagePath)) {
        $failureStage = 'image validation'
        if (-not (Test-Path -LiteralPath $ImagePath -PathType Leaf)) { throw 'Image missing' }
        $file = Get-Item -LiteralPath $ImagePath
        if ($file.PSProvider.Name -ne 'FileSystem') { throw 'Not a filesystem image' }
        $extension = $file.Extension.ToLowerInvariant()
        if ($extension -notin @('.png','.jpg','.jpeg','.webp','.gif','.bmp','.tif','.tiff','.svg')) {
            throw 'Unsupported image extension'
        }
        $limit = if ($AsDocument) { 50MB } else { 10MB }
        if ($file.Length -le 0 -or $file.Length -gt $limit) { throw 'Invalid image size' }
        $method = if ($AsDocument) { 'sendDocument' } else { 'sendPhoto' }
        $field = if ($AsDocument) { 'document' } else { 'photo' }
        $content = if ([string]::IsNullOrWhiteSpace($Caption)) { $Summary } else { $Caption }
        if ([string]::IsNullOrWhiteSpace($content)) { throw 'Image caption required' }
        $message = "Dự án: $Project`nPhase: $Phase`nTrạng thái: $Status`n$content"
        if ($message.Length -gt 1024) { throw 'Caption too long' }
        $fileBytes = [IO.File]::ReadAllBytes($file.FullName)
        if ($fileBytes.Length -gt $limit) { throw 'Image size changed' }
    } else {
        if ([string]::IsNullOrWhiteSpace($Summary)) { throw 'Text summary required' }
        $message = "Project: $Project`nPhase: $Phase`nStatus: $Status`nSummary: $Summary"
        if ($message.Length -gt 4096) { throw 'Message too long' }
    }

    $failureStage = 'configuration'
    $configPath = Join-Path $env:LOCALAPPDATA 'CodexTelegram\config.json'
    $config = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ([string]::IsNullOrWhiteSpace([string]$config.Token) -or
        [string]::IsNullOrWhiteSpace([string]$config.ChatId)) { throw 'Invalid configuration' }
    $failureStage = 'DPAPI decryption'
    $secureToken = ConvertTo-SecureString -String ([string]$config.Token)
    $tokenPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureToken)
    $token = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($tokenPointer)
    if ($token -notmatch '^\d+:[A-Za-z0-9_-]+$') { throw 'Invalid token' }

    if ($method -eq 'sendMessage') {
        $body = [Text.Encoding]::UTF8.GetBytes((@{chat_id=[string]$config.ChatId; text=$message} | ConvertTo-Json -Compress))
        $contentType = 'application/json; charset=utf-8'
    } else {
        # Build byte-accurate multipart for Windows PowerShell 5.1 (no -Form).
        $boundary = 'CodexTelegram' + [Guid]::NewGuid().ToString('N')
        $multipart = New-Object IO.MemoryStream
        $writeText = {
            param([string]$Value)
            $bytes = [Text.Encoding]::UTF8.GetBytes($Value)
            $multipart.Write($bytes, 0, $bytes.Length)
        }
        foreach ($part in @(@('chat_id',[string]$config.ChatId),@('caption',$message))) {
            & $writeText ("--$boundary`r`nContent-Disposition: form-data; name=`"" + $part[0] + "`"`r`nContent-Type: text/plain; charset=utf-8`r`n`r`n" + $part[1] + "`r`n")
        }
        # A generic upload filename avoids leaking the local path or private basename.
        $mime = switch ($extension) {
            '.png' { 'image/png' }
            '.jpg' { 'image/jpeg' }
            '.jpeg' { 'image/jpeg' }
            default { 'application/octet-stream' }
        }
        & $writeText ("--$boundary`r`nContent-Disposition: form-data; name=`"$field`"; filename=`"preview$extension`"`r`nContent-Type: $mime`r`n`r`n")
        $multipart.Write($fileBytes, 0, $fileBytes.Length)
        & $writeText ("`r`n--$boundary--`r`n")
        $body = $multipart.ToArray()
        $contentType = 'multipart/form-data; boundary=' + $boundary
    }
    $uri = 'https://api.telegram.org/bot' + $token + '/' + $method
    $failureStage = 'Telegram request'
    $response = Invoke-RestMethod -Uri $uri -Method Post -Body $body -ContentType $contentType `
        -TimeoutSec 15 -MaximumRedirection 0 -ErrorAction Stop -Verbose:$false -Debug:$false
    if ($response.ok -ne $true) {
        $apiCode = 0
        [void][int]::TryParse([string]$response.error_code, [ref]$apiCode)
        $failureStage = "Telegram API rejection (error_code=$apiCode)"
        throw 'API did not confirm delivery'
    }
    $messageId = 0L
    if ($null -ne $response.result) {
        [void][long]::TryParse([string]$response.result.message_id, [ref]$messageId)
    }
    Write-Output "Telegram $method sent (API ok=true). message_id=$messageId"
}
catch {
    # Expose only a numeric HTTP status / known transport category, never raw errors.
    if ($failureStage -eq 'Telegram request') {
        $httpStatus = 0
        if ($null -ne $_.Exception.Response) {
            try { $httpStatus = [int]$_.Exception.Response.StatusCode } catch { }
        }
        if ($httpStatus -gt 0) { $failureStage = "Telegram request (HTTP $httpStatus)" }
        elseif ($_.Exception -is [System.Net.WebException] -and
                $_.Exception.Status -eq [System.Net.WebExceptionStatus]::Timeout) {
            $failureStage = 'Telegram request (timeout; delivery unconfirmed)'
        }
    }
    Write-Warning -Message "Telegram notification not sent ($failureStage; details redacted). Main work may continue." -WarningAction Continue
}
finally {
    if ($tokenPointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($tokenPointer) }
    if ($null -ne $secureToken) { $secureToken.Dispose() }
    if ($null -ne $multipart) { $multipart.Dispose() }
    $token = $uri = $config = $response = $body = $fileBytes = $null
}
