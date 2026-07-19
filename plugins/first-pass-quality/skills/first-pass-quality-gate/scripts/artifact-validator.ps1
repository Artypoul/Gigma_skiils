[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Path,
    [ValidateSet('auto', 'file', 'markdown', 'json', 'image', 'pdf', 'docx')]
    [string]$Kind = 'auto',
    [string]$Expectation
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)

function Get-Hash {
    param([Parameter(Mandatory)][string]$File)
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        $stream = [IO.File]::OpenRead($File)
        try { ([Convert]::ToHexString($sha.ComputeHash($stream))).ToLowerInvariant() }
        finally { $stream.Dispose() }
    } finally {
        $sha.Dispose()
    }
}

function Get-Kind {
    param([string]$File, [string]$Requested)
    if ($Requested -ne 'auto') { return $Requested }
    switch ([IO.Path]::GetExtension($File).ToLowerInvariant()) {
        '.md' { 'markdown' }
        '.json' { 'json' }
        '.png' { 'image' }
        '.jpg' { 'image' }
        '.jpeg' { 'image' }
        '.webp' { 'image' }
        '.pdf' { 'pdf' }
        '.docx' { 'docx' }
        default { 'file' }
    }
}

function Get-BigEndianUInt32 {
    param([byte[]]$Bytes, [int]$Offset)
    ([uint32]$Bytes[$Offset] -shl 24) -bor ([uint32]$Bytes[$Offset + 1] -shl 16) -bor ([uint32]$Bytes[$Offset + 2] -shl 8) -bor [uint32]$Bytes[$Offset + 3]
}

function Get-JpegDimensions {
    param([byte[]]$Bytes)
    $i = 2
    while ($i + 8 -lt $Bytes.Length) {
        if ($Bytes[$i] -ne 0xFF) { $i++; continue }
        while ($i -lt $Bytes.Length -and $Bytes[$i] -eq 0xFF) { $i++ }
        if ($i -ge $Bytes.Length) { break }
        $marker = $Bytes[$i]; $i++
        if ($marker -in @(0xD8, 0xD9)) { continue }
        if ($i + 1 -ge $Bytes.Length) { break }
        $length = ([int]$Bytes[$i] -shl 8) -bor [int]$Bytes[$i + 1]
        if ($length -lt 2 -or $i + $length -gt $Bytes.Length) { break }
        if ($marker -in @(0xC0,0xC1,0xC2,0xC3,0xC5,0xC6,0xC7,0xC9,0xCA,0xCB,0xCD,0xCE,0xCF)) {
            return @{ height = (([int]$Bytes[$i + 3] -shl 8) -bor [int]$Bytes[$i + 4]); width = (([int]$Bytes[$i + 5] -shl 8) -bor [int]$Bytes[$i + 6]) }
        }
        $i += $length
    }
    $null
}

$resolved = [IO.Path]::GetFullPath($Path)
$result = [ordered]@{
    path = $resolved
    kind = $null
    status = 'failed'
    checks = @()
    sizeBytes = 0
    sha256 = $null
    expectation = $Expectation
}

if (-not (Test-Path -LiteralPath $resolved -PathType Leaf)) {
    $result.checks += @{ name = 'exists'; status = 'failed'; detail = 'file not found' }
    $result | ConvertTo-Json -Depth 8
    exit 2
}

$item = Get-Item -LiteralPath $resolved
$result.sizeBytes = [int64]$item.Length
$result.sha256 = Get-Hash $resolved
$result.kind = Get-Kind $resolved $Kind
$result.checks += @{ name = 'exists'; status = 'passed'; detail = 'file exists' }
$result.checks += @{ name = 'nonempty'; status = $(if ($item.Length -gt 0) { 'passed' } else { 'failed' }); detail = "$($item.Length) bytes" }

