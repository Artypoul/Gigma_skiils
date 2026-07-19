[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$pluginRoot = Split-Path -Parent $PSScriptRoot
$hooksPath = Join-Path $pluginRoot 'hooks/hooks.json'
$config = Get-Content -LiteralPath $hooksPath -Raw | ConvertFrom-Json
$windowsCommand = [string]$config.hooks.SessionStart[0].hooks[0].commandWindows
$portableCommand = [string]$config.hooks.SessionStart[0].hooks[0].command
$tempBase = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
$testRoot = Join-Path $tempBase ('first-pass-hook-smoke-' + [guid]::NewGuid().ToString('N'))
$pointer = Join-Path $testRoot 'pointer.json'
$script:Assertions = 0

function Assert-True {
    param([bool]$Condition, [string]$Message)
    $script:Assertions++
    if (-not $Condition) { throw "Assertion failed: $Message" }
}

function Get-FileFingerprint {
    param([Parameter(Mandatory)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return 'missing' }
    (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
}

function Invoke-ProcessJson {
    param(
        [Parameter(Mandatory)][string]$FileName,
        [Parameter(Mandatory)][string[]]$Arguments,
        [Parameter(Mandatory)][string]$InputJson
    )
    $psi = [Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $FileName
    foreach ($argument in $Arguments) { [void]$psi.ArgumentList.Add($argument) }
    $psi.RedirectStandardInput = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.StandardInputEncoding = [Text.UTF8Encoding]::new($false)
    $psi.StandardOutputEncoding = [Text.UTF8Encoding]::new($false)
    $psi.StandardErrorEncoding = [Text.UTF8Encoding]::new($false)
    $process = [Diagnostics.Process]::Start($psi)
    $process.StandardInput.Write($InputJson)
    $process.StandardInput.Close()
    $stdout = $process.StandardOutput.ReadToEnd().Trim()
    $stderr = $process.StandardError.ReadToEnd().Trim()
    $process.WaitForExit()
    if ($process.ExitCode -ne 0) { throw "$FileName failed: $stderr" }
    if (-not $stdout) { throw "$FileName returned no hook output." }
    $stdout | ConvertFrom-Json -AsHashtable
}

function New-SessionStartJson {
    param([Parameter(Mandatory)][string]$SessionId)
    @{
        session_id = $SessionId
        cwd = $pluginRoot
        hook_event_name = 'SessionStart'
        source = 'startup'
        model = 'contract-model'
        permission_mode = 'default'
    } | ConvertTo-Json -Compress
}

$saved = @{
    PLUGIN_ROOT = $env:PLUGIN_ROOT
    PLUGIN_DATA = $env:PLUGIN_DATA
    CLAUDE_PLUGIN_ROOT = $env:CLAUDE_PLUGIN_ROOT
    CLAUDE_PLUGIN_DATA = $env:CLAUDE_PLUGIN_DATA
    FIRST_PASS_QUALITY_POINTER = $env:FIRST_PASS_QUALITY_POINTER
    FIRST_PASS_QUALITY_TEST_DATA = $env:FIRST_PASS_QUALITY_TEST_DATA
}
$protectedPointers = @(
    (Join-Path $HOME '.codex/first-pass-quality-pointer.json'),
    (Join-Path $HOME '.claude/first-pass-quality-pointer.json')
)
$protectedPointerBefore = @{}
foreach ($protectedPointer in $protectedPointers) {
    $protectedPointerBefore[$protectedPointer] = Get-FileFingerprint -Path $protectedPointer
}

try {
    New-Item -ItemType Directory -Path $testRoot -Force | Out-Null
    $env:FIRST_PASS_QUALITY_POINTER = $pointer
    Remove-Item Env:FIRST_PASS_QUALITY_TEST_DATA -ErrorAction SilentlyContinue

    $env:PLUGIN_ROOT = $pluginRoot
    $env:PLUGIN_DATA = Join-Path $testRoot 'codex-plugin-data'
    Remove-Item Env:CLAUDE_PLUGIN_ROOT, Env:CLAUDE_PLUGIN_DATA -ErrorAction SilentlyContinue
    $codexText = (New-SessionStartJson 'codex-hook-smoke') | & cmd.exe /d /s /c $windowsCommand
    if ($LASTEXITCODE -ne 0) { throw "Codex commandWindows failed with exit code $LASTEXITCODE." }
    $codex = ($codexText -join [Environment]::NewLine) | ConvertFrom-Json -AsHashtable
    $codexPointer = Get-Content -LiteralPath $pointer -Raw | ConvertFrom-Json -AsHashtable
    Assert-True ($codex.hookSpecificOutput.hookEventName -eq 'SessionStart') 'Codex commandWindows must return typed SessionStart output.'
    Assert-True ([string]$codexPointer.dataRoot -eq (Join-Path $env:PLUGIN_DATA 'first-pass-quality')) 'Codex commandWindows must bind state to PLUGIN_DATA.'
    Assert-True (Test-Path -LiteralPath (Join-Path $codexPointer.dataRoot 'sessions/codex-hook-smoke.json')) 'Codex commandWindows must persist the session in isolated plugin data.'

    Remove-Item -LiteralPath $pointer -Force
    Remove-Item Env:PLUGIN_ROOT, Env:PLUGIN_DATA -ErrorAction SilentlyContinue
    $env:CLAUDE_PLUGIN_ROOT = $pluginRoot
    $env:CLAUDE_PLUGIN_DATA = Join-Path $testRoot 'claude-plugin-data'
    $claude = Invoke-ProcessJson -FileName 'bash' -Arguments @('-lc', $portableCommand) -InputJson (New-SessionStartJson 'claude-hook-smoke')
    $claudePointer = Get-Content -LiteralPath $pointer -Raw | ConvertFrom-Json -AsHashtable
    Assert-True ($claude.hookSpecificOutput.hookEventName -eq 'SessionStart') 'Portable command must return typed SessionStart output with Claude variables.'
    Assert-True ([string]$claudePointer.dataRoot -eq (Join-Path $env:CLAUDE_PLUGIN_DATA 'first-pass-quality')) 'Portable command must bind state to CLAUDE_PLUGIN_DATA.'
    Assert-True (Test-Path -LiteralPath (Join-Path $claudePointer.dataRoot 'sessions/claude-hook-smoke.json')) 'Portable command must persist the Claude session in isolated plugin data.'
    foreach ($protectedPointer in $protectedPointers) {
        Assert-True ((Get-FileFingerprint -Path $protectedPointer) -eq $protectedPointerBefore[$protectedPointer]) "Hook smoke must not change the user pointer: $protectedPointer"
    }

    [pscustomobject]@{
        status = 'passed'
        assertions = $script:Assertions
        runtimes = @('codex-windows', 'claude-bash-with-pwsh')
    } | ConvertTo-Json
} finally {
    foreach ($name in $saved.Keys) {
        if ($null -eq $saved[$name]) { Remove-Item ("Env:$name") -ErrorAction SilentlyContinue }
        else { Set-Item ("Env:$name") $saved[$name] }
    }
    $resolved = [IO.Path]::GetFullPath($testRoot)
    $relative = [IO.Path]::GetRelativePath($tempBase, $resolved)
    if ((Test-Path -LiteralPath $resolved) -and -not [IO.Path]::IsPathRooted($relative) -and -not $relative.StartsWith('..')) {
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}