switch ($result.kind) {
    'json' {
        try {
            $null = Get-Content -LiteralPath $resolved -Raw -Encoding UTF8 | ConvertFrom-Json
            $result.checks += @{ name = 'json-parse'; status = 'passed'; detail = 'valid JSON' }
        } catch {
            $result.checks += @{ name = 'json-parse'; status = 'failed'; detail = $_.Exception.Message }
        }
    }
    'markdown' {
        $text = Get-Content -LiteralPath $resolved -Raw -Encoding UTF8
        $needsTable = $Expectation -match '(?i)table|таблиц'
        $result.checks += @{ name = 'headings'; status = $(if ($text -match '(?m)^#{1,6}\s+\S') { 'passed' } else { 'unknown' }); detail = 'markdown heading scan' }
        $hasTable = $text -match '(?ms)^\|[^\r\n]+\|\r?\n\|\s*:?-{3,}[^\r\n]*\|'
        $result.checks += @{ name = 'tables'; status = $(if ($hasTable) { 'passed' } elseif ($needsTable) { 'failed' } else { 'passed' }); detail = $(if ($needsTable) { 'header and separator row required' } else { 'markdown table optional' }) }
    }
    'image' {
        $bytes = [IO.File]::ReadAllBytes($resolved)
        $isPng = $bytes.Length -ge 24 -and @($bytes[0..7]) -join ',' -eq '137,80,78,71,13,10,26,10' -and [Text.Encoding]::ASCII.GetString($bytes, 12, 4) -eq 'IHDR'
        $isJpeg = $bytes.Length -ge 4 -and $bytes[0] -eq 0xFF -and $bytes[1] -eq 0xD8 -and $bytes[-2] -eq 0xFF -and $bytes[-1] -eq 0xD9
        $isWebp = $bytes.Length -ge 12 -and [Text.Encoding]::ASCII.GetString($bytes, 0, 4) -eq 'RIFF' -and [Text.Encoding]::ASCII.GetString($bytes, 8, 4) -eq 'WEBP' -and ([BitConverter]::ToUInt32($bytes, 4) + 8) -le $bytes.Length
        $known = $isPng -or $isJpeg -or $isWebp
        $result.checks += @{ name = 'image-signature'; status = $(if ($known) { 'passed' } else { 'failed' }); detail = 'full PNG/JPEG/WEBP container signature' }
        if ($isPng) {
            $width = Get-BigEndianUInt32 $bytes 16; $height = Get-BigEndianUInt32 $bytes 20
            $result.checks += @{ name = 'image-dimensions'; status = $(if ($width -gt 0 -and $height -gt 0) { 'passed' } else { 'failed' }); detail = "${width}x${height}" }
        } elseif ($isJpeg) {
            $dimensions = Get-JpegDimensions $bytes
            $result.checks += @{ name = 'image-dimensions'; status = $(if ($dimensions -and $dimensions.width -gt 0 -and $dimensions.height -gt 0) { 'passed' } else { 'unknown' }); detail = $(if ($dimensions) { "$($dimensions.width)x$($dimensions.height)" } else { 'SOF dimensions not found' }) }
        }
    }
    'pdf' {
        $bytes = [IO.File]::ReadAllBytes($resolved)
        $isPdf = $bytes.Length -ge 8 -and [Text.Encoding]::ASCII.GetString($bytes, 0, 5) -eq '%PDF-'
        $result.checks += @{ name = 'pdf-signature'; status = $(if ($isPdf) { 'passed' } else { 'failed' }); detail = 'PDF header scan' }
        $tailLength = [Math]::Min(2048, $bytes.Length)
        $tail = if ($tailLength -gt 0) { [Text.Encoding]::ASCII.GetString($bytes, $bytes.Length - $tailLength, $tailLength) } else { '' }
        $result.checks += @{ name = 'pdf-eof'; status = $(if ($tail -match '%%EOF') { 'passed' } else { 'failed' }); detail = 'PDF EOF marker in final 2 KB' }
        $pdfInfo = Get-Command pdfinfo -ErrorAction SilentlyContinue
        if ($pdfInfo) {
            $info = @(& $pdfInfo.Source $resolved 2>&1)
            $code = $LASTEXITCODE
            $pages = @($info | Select-String -Pattern '^Pages:\s+(\d+)' | Select-Object -First 1)
            $result.checks += @{ name = 'pdf-parse'; status = $(if ($code -eq 0 -and $pages.Count -eq 1) { 'passed' } else { 'unknown' }); detail = $(if ($pages.Count -eq 1) { $pages[0].Line } else { 'pdfinfo unavailable or could not read page count' }) }
        }
        if ($Expectation -match '(?i)render|visual|layout|визуал|рендер|макет') {
            $result.checks += @{ name = 'pdf-render'; status = 'unknown'; detail = 'render/screenshot must be supplied by a visual validator' }
        }
    }
    'docx' {
        try {
            Add-Type -AssemblyName System.IO.Compression.FileSystem
            $archive = [IO.Compression.ZipFile]::OpenRead($resolved)
            try {
                $names = @($archive.Entries | ForEach-Object { $_.FullName })
                $required = @('[Content_Types].xml', '_rels/.rels', 'word/document.xml')
                $missing = @($required | Where-Object { $_ -notin $names })
                $result.checks += @{ name = 'docx-parts'; status = $(if ($missing.Count -eq 0) { 'passed' } else { 'failed' }); detail = $(if ($missing.Count) { 'missing: ' + ($missing -join ', ') } else { 'required OOXML parts present' }) }
                $document = $archive.GetEntry('word/document.xml')
                if ($document) {
                    $reader = [IO.StreamReader]::new($document.Open(), [Text.Encoding]::UTF8, $true)
                    try { [xml]$xml = $reader.ReadToEnd(); $null = $xml.DocumentElement; $xmlOk = $true } catch { $xmlOk = $false } finally { $reader.Dispose() }
                    $result.checks += @{ name = 'docx-document-xml'; status = $(if ($xmlOk) { 'passed' } else { 'failed' }); detail = 'word/document.xml parses as XML' }
                }
            } finally { $archive.Dispose() }
        } catch {
            $result.checks += @{ name = 'docx-container'; status = 'failed'; detail = $_.Exception.Message }
        }
        if ($Expectation -match '(?i)render|visual|layout|визуал|рендер|макет') {
            $result.checks += @{ name = 'docx-render'; status = 'unknown'; detail = 'render/screenshot must be supplied by a document visual validator' }
        }
    }
}

$failed = @($result.checks | Where-Object { $_.status -eq 'failed' })
$unknown = @($result.checks | Where-Object { $_.status -eq 'unknown' })
if ($failed.Count -gt 0) {
    $result.status = 'failed'
    $result | ConvertTo-Json -Depth 8
    exit 2
}
if ($unknown.Count -gt 0) {
    $result.status = 'unknown'
    $result | ConvertTo-Json -Depth 8
    exit 1
}
$result.status = 'passed'
$result | ConvertTo-Json -Depth 8
