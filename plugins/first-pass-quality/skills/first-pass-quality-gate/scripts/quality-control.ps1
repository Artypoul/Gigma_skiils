[CmdletBinding()]
param(
    [ValidateSet('Hook', 'StartTask', 'ConfirmContext', 'SetGate', 'SetEntityLock', 'AuthorizeProduction', 'AddEvidence', 'SetStatus', 'AuthorizeDelegation', 'VerifyDelegation', 'AcknowledgeWriteRecovery', 'ShowStatus', 'ResetTask', 'Version')]
    [string]$Action = 'Hook',
    [string]$SessionId,
    [string]$Outcome,
    [string]$Scope,
    [string]$OutOfScope,
    [string]$Mode,
    [string]$Risk,
    [string]$CompletionPolicy,
    [string]$Workflow,
    [string]$WorkflowStage,
    [string]$WriteScope,
    [string]$PrePublishWhen,
    [string]$DoneWhen,
    [string]$AllowedActions,
    [switch]$AllowDirty,
    [switch]$Continuation,
    [string]$ContextDisposition,
    [string]$ContextNote,
    [string]$Gate,
    [string]$GateStatus,
    [string]$EntityType,
    [string]$StableId,
    [string]$ProjectId,
    [string]$Environment,
    [string]$Intent,
    [string]$WrapperToolName,
    [string]$ExpectedBeforeHash,
    [string]$ChangeHash,
    [string]$StableIdField,
    [string]$ProjectIdField,
    [string]$ExpectedToolInputJson,
    [string]$CriterionId,
    [string]$Validator,
    [string]$EvidenceStatus,
    [string]$Subject,
    [string]$ExpectedToolName,
    [string]$FinalStatus,
    [string]$Reason,
    [string]$Limitations,
    [string]$NextAction,
    [switch]$HardBlocker,
    [string]$DelegationOutcome,
    [string]$DelegationScope,
    [string]$DelegationEvidence
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$script:SchemaVersion = 3
$script:PolicyVersion = '0.3.0'
$script:ListSeparator = '~~'

function Get-UtcNow {
    [DateTime]::UtcNow.ToString('o')
}

function Get-Hash {
    param([AllowNull()][string]$Value)
    if ($null -eq $Value) { $Value = '' }
    $bytes = [Text.Encoding]::UTF8.GetBytes($Value)
    $hash = [Security.Cryptography.SHA256]::HashData($bytes)
    ([Convert]::ToHexString($hash)).ToLowerInvariant()
}

function Get-SafeId {
    param([Parameter(Mandatory)][string]$Value)
    [regex]::Replace($Value, '[^A-Za-z0-9._-]', '_')
}

function Split-Values {
    param([AllowNull()][string]$Value)
    if ([string]::IsNullOrWhiteSpace($Value)) { return @() }
    @($Value.Split($script:ListSeparator, [StringSplitOptions]::RemoveEmptyEntries) | ForEach-Object { $_.Trim() } | Where-Object { $_ })
}

function Get-NormalizedText {
    param([AllowNull()][string]$Value, [int]$MaxLength = 600)
    if ([string]::IsNullOrWhiteSpace($Value)) { return '' }
    $normalized = [regex]::Replace($Value, '[\r\n\t]+', ' ').Trim()
    if ($normalized.Length -gt $MaxLength) { return $normalized.Substring(0, $MaxLength) }
    $normalized
}

function ConvertTo-CanonicalValue {
    param([AllowNull()]$Value)
    if ($null -eq $Value) { return $null }
    if ($Value -is [Collections.IDictionary]) {
        $result = [ordered]@{}
        foreach ($key in @($Value.Keys | ForEach-Object { [string]$_ } | Sort-Object)) {
            $result[$key] = ConvertTo-CanonicalValue $Value[$key]
        }
        return $result
    }
    if ($Value -is [Collections.IEnumerable] -and $Value -isnot [string]) {
        $items = @()
        foreach ($item in $Value) { $items += ,(ConvertTo-CanonicalValue $item) }
        return $items
    }
    $Value
}

function ConvertTo-CanonicalJson {
    param([AllowNull()]$Value)
    ConvertTo-CanonicalValue $Value | ConvertTo-Json -Depth 32 -Compress
}

function Get-NestedValue {
    param([AllowNull()]$Value, [Parameter(Mandatory)][string]$Path)
    $current = $Value
    foreach ($segment in @($Path.Split('.', [StringSplitOptions]::RemoveEmptyEntries))) {
        if ($current -is [Collections.IDictionary] -and $current.Contains($segment)) {
            $current = $current[$segment]
            continue
        }
        if ($null -ne $current) {
            $property = $current.PSObject.Properties[$segment]
            if ($property) { $current = $property.Value; continue }
        }
        return $null
    }
    $current
}

function Get-ToolInputHash {
    param([AllowNull()]$ToolInput)
    Get-Hash (ConvertTo-CanonicalJson $ToolInput)
}

function Test-IsConciseClarification {
    param([AllowNull()][string]$Message)
    if ([string]::IsNullOrWhiteSpace($Message)) { return $false }
    $text = $Message.Trim()
    if ($text.Length -gt 500) { return $false }
    if (@([regex]::Matches($text, '\?')).Count -ne 1) { return $false }
    $text -match '\?\s*$'
}

function Get-GitRoot {
    param([Parameter(Mandatory)][string]$Cwd)
    try {
        $root = (& git -C $Cwd rev-parse --show-toplevel 2>$null | Select-Object -First 1)
        if ($LASTEXITCODE -eq 0 -and $root) { return [IO.Path]::GetFullPath([string]$root) }
    } catch { }
    $null
}

function Get-AgentDataNamespace {
    if ($env:CLAUDE_PLUGIN_ROOT -and -not $env:PLUGIN_ROOT) { return '.claude' }
    '.codex'
}

function Get-PointerPath {
    if ($env:FIRST_PASS_QUALITY_POINTER) { return [IO.Path]::GetFullPath($env:FIRST_PASS_QUALITY_POINTER) }
    Join-Path $HOME ((Get-AgentDataNamespace) + '/first-pass-quality-pointer.json')
}

function Set-DataRootPointer {
    param([Parameter(Mandatory)][string]$Root)
    if ($env:FIRST_PASS_QUALITY_TEST_DATA) { return }
    $path = Get-PointerPath
    $parent = Split-Path -Parent $path
    if (-not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
    $payload = @{ schemaVersion = 1; dataRoot = $Root; updatedAt = Get-UtcNow } | ConvertTo-Json -Compress
    [IO.File]::WriteAllText($path, $payload, [Text.UTF8Encoding]::new($false))
}

function Get-DataRoot {
    if ($env:FIRST_PASS_QUALITY_TEST_DATA) {
        return [IO.Path]::GetFullPath($env:FIRST_PASS_QUALITY_TEST_DATA)
    }
    $pluginData = if ($env:PLUGIN_DATA) { $env:PLUGIN_DATA } elseif ($env:CLAUDE_PLUGIN_DATA) { $env:CLAUDE_PLUGIN_DATA } else { $null }
    if ($pluginData) {
        $root = Join-Path $pluginData 'first-pass-quality'
        Set-DataRootPointer -Root $root
        return [IO.Path]::GetFullPath($root)
    }
    $pointer = Get-PointerPath
    if (Test-Path -LiteralPath $pointer) {
        try {
            $saved = Get-Content -LiteralPath $pointer -Raw | ConvertFrom-Json -AsHashtable
            if ($saved.dataRoot) { return [IO.Path]::GetFullPath([string]$saved.dataRoot) }
        } catch { }
    }
    [IO.Path]::GetFullPath((Join-Path $HOME ((Get-AgentDataNamespace) + '/first-pass-quality-data')))
}

function Initialize-DataRoot {
    param([Parameter(Mandatory)][string]$Root)
    foreach ($relative in @('sessions', 'telemetry', 'current')) {
        $path = Join-Path $Root $relative
        if (-not (Test-Path -LiteralPath $path)) { New-Item -ItemType Directory -Path $path -Force | Out-Null }
    }
}

function Get-StatePath {
    param([Parameter(Mandatory)][string]$Root, [Parameter(Mandatory)][string]$Id)
    Join-Path (Join-Path $Root 'sessions') ((Get-SafeId $Id) + '.json')
}

function Read-State {
    param([Parameter(Mandatory)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    try {
        $state = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json -AsHashtable
        if ($state -and $state.gates -and -not $state.gates.ContainsKey('publish')) {
            $state.gates.publish = if ($state.task -and $state.task.mode -eq 'pr') { 'pending' } else { 'not_required' }
        }
        if ($state -and $state.task) {
            if (-not $state.task.ContainsKey('writeScopePaths')) { $state.task.writeScopePaths = @($state.task.scopePaths) }
            if (-not $state.task.ContainsKey('workflowStage')) { $state.task.workflowStage = 'none' }
            if (-not $state.task.ContainsKey('prePublishWhen')) { $state.task.prePublishWhen = @($state.task.doneWhen) }
        }
        $state
    } catch { $null }
}

function Write-State {
    param([Parameter(Mandatory)][string]$Path, [Parameter(Mandatory)][hashtable]$State)
    $State.updatedAt = Get-UtcNow
    $State.revision = [int]$State.revision + 1
    $json = $State | ConvertTo-Json -Depth 24
    $temp = "$Path.$PID.tmp"
    [IO.File]::WriteAllText($temp, $json, [Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $temp -Destination $Path -Force
}

function Invoke-WithSessionLock {
    param([Parameter(Mandatory)][string]$Id, [Parameter(Mandatory)][scriptblock]$Operation)
    $name = 'Local\FirstPassQuality_' + (Get-Hash $Id).Substring(0, 24)
    $mutex = [Threading.Mutex]::new($false, $name)
    $acquired = $false
    try {
        $acquired = $mutex.WaitOne([TimeSpan]::FromSeconds(15))
        if (-not $acquired) { throw 'Timed out waiting for quality state lock.' }
        & $Operation
    } finally {
        if ($acquired) { $mutex.ReleaseMutex() }
        $mutex.Dispose()
    }
}

function New-State {
    param([Parameter(Mandatory)][hashtable]$HookData)
    @{
        schemaVersion = $script:SchemaVersion
        policyVersion = $script:PolicyVersion
        sessionId = [string]$HookData.session_id
        turnId = if ($HookData.ContainsKey('turn_id')) { [string]$HookData.turn_id } else { '' }
        revision = 0
        createdAt = Get-UtcNow
        updatedAt = Get-UtcNow
        model = [string]$HookData.model
        cwd = [string]$HookData.cwd
        phase = 'awaiting_clarification'
        promptCount = 0
        clarificationAsked = $false
        clarified = $false
        autoReview = $false
        stopOverride = $false
        contextConfirmed = $false
        confirmationCandidate = $false
        confirmationTurnId = $null
        delegationCandidate = $false
        lastPromptHash = $null
        lastPromptAt = $null
        task = $null
        entityLocks = @()
        evidence = @()
        gates = @{
            clarification = 'pending'
            context = 'pending'
            workflow = 'missing'
            risk = 'pending'
            publish = 'not_required'
            acceptance = 'pending'
            selfReview = 'pending'
            review = 'not_required'
        }
        delegation = $null
        tools = @{ count = 0; writes = 0; failures = 0 }
        lastTool = $null
        lastWriteToolUseId = $null
        lastWriteAt = $null
        failedWritePending = $false
        pendingProduction = $null
        lastProduction = $null
        agentChangedFiles = @()
        contextHistory = @()
        compaction = @{ count = 0; snapshotAt = $null; snapshotHash = $null; restoredAt = $null }
        status = 'active'
        terminal = @{ reason = $null; limitations = @(); nextAction = $null; hardBlocker = $false }
    }
}

function Set-CurrentSessionIndex {
    param([Parameter(Mandatory)][string]$Root, [Parameter(Mandatory)][hashtable]$State)
    $key = (Get-Hash ([string]$State.cwd)).Substring(0, 32)
    $path = Join-Path (Join-Path $Root 'current') ($key + '.json')
    $json = @{ sessionId = $State.sessionId; cwdHash = Get-Hash ([string]$State.cwd); updatedAt = Get-UtcNow } | ConvertTo-Json -Compress
    [IO.File]::WriteAllText($path, $json, [Text.UTF8Encoding]::new($false))
}

function Get-SessionIdForAction {
    param([Parameter(Mandatory)][string]$Root)
    if ($SessionId) { return $SessionId }
    if ($env:CODEX_THREAD_ID) { return $env:CODEX_THREAD_ID }
    $cwdHash = (Get-Hash ((Get-Location).Path)).Substring(0, 32)
    $index = Join-Path (Join-Path $Root 'current') ($cwdHash + '.json')
    if (Test-Path -LiteralPath $index) {
        $saved = Get-Content -LiteralPath $index -Raw | ConvertFrom-Json -AsHashtable
        if ($saved.sessionId) { return [string]$saved.sessionId }
    }
    throw 'No agent session id found. Start a new task so SessionStart can initialize quality state.'
}

function Write-Telemetry {
    param([Parameter(Mandatory)][string]$Root, [Parameter(Mandatory)][hashtable]$Record)
    $payload = @{
        timestamp = Get-UtcNow
        sessionIdHash = (Get-Hash ([string]$Record.sessionId)).Substring(0, 24)
        turnIdHash = (Get-Hash ([string]$Record.turnId)).Substring(0, 24)
        model = [string]$Record.model
        cwdHash = (Get-Hash ([string]$Record.cwd)).Substring(0, 24)
        event = [string]$Record.event
        action = [string]$Record.action
        result = [string]$Record.result
        toolNameHash = if ($Record.toolName) { (Get-Hash ([string]$Record.toolName)).Substring(0, 24) } else { '' }
        phase = [string]$Record.phase
        status = [string]$Record.status
        risk = [string]$Record.risk
        userCorrectionDetected = [bool]$Record.userCorrectionDetected
    } | ConvertTo-Json -Compress
    $path = Join-Path (Join-Path $Root 'telemetry') 'quality.jsonl'
    $mutex = [Threading.Mutex]::new($false, 'Local\FirstPassQuality_Telemetry')
    $acquired = $false
    try {
        $acquired = $mutex.WaitOne([TimeSpan]::FromSeconds(10))
        if (-not $acquired) { return }
        [IO.File]::AppendAllText($path, $payload + [Environment]::NewLine, [Text.UTF8Encoding]::new($false))
    } finally {
        if ($acquired) { $mutex.ReleaseMutex() }
        $mutex.Dispose()
    }
}

function Write-HookOutput {
    param([AllowNull()][hashtable]$Output)
    if ($null -eq $Output -or $Output.Count -eq 0) { return }
    $Output | ConvertTo-Json -Depth 12 -Compress | Write-Output
}

function New-PreToolDeny {
    param([Parameter(Mandatory)][string]$Message)
    @{
        hookSpecificOutput = @{
            hookEventName = 'PreToolUse'
            permissionDecision = 'deny'
            permissionDecisionReason = $Message
        }
    }
}

function New-PermissionDeny {
    param([Parameter(Mandatory)][string]$Message)
    @{
        hookSpecificOutput = @{
            hookEventName = 'PermissionRequest'
            decision = @{ behavior = 'deny'; message = $Message }
        }
    }
}

function New-StopBlock {
    param([Parameter(Mandatory)][string]$Message)
    @{ decision = 'block'; reason = $Message }
}

function Get-CommandText {
    param([AllowNull()]$ToolInput)
    if ($ToolInput -is [hashtable]) {
        foreach ($key in @('command', 'cmd', 'script')) {
            if ($ToolInput.ContainsKey($key) -and $ToolInput[$key]) { return [string]$ToolInput[$key] }
        }
    }
    ''
}

function Test-IsQualityControlCommand {
    param([AllowNull()][string]$Command)
    if ([string]::IsNullOrWhiteSpace($Command)) { return $false }
    $allowedRoot = '\$\(\s*\$env:PLUGIN_ROOT\s*\?\?\s*\$env:CLAUDE_PLUGIN_ROOT\s*\)'
    $controllerRelative = 'skills[\\/]first-pass-quality-gate[\\/]scripts[\\/]quality-control\.ps1'
    $canonicalPath = ('^\s*&\s*["'']?{0}[\\/]{1}["'']?' -f $allowedRoot, $controllerRelative)
    $absolutePath = ('(?i)^\s*&\s*["'']?(?:[A-Z]:[\\/]|/).*?first-pass-quality[\\/].*?{0}["'']?' -f $controllerRelative)
    if ($Command -notmatch $canonicalPath -and $Command -notmatch $absolutePath) { return $false }
    if ($Command -notmatch '(?i)-Action\s+(StartTask|ConfirmContext|SetGate|SetEntityLock|AuthorizeProduction|AddEvidence|SetStatus|AuthorizeDelegation|VerifyDelegation|AcknowledgeWriteRecovery|ShowStatus|ResetTask|Version)\b') { return $false }
    if ($Command -notmatch '^\s*&\s*') { return $false }
    if ($Command -match '[\r\n;|><`]|&&|\|\|') { return $false }
    $withoutAllowedRoot = [regex]::Replace($Command, $allowedRoot, '')
    if ($withoutAllowedRoot -match '\$\(') { return $false }
    $withoutLeadingCall = [regex]::Replace($withoutAllowedRoot, '^\s*&\s*', '')
    if ($withoutLeadingCall -match '&') { return $false }
    $true
}

function Test-IsGhApiExternalWrite {
    param([AllowNull()][string]$Command)
    if ([string]::IsNullOrWhiteSpace($Command) -or $Command -notmatch '(?i)\bgh\s+api\b') { return $false }
    if ($Command -match '(?i)(?:--method|-X)(?:\s+|=)(POST|PUT|PATCH|DELETE)\b') { return $true }
    if ($Command -match '(?i)(?:--method|-X)(?:\s+|=)GET\b') { return $false }
    $Command -match '(?:^|\s)(?:(?-i:-f|-F)(?=\s|=)|(?-i:--raw-field|--field|--input)(?=\s|=))'
}

function Test-IsCurlExternalWrite {
    param([AllowNull()][string]$Command)
    if ([string]::IsNullOrWhiteSpace($Command) -or $Command -notmatch '(?i:\bcurl(?:\.exe)?\b)') { return $false }
    $Command -match '(?:\s(?-i:-d|-F|-T)(?=\s|=)|\s(?-i:--data(?:-[a-z-]+)?|--json|--form(?:-string)?|--upload-file)(?=\s|=)|\s(?-i:-X|--request)(?:\s+|=)(?i:POST|PUT|PATCH|DELETE)\b)'
}

function Test-IsRawFileMutationCommand {
    param([AllowNull()][string]$Command)
    if ([string]::IsNullOrWhiteSpace($Command)) { return $false }
    $powerShell = '(?i)\b(Set-Content|Add-Content|Out-File|Remove-Item|Move-Item|Copy-Item|New-Item)\b'
    $posix = '(?i)(?:^|[;&|]\s*|\s)(rm|mv|cp|mkdir|touch)(?:\.exe)?(?=\s|$)|\bsed(?:\.exe)?\b[^\r\n;|&]*\s-i(?:[^\s]*)?(?=\s|$)'
    $redirection = '(^|\s)(>>?|2>)\s*[^&]'
    $Command -match "$powerShell|$posix|$redirection"
}

function Get-ToolClassification {
    param([Parameter(Mandatory)][string]$ToolName, [AllowNull()]$ToolInput)
    $command = Get-CommandText $ToolInput
    if ($ToolName -eq 'Bash' -and (Test-IsQualityControlCommand $command)) { return @{ kind = 'management'; command = $command } }
    if ($ToolName -match '^(Agent|spawn_agent)$') { return @{ kind = 'delegation'; command = $command } }
    if ($ToolName -match '^(apply_patch|Edit|Write)$') { return @{ kind = 'write'; command = $command } }
    if ($ToolName -eq 'Bash') {
        $readPattern = '(?i)^\s*(rg\b|git\s+(status|diff|log|show|rev-parse|branch\s+--show-current|remote\s+-v)\b|gh\s+pr\s+(view|status|checks|diff)\b|gh\s+api\b|Get-Content\b|Get-ChildItem\b|Get-Item\b|Test-Path\b|Resolve-Path\b|Get-FileHash\b|Select-String\b|where\.exe\b|codex\s+(--version|features\s+list|plugin\s+list|doctor)\b)'
        $validatePattern = '(?i)(run-contract-tests\.ps1|artifact-validator\.ps1|quick_validate\.py|validate_plugin\.py|\bpytest\b|\bPester\b|\bnpm\s+(run\s+)?test\b|\bpnpm\s+(run\s+)?test\b|\bdotnet\s+test\b|\bcargo\s+test\b|\bgit\s+diff\s+--check\b)'
        $productionPattern = '(?i)\b(kubectl\s+(apply|delete|rollout|set|patch)|terraform\s+apply|ansible-playbook|gh\s+pr\s+merge|git\s+push\s+.*(--force|-f)|deploy|release\s+promote)\b'
        $externalWritePattern = '(?i)\b(Invoke-RestMethod|Invoke-WebRequest)\b.*\b(POST|PUT|PATCH|DELETE)\b|\b(ssh|scp|rsync|gh\s+(pr\s+(close|reopen)|issue\s+(create|edit|close)))\b'
        $writePattern = '(?i)\b(git\s+(merge|rebase|reset|clean)|npm\s+(install|uninstall)|pnpm\s+(add|remove|install)|yarn\s+(add|remove|install)|pip\s+install)\b'
        if ($command -match $productionPattern) { return @{ kind = 'production-shell'; command = $command } }
        if ($command -match '(?i)\bgit\s+commit\b') { return @{ kind = 'commit'; command = $command } }
        if ($command -match '(?i)\bgit\s+push\b') { return @{ kind = 'push'; command = $command } }
        if ($command -match '(?i)\bgit\s+add\b') { return @{ kind = 'vcs-stage'; command = $command } }
        if ($command -match '(?i)\bgh\s+pr\s+(create|edit|comment|review|ready)\b') { return @{ kind = 'pr-write'; command = $command } }
        if ((Test-IsCurlExternalWrite $command) -or (Test-IsGhApiExternalWrite $command) -or $command -match $externalWritePattern) { return @{ kind = 'external-write'; command = $command } }
        if ($command -match $validatePattern) { return @{ kind = 'validate'; command = $command } }
        if ((Test-IsRawFileMutationCommand $command) -or $command -match $writePattern) { return @{ kind = 'write'; command = $command } }
        if ($command -match $readPattern) { return @{ kind = 'read'; command = $command } }
        return @{ kind = 'execute'; command = $command }
    }
    if ($ToolName -match '^(view_image|get_goal|list_mcp_resources|list_mcp_resource_templates|read_mcp_resource|codex_app__read_thread_terminal)$') {
        return @{ kind = 'read'; command = $command }
    }
    if ($ToolName -match '^mcp__' -or $ToolName -match '__') {
        if ($ToolName -match '(?i)(merge_pull_request|enable_auto_merge|deploy|release|promote)') { return @{ kind = 'external-write'; command = $command } }
        if ($ToolName -match '(?i)(create|update|edit)_pull_request|pull_request_(create|update|edit|comment|review)|create_pull_request_review|submit_pull_request_review|request_reviewers|add_(issue_)?comment') { return @{ kind = 'pr-write'; command = $command } }
        if ($ToolName -match '(?i)(^|__|_)(create|update|delete|remove|add|write|send|post|put|patch|merge|deploy|publish|approve|close|archive|move|copy|set|enable|disable|rerun|request)(_|$)') { return @{ kind = 'external-write'; command = $command } }
        if ($ToolName -match '(?i)(^|__)(get|list|read|search|find|status|inspect|view|query|fetch|open)(_|$)') { return @{ kind = 'read'; command = $command } }
        return @{ kind = 'external-write'; command = $command }
    }
    if ($ToolName -match '^(update_plan|request_user_input)$') { return @{ kind = 'coordination'; command = $command } }
    return @{ kind = 'execute'; command = $command }
}

function Get-ToolWorkdir {
    param([AllowNull()]$ToolInput, [Parameter(Mandatory)][string]$Fallback)
    if ($ToolInput -is [hashtable]) {
        foreach ($key in @('workdir', 'cwd')) {
            if ($ToolInput.ContainsKey($key) -and $ToolInput[$key]) { return [IO.Path]::GetFullPath([string]$ToolInput[$key]) }
        }
    }
    [IO.Path]::GetFullPath($Fallback)
}

function Get-PathStringComparison {
    if ($env:FIRST_PASS_QUALITY_FORCE_CASE_SENSITIVE -eq '1') { return [StringComparison]::Ordinal }
    if ([OperatingSystem]::IsWindows()) { return [StringComparison]::OrdinalIgnoreCase }
    [StringComparison]::Ordinal
}

function Test-PathWithinScope {
    param([Parameter(Mandatory)][string]$Candidate, [Parameter(Mandatory)][object[]]$Roots)
    $candidateFull = [IO.Path]::GetFullPath($Candidate).TrimEnd('\', '/')
    $comparison = Get-PathStringComparison
    foreach ($root in $Roots) {
        if (-not $root) { continue }
        $rootFull = [IO.Path]::GetFullPath([string]$root).TrimEnd('\', '/')
        if ($candidateFull.Equals($rootFull, $comparison)) { return $true }
        $prefix = $rootFull + [IO.Path]::DirectorySeparatorChar
        if ($candidateFull.StartsWith($prefix, $comparison)) { return $true }
    }
    $false
}

function Get-ApplyPatchFiles {
    param([AllowNull()]$ToolInput, [Parameter(Mandatory)][string]$Cwd)
    $text = ''
    $files = @()
    if ($ToolInput -is [hashtable]) {
        foreach ($key in @('file_path', 'filePath', 'path')) {
            if (-not $ToolInput.ContainsKey($key) -or -not $ToolInput[$key]) { continue }
            $value = [string]$ToolInput[$key]
            if (-not [IO.Path]::IsPathRooted($value)) { $value = Join-Path $Cwd $value }
            $files += [IO.Path]::GetFullPath($value)
        }
        foreach ($key in @('patch', 'input')) {
            if ($ToolInput.ContainsKey($key) -and $ToolInput[$key]) { $text = [string]$ToolInput[$key]; break }
        }
    } elseif ($ToolInput) { $text = [string]$ToolInput }
    foreach ($match in [regex]::Matches($text, '(?m)^\*\*\* (?:Update|Add|Delete) File:\s*(.+?)\s*$')) {
        $value = $match.Groups[1].Value.Trim()
        if (-not [IO.Path]::IsPathRooted($value)) { $value = Join-Path $Cwd $value }
        $files += [IO.Path]::GetFullPath($value)
    }
    foreach ($match in [regex]::Matches($text, '(?m)^\*\*\* Move to:\s*(.+?)\s*$')) {
        $value = $match.Groups[1].Value.Trim()
        if (-not [IO.Path]::IsPathRooted($value)) { $value = Join-Path $Cwd $value }
        $files += [IO.Path]::GetFullPath($value)
    }
    @($files | Select-Object -Unique)
}

function Get-DirtyFiles {
    param([Parameter(Mandatory)][string]$Cwd)
    try {
        $root = Get-GitRoot -Cwd $Cwd
        if (-not $root) { return @() }
        $items = @()
        foreach ($line in @(& git -C $root status --porcelain=v1 --untracked-files=all 2>$null)) {
            if ($line.Length -lt 4) { continue }
            $relative = $line.Substring(3).Trim()
            if ($relative -match ' -> ') { $relative = ($relative -split ' -> ')[-1] }
            $relative = $relative.Trim('"')
            $items += [IO.Path]::GetFullPath((Join-Path $root $relative))
        }
        @($items | Select-Object -Unique)
    } catch { @() }
}

function Get-RequiredAction {
    param([Parameter(Mandatory)][hashtable]$Classification)
    $command = [string]$Classification.command
    switch ([string]$Classification.kind) {
        'read' { 'read' }
        'write' { 'write' }
        'vcs-stage' { 'write' }
        'commit' { 'commit' }
        'push' { 'push' }
        'pr-write' { 'pr' }
        'validate' { 'validate' }
        'execute' { 'execute' }
        'delegation' { 'delegate' }
        'external-write' { 'production' }
        'production-shell' { 'production' }
        default { $null }
    }
}

function Test-ProductionLockMatches {
    param(
        [Parameter(Mandatory)][hashtable]$Lock,
        [Parameter(Mandatory)][string]$ToolName,
        [AllowNull()]$ToolInput
    )
    if ([string]$Lock.wrapperToolName -ne $ToolName) { return $false }
    $inputHash = Get-ToolInputHash $ToolInput
    if ([string]$Lock.expectedToolInputHash -ne $inputHash) { return $false }
    $actualStableId = Get-NestedValue -Value $ToolInput -Path ([string]$Lock.stableIdField)
    if ($null -eq $actualStableId -or (Get-Hash ([string]$actualStableId)) -ne [string]$Lock.stableIdHash) { return $false }
    if ($Lock.projectIdField) {
        $actualProjectId = Get-NestedValue -Value $ToolInput -Path ([string]$Lock.projectIdField)
        if ($null -eq $actualProjectId -or (Get-Hash ([string]$actualProjectId)) -ne [string]$Lock.projectIdHash) { return $false }
    }
    $true
}

function Get-ReadinessProblems {
    param([Parameter(Mandatory)][hashtable]$State)
    $problems = [Collections.Generic.List[string]]::new()
    if (-not $State.task) { $problems.Add('Task Lock is missing.') }
    if ($State.ContainsKey('failedWritePending') -and $State.failedWritePending) { $problems.Add('A failed write still requires recovery verification.') }
    if ($State.ContainsKey('delegation') -and $State.delegation -and -not $State.delegation.verified) { $problems.Add('Delegated work has not been independently verified by the parent.') }
    foreach ($name in @('clarification', 'context', 'risk')) {
        if ([string]$State.gates[$name] -ne 'passed') { $problems.Add("Gate '$name' is not passed.") }
    }
    if ([string]$State.gates.workflow -notin @('passed', 'not_required')) { $problems.Add('Workflow gate is not terminal-success.') }
    if ([string]$State.gates.publish -notin @('passed', 'not_required')) { $problems.Add('Publish gate is not terminal-success.') }
    if ([string]$State.gates.acceptance -ne 'passed') { $problems.Add('Acceptance gate is not passed.') }
    if ([string]$State.gates.selfReview -ne 'passed') { $problems.Add('Self-review gate is not passed.') }
    if ([string]$State.gates.review -notin @('passed', 'not_required')) { $problems.Add('Review gate is not terminal-success.') }
    if ($State.task) {
        foreach ($criterion in @($State.task.doneWhen)) {
            $latest = @($State.evidence | Where-Object {
                $_.criterionId -eq $criterion.id -and
                (-not $State.lastWriteAt -or [string]$_.observedAt -ge [string]$State.lastWriteAt)
            } | Sort-Object observedAt -Descending | Select-Object -First 1)
            if ($latest.Count -eq 0 -or [string]$latest[0].status -ne 'passed') { $problems.Add("Criterion '$($criterion.id)' has no passed evidence.") }
        }
        if ($State.lastWriteToolUseId) {
            $writeEvidence = @($State.evidence | Where-Object { $_.toolUseId -eq $State.lastWriteToolUseId -and $_.status -eq 'passed' })
            if ($writeEvidence.Count -eq 0) { $problems.Add('The latest write has no passed evidence bound to its tool use id.') }
        }
        if ($State.task.mode -eq 'production') {
            if (@($State.entityLocks | Where-Object { $_.intent -eq 'write' }).Count -eq 0) { $problems.Add('Production write Entity Lock is missing.') }
            if ($State.pendingProduction) { $problems.Add('Production outcome is still pending or unknown.') }
            if (-not $State.lastProduction -or $State.lastProduction.status -ne 'succeeded') { $problems.Add('No successful one-shot production result is recorded.') }
        }
    }
    @($problems)
}

function Get-ToolSuccess {
    param([AllowNull()]$Response)
    if ($null -eq $Response) { return $false }
    if ($Response -is [hashtable]) {
        foreach ($key in @('exit_code', 'exitCode')) {
            if ($Response.ContainsKey($key)) { return ([int]$Response[$key] -eq 0) }
        }
        if ($Response.ContainsKey('success')) { return [bool]$Response.success }
        if ($Response.ContainsKey('is_error')) { return -not [bool]$Response.is_error }
        if ($Response.ContainsKey('error') -and $Response.error) { return $false }
    }
    if ($Response -is [string]) {
        if ($Response -match '(?i)Exit\s+code:\s*(-?\d+)') { return ([int]$Matches[1] -eq 0) }
        if ($Response -match '(?i)\b(script|command|tool)\s+(failed|error)\b') { return $false }
    }
    $true
}

function Invoke-SessionStart {
    param([Parameter(Mandatory)][hashtable]$HookData, [Parameter(Mandatory)][string]$Root)
    $id = [string]$HookData.session_id
    Invoke-WithSessionLock -Id $id -Operation {
        $path = Get-StatePath -Root $Root -Id $id
        $state = Read-State $path
        if (-not $state) { $state = New-State $HookData }
        if ($HookData.ContainsKey('turn_id')) { $state.turnId = [string]$HookData.turn_id }
        $state.model = [string]$HookData.model
        $state.cwd = [string]$HookData.cwd
        Write-State -Path $path -State $state
        Set-CurrentSessionIndex -Root $Root -State $state
    }
    @{
        hookSpecificOutput = @{
            hookEventName = 'SessionStart'
            additionalContext = 'First-Pass Quality enforcement is active. Ask one clarification question for a new task, then create a Task Lock with $first-pass-quality-gate before any tool use.'
        }
    }
}

function Invoke-UserPromptSubmit {
    param([Parameter(Mandatory)][hashtable]$HookData, [Parameter(Mandatory)][string]$Root)
    $id = [string]$HookData.session_id
    $prompt = [string]$HookData.prompt
    $outputBox = @{ value = @{} }
    Invoke-WithSessionLock -Id $id -Operation {
        $path = Get-StatePath -Root $Root -Id $id
        $state = Read-State $path
        if (-not $state) { $state = New-State $HookData }
        if ([string]$state.status -in @('ready', 'partial', 'blocked', 'unknown')) {
            $previous = $state
            $state = New-State $HookData
            $state.phase = 'needs_task_decision'
            $state.previousTaskHash = if ($previous.task) { Get-Hash (($previous.task | ConvertTo-Json -Depth 12 -Compress)) } else { $null }
        }
        $state.turnId = [string]$HookData.turn_id
        $state.model = [string]$HookData.model
        $state.cwd = [string]$HookData.cwd
        $state.promptCount = [int]$state.promptCount + 1
        $state.confirmationCandidate = $false
        $state.confirmationTurnId = $null
        if ($state.task) {
            $state.task.productionAuthorized = $false
            $state.task.productionAuthorizationTurnIdHash = $null
        }
        $state.lastPromptHash = Get-Hash $prompt
        $state.lastPromptAt = Get-UtcNow
        $correction = $prompt -match '(?i)(опять|ошиб|не так|не туда|накосяч|ты не сделал|wrong|incorrect)'
        $stopCandidate = [regex]::Replace(
            $prompt,
            "(?i)\b(?:do\s+not|don['’]?t|never)\s+(?:please\s+)?(?:stop|pause)\b|(?i)(?:^|\s)не\s+(?:стоп|stop|pause|останавливайся|останавливай|прекращай)(?=\s|$)",
            ''
        )
        $stop = $stopCandidate -match '(?i)(^|\s)(стоп|оставь|не туда|pause|stop)(\s|$)'
        $confirm = $prompt -match '(?is)((подтверждаю|да,?\s*(выполняй|делай|запускай)|confirm(ed)?).{0,60}(production|продакш|боев)|(production|продакш|боев).{0,60}(подтверждаю|выполняй|делай|confirm|execute))'
        $delegationRequested = $prompt -match '(?is)(субагент|подагент|делегир|параллельн.*агент|subagent|delegate|spawn\s+agent)'
        $autoReview = $prompt -match '(?is)(monster|монстр).*(PR\s*#?\d+).*(base|head).*(checklist|чек)'
        if ($stop) {
            $state.stopOverride = $true
            $outputBox.value = @{ systemMessage = 'Art requested an immediate stop. Stop current work without another commit, push, mutation, or useful extra step.' }
        } elseif ($autoReview -and -not $state.task) {
            $state.autoReview = $true
            $state.clarified = $true
            $state.phase = 'clarified'
            $state.gates.clarification = 'passed'
            $outputBox.value = @{ hookSpecificOutput = @{ hookEventName = 'UserPromptSubmit'; additionalContext = 'Fully specified automated review detected. Create the review Task Lock now; do not ask the standard clarification question.' } }
        } elseif ($state.phase -eq 'awaiting_clarification' -and $state.clarificationAsked) {
            $state.clarified = $true
            $state.phase = 'clarified'
            $state.gates.clarification = 'passed'
            $outputBox.value = @{ hookSpecificOutput = @{ hookEventName = 'UserPromptSubmit'; additionalContext = 'Clarification answer received. Create a Task Lock with $first-pass-quality-gate before using tools.' } }
        } elseif ($state.task) {
            $state.contextConfirmed = $false
            $state.gates.context = 'pending'
            $outputBox.value = @{ hookSpecificOutput = @{ hookEventName = 'UserPromptSubmit'; additionalContext = 'New user input arrived during an active Task Lock. Reconcile whether it replaces, extends, or only asks status; run ConfirmContext before the next mutation.' } }
        } elseif ($state.phase -eq 'needs_task_decision') {
            $outputBox.value = @{ hookSpecificOutput = @{ hookEventName = 'UserPromptSubmit'; additionalContext = 'Decide whether this is a continuation. For a clarified continuation create a new Task Lock with -Continuation; otherwise ask one concise clarification question.' } }
        } else {
            $outputBox.value = @{ hookSpecificOutput = @{ hookEventName = 'UserPromptSubmit'; additionalContext = 'New task detected. Ask Art one concise clarification question and wait before using tools.' } }
        }
        if ($confirm) {
            $state.confirmationCandidate = $true
            $state.confirmationTurnId = [string]$HookData.turn_id
        }
        if ($delegationRequested) { $state.delegationCandidate = $true }
        Write-State -Path $path -State $state
        Set-CurrentSessionIndex -Root $Root -State $state
        Write-Telemetry -Root $Root -Record @{
            sessionId = $state.sessionId; turnId = $state.turnId; model = $state.model; cwd = $state.cwd
            event = 'UserPromptSubmit'; action = 'classify'; result = if ($stop) { 'stop' } elseif ($confirm) { 'confirm-candidate' } else { 'continue' }
            toolName = ''; phase = $state.phase; status = $state.status; risk = if ($state.task) { $state.task.risk } else { '' }
            userCorrectionDetected = $correction
        }
    }
    $outputBox.value
}

function Invoke-PreToolUse {
    param([Parameter(Mandatory)][hashtable]$HookData, [Parameter(Mandatory)][string]$Root, [switch]$DryRun)
    $id = [string]$HookData.session_id
    $toolName = [string]$HookData.tool_name
    $classification = Get-ToolClassification -ToolName $toolName -ToolInput $HookData.tool_input
    $decisionBox = @{ value = $null }
    Invoke-WithSessionLock -Id $id -Operation {
        $path = Get-StatePath -Root $Root -Id $id
        $state = Read-State $path
        if (-not $state) { $decisionBox.value = New-PreToolDeny 'Quality state is missing. Start a new task and create a Task Lock before tools.'; return }
        if ($state.stopOverride) { $decisionBox.value = New-PreToolDeny 'Art requested stop; no further tool use is allowed.'; return }
        if ($classification.kind -eq 'management') { return }
        if (-not $state.task) {
            $decisionBox.value = New-PreToolDeny 'Task Lock is missing. Ask the required clarification question, then run StartTask from $first-pass-quality-gate.'
            return
        }
        if ([string]$state.status -ne 'active') { $decisionBox.value = New-PreToolDeny "Task is already terminal ($($state.status)); start a new Task Lock before more tools."; return }
        $requiredAction = Get-RequiredAction -Classification $classification
        if ($requiredAction -and $requiredAction -notin @($state.task.allowedActions)) {
            $decisionBox.value = New-PreToolDeny "Task Lock does not allow action '$requiredAction'."; return
        }
        if ($classification.kind -in @('read', 'validate')) { return }
        if ([string]$HookData.permission_mode -eq 'plan' -and $classification.kind -notin @('coordination', 'read', 'validate')) {
            $decisionBox.value = New-PreToolDeny 'Plan permission mode does not allow implementation or side effects.'; return
        }
        if ($classification.kind -eq 'coordination') { return }
        if (-not $state.contextConfirmed -or $state.gates.context -ne 'passed') {
            $decisionBox.value = New-PreToolDeny 'Context gate is pending after new input or compaction. Run ConfirmContext first.'; return
        }
        if ($state.gates.workflow -notin @('passed', 'not_required')) {
            $decisionBox.value = New-PreToolDeny 'Workflow gate is not passed. Complete/review the required plan before implementation.'; return
        }
        if ($state.gates.risk -ne 'passed') { $decisionBox.value = New-PreToolDeny 'Risk gate is not passed.'; return }
        if ($state.task.mode -eq 'report-only') { $decisionBox.value = New-PreToolDeny 'Task mode is report-only; mutations and execution are not authorized.'; return }
        if ($classification.kind -in @('vcs-stage', 'commit', 'push', 'pr-write') -and $state.task.mode -ne 'pr') {
            $decisionBox.value = New-PreToolDeny 'Version-control publication actions require a PR Task Lock.'; return
        }
        if ($state.failedWritePending) { $decisionBox.value = New-PreToolDeny 'A previous write failed or has unknown outcome. Inspect current state and run AcknowledgeWriteRecovery before another mutation.'; return }
        if ($classification.kind -eq 'delegation') {
            if (-not $state.delegation) { $decisionBox.value = New-PreToolDeny 'Delegation is not authorized in the Task Lock. Run AuthorizeDelegation with bounded outcome and scope.'; return }
            if ($state.delegation.started -and -not $state.delegation.verified) { $decisionBox.value = New-PreToolDeny 'The existing delegated handoff is still awaiting parent verification.'; return }
            if (-not $DryRun) {
                $state.delegation.started = $true
                $state.delegation.verified = $false
                $state.delegation.toolUseId = [string]$HookData.tool_use_id
                Write-State -Path $path -State $state
            }
            return
        }
        if ($state.delegation -and $state.delegation.started -and -not $state.delegation.verified) {
            $decisionBox.value = New-PreToolDeny 'Parent verification of the delegated result is required before mutation.'; return
        }
        $workdir = Get-ToolWorkdir -ToolInput $HookData.tool_input -Fallback ([string]$HookData.cwd)
        if (-not (Test-PathWithinScope -Candidate $workdir -Roots @($state.task.scopePaths))) {
            $decisionBox.value = New-PreToolDeny "Tool workdir is outside the locked scope: $workdir"; return
        }
        if ($classification.kind -eq 'production-shell') {
            $decisionBox.value = New-PreToolDeny 'Direct production/merge/deploy shell mutation is forbidden. Use the exact registered MCP/API wrapper after Entity Lock and explicit confirmation.'; return
        }
        if ($classification.kind -eq 'external-write' -and $state.task.mode -ne 'production') {
            $decisionBox.value = New-PreToolDeny 'External writes require a production Task Lock, exact Entity Lock, and fresh confirmation.'; return
        }
        if ($classification.kind -eq 'external-write' -and $state.task.mode -eq 'production') {
            $locks = @($state.entityLocks)
            $matching = @($locks | Where-Object { $_.intent -eq 'write' -and (Test-ProductionLockMatches -Lock $_ -ToolName $toolName -ToolInput $HookData.tool_input) })
            if ($matching.Count -ne 1) { $decisionBox.value = New-PreToolDeny 'Production tool name, exact input, stable entity id, or project id does not match one unique Entity Lock.'; return }
            $inputHash = Get-ToolInputHash $HookData.tool_input
            $pendingMatches = $state.pendingProduction -and $state.pendingProduction.toolUseId -eq [string]$HookData.tool_use_id -and $state.pendingProduction.inputHash -eq $inputHash
            if (-not $state.task.productionAuthorized -and -not $pendingMatches) { $decisionBox.value = New-PreToolDeny 'Production operation lacks fresh one-shot confirmation bound to the latest user turn.'; return }
            if (-not $DryRun -and -not $pendingMatches) {
                $state.task.productionAuthorized = $false
                $state.pendingProduction = @{
                    toolUseId = [string]$HookData.tool_use_id
                    toolName = $toolName
                    inputHash = $inputHash
                    lockId = $matching[0].lockId
                    authorizedTurnIdHash = $state.task.productionAuthorizationTurnIdHash
                    startedAt = Get-UtcNow
                }
                Write-State -Path $path -State $state
            }
        }
        if ($classification.kind -eq 'external-write' -and $toolName -eq 'Bash') {
            $decisionBox.value = New-PreToolDeny 'Direct external mutation through shell is blocked. Use a dedicated typed tool/wrapper.'; return
        }
        if ($toolName -match '^(apply_patch|Edit|Write)$') {
            $files = Get-ApplyPatchFiles -ToolInput $HookData.tool_input -Cwd $workdir
            if (@($files).Count -eq 0) { $decisionBox.value = New-PreToolDeny 'No patch target could be parsed; scope cannot be enforced.'; return }
            foreach ($file in @($files)) {
                if (-not (Test-PathWithinScope -Candidate $file -Roots @($state.task.writeScopePaths))) {
                    $decisionBox.value = New-PreToolDeny "Patch target is outside the Task Lock write scope: $file"; return
                }
            }
            if (-not $state.task.allowDirty) {
                if (-not (Get-GitRoot -Cwd $workdir)) { $decisionBox.value = New-PreToolDeny 'Dirty overlap cannot be verified outside Git. Use -AllowDirty only when Art explicitly authorized editing this non-Git scope.'; return }
                $dirty = @(Get-DirtyFiles -Cwd $workdir)
                $pathComparison = Get-PathStringComparison
                foreach ($file in $files) {
                    $isDirty = @($dirty | Where-Object { $_.Equals($file, $pathComparison) }).Count -gt 0
                    $owned = @($state.agentChangedFiles | Where-Object { ([string]$_).Equals($file, $pathComparison) }).Count -gt 0
                    if ($isDirty -and -not $owned) { $decisionBox.value = New-PreToolDeny "Target file already has user changes and dirty overlap is not authorized: $file"; return }
                }
            }
        }
        $command = [string]$classification.command
        if ($toolName -eq 'Bash' -and $classification.kind -eq 'write' -and (Test-IsRawFileMutationCommand $command)) {
            $decisionBox.value = New-PreToolDeny 'Raw shell filesystem mutation cannot be scoped reliably. Use apply_patch/Edit/Write for local files.'; return
        }
        if ($classification.kind -in @('commit', 'push', 'pr-write')) {
            if ($state.gates.publish -ne 'passed' -or $state.gates.selfReview -ne 'passed') {
                $decisionBox.value = New-PreToolDeny 'Commit/push/PR publication requires passed pre-publish evidence and self-review gates.'; return
            }
        }
    }
    if ($decisionBox.value) {
        $stateForLog = Read-State (Get-StatePath -Root $Root -Id $id)
        Write-Telemetry -Root $Root -Record @{
            sessionId = $id; turnId = [string]$HookData.turn_id; model = [string]$HookData.model; cwd = [string]$HookData.cwd
            event = 'PreToolUse'; action = $classification.kind; result = 'denied'; toolName = $toolName
            phase = if ($stateForLog) { $stateForLog.phase } else { 'missing' }; status = if ($stateForLog) { $stateForLog.status } else { 'missing' }
            risk = if ($stateForLog -and $stateForLog.task) { $stateForLog.task.risk } else { '' }; userCorrectionDetected = $false
        }
    }
    $decisionBox.value
}

function Invoke-PostToolUse {
    param([Parameter(Mandatory)][hashtable]$HookData, [Parameter(Mandatory)][string]$Root)
    $id = [string]$HookData.session_id
    $toolName = [string]$HookData.tool_name
    $classification = Get-ToolClassification -ToolName $toolName -ToolInput $HookData.tool_input
    $success = Get-ToolSuccess $HookData.tool_response
    Invoke-WithSessionLock -Id $id -Operation {
        $path = Get-StatePath -Root $Root -Id $id
        $state = Read-State $path
        if (-not $state) { return }
        $state.tools.count = [int]$state.tools.count + 1
        if (-not $success) { $state.tools.failures = [int]$state.tools.failures + 1 }
        $responseHash = Get-Hash (($HookData.tool_response | ConvertTo-Json -Depth 12 -Compress))
        $state.lastTool = @{
            toolUseId = [string]$HookData.tool_use_id
            toolName = $toolName
            kind = $classification.kind
            success = $success
            observedAt = Get-UtcNow
            responseHash = $responseHash
        }
        $mutationKinds = @('write', 'vcs-stage', 'commit', 'push', 'pr-write', 'external-write', 'production-shell')
        if ($classification.kind -in $mutationKinds) {
            $state.tools.writes = [int]$state.tools.writes + 1
            if (-not $success) { $state.failedWritePending = $true }
        }
        if ($classification.kind -in @('write', 'external-write', 'production-shell')) {
            $state.lastWriteToolUseId = [string]$HookData.tool_use_id
            $state.lastWriteAt = Get-UtcNow
            $state.gates.publish = if ($state.task.mode -eq 'pr') { 'pending' } else { 'not_required' }
            $state.gates.acceptance = 'pending'
            $state.gates.selfReview = 'pending'
            if ($state.task.reviewRequired) { $state.gates.review = 'pending' }
            if ($success -and $toolName -match '^(apply_patch|Edit|Write)$') {
                $workdir = Get-ToolWorkdir -ToolInput $HookData.tool_input -Fallback ([string]$HookData.cwd)
                foreach ($file in @(Get-ApplyPatchFiles -ToolInput $HookData.tool_input -Cwd $workdir)) {
                    if ($file -notin @($state.agentChangedFiles)) { $state.agentChangedFiles += $file }
                }
            }
        }
        if ($success -and $classification.kind -eq 'push' -and $state.task.reviewRequired) {
            $state.gates.review = 'pending'
        }
        if ($classification.kind -eq 'delegation' -and $state.delegation) {
            $state.delegation.completed = $true
            $state.delegation.completedAt = Get-UtcNow
            $state.delegation.verified = $false
        }
        if ($classification.kind -eq 'external-write' -and $state.pendingProduction -and $state.pendingProduction.toolUseId -eq [string]$HookData.tool_use_id) {
            $state.lastProduction = @{
                toolUseId = [string]$HookData.tool_use_id
                toolName = $toolName
                inputHash = $state.pendingProduction.inputHash
                lockId = $state.pendingProduction.lockId
                status = if ($success) { 'succeeded' } else { 'failed_or_unknown' }
                observedAt = Get-UtcNow
            }
            $state.pendingProduction = $null
        }
        Write-State -Path $path -State $state
        Write-Telemetry -Root $Root -Record @{
            sessionId = $state.sessionId; turnId = [string]$HookData.turn_id; model = $state.model; cwd = $state.cwd
            event = 'PostToolUse'; action = $classification.kind; result = if ($success) { 'success' } else { 'failed' }; toolName = $toolName
            phase = $state.phase; status = $state.status; risk = if ($state.task) { $state.task.risk } else { '' }; userCorrectionDetected = $false
        }
    }
    if (-not $success) { return @{ systemMessage = 'The last tool call failed. Do not convert it into passed evidence or a readiness claim.' } }
    @{}
}

function Invoke-PreCompact {
    param([Parameter(Mandatory)][hashtable]$HookData, [Parameter(Mandatory)][string]$Root)
    $id = [string]$HookData.session_id
    Invoke-WithSessionLock -Id $id -Operation {
        $path = Get-StatePath -Root $Root -Id $id
        $state = Read-State $path
        if (-not $state) { return }
        $state.compaction.snapshotAt = Get-UtcNow
        $state.compaction.snapshotHash = Get-Hash (($state | ConvertTo-Json -Depth 20 -Compress))
        Write-State -Path $path -State $state
    }
    @{}
}

function Invoke-PostCompact {
    param([Parameter(Mandatory)][hashtable]$HookData, [Parameter(Mandatory)][string]$Root)
    $id = [string]$HookData.session_id
    $messageBox = @{ value = 'Quality state could not be restored; all mutations remain blocked.' }
    Invoke-WithSessionLock -Id $id -Operation {
        $path = Get-StatePath -Root $Root -Id $id
        $state = Read-State $path
        if (-not $state) { return }
        $state.compaction.count = [int]$state.compaction.count + 1
        $state.compaction.restoredAt = Get-UtcNow
        $state.contextConfirmed = $false
        $state.gates.context = if ($state.compaction.snapshotHash) { 'pending' } else { 'unknown' }
        $messageBox.value = "Task state restored after compaction. Outcome hash: $(if ($state.task) { (Get-Hash $state.task.outcome).Substring(0,12) } else { 'none' }); context gate is $($state.gates.context). Run ConfirmContext before mutation."
        Write-State -Path $path -State $state
    }
    @{ systemMessage = $messageBox.value }
}

function Invoke-PermissionRequest {
    param([Parameter(Mandatory)][hashtable]$HookData, [Parameter(Mandatory)][string]$Root)
    $preInput = @{}
    foreach ($key in $HookData.Keys) { $preInput[$key] = $HookData[$key] }
    if (-not $preInput.ContainsKey('tool_use_id')) { $preInput.tool_use_id = 'permission-request' }
    $deny = Invoke-PreToolUse -HookData $preInput -Root $Root -DryRun
    if ($deny) {
        $message = [string]$deny.hookSpecificOutput.permissionDecisionReason
        return New-PermissionDeny $message
    }
    @{}
}

function Invoke-SubagentStart {
    param([Parameter(Mandatory)][hashtable]$HookData, [Parameter(Mandatory)][string]$Root)
    $state = Read-State (Get-StatePath -Root $Root -Id ([string]$HookData.session_id))
    if (-not $state -or -not $state.delegation) {
        return @{ systemMessage = 'Subagent started without a bounded handoff. Treat its output as untrusted and do not mutate.' }
    }
    $context = "Bounded subagent handoff. Outcome: $($state.delegation.outcome). Scope: $($state.delegation.scope). Mode: $($state.task.mode). Authority is not expanded. End with all exact labels: OUTCOME:, EVIDENCE:, CHANGED_FILES:, LIMITATIONS:, PARENT_VERIFY:."
    @{ hookSpecificOutput = @{ hookEventName = 'SubagentStart'; additionalContext = $context } }
}

function Invoke-SubagentStop {
    param([Parameter(Mandatory)][hashtable]$HookData)
    $message = [string]$HookData.last_assistant_message
    foreach ($label in @('OUTCOME:', 'EVIDENCE:', 'CHANGED_FILES:', 'LIMITATIONS:', 'PARENT_VERIFY:')) {
        if ($message -notmatch ('(?im)^\s*' + [regex]::Escape($label))) {
            return New-StopBlock 'Return a structured handoff with exact labels OUTCOME:, EVIDENCE:, CHANGED_FILES:, LIMITATIONS:, and PARENT_VERIFY:.'
        }
    }
    @{}
}

function Invoke-Stop {
    param([Parameter(Mandatory)][hashtable]$HookData, [Parameter(Mandatory)][string]$Root)
    $id = [string]$HookData.session_id
    $outputBox = @{ value = @{} }
    Invoke-WithSessionLock -Id $id -Operation {
        $path = Get-StatePath -Root $Root -Id $id
        $state = Read-State $path
        if (-not $state) { $outputBox.value = New-StopBlock 'Quality state is missing. Reinitialize the task and create a Task Lock.'; return }
        if ($state.stopOverride) {
            if ($state.status -eq 'active') {
                $state.status = 'blocked'
                $state.terminal.reason = 'Stopped by Art.'
                $state.terminal.nextAction = 'Wait for Art.'
                $state.terminal.hardBlocker = $true
            }
            Write-State -Path $path -State $state
            return
        }
        $last = [string]$HookData.last_assistant_message
        if ($state.phase -eq 'awaiting_clarification') {
            if (Test-IsConciseClarification $last) {
                $state.clarificationAsked = $true
                Write-State -Path $path -State $state
                return
            }
            $outputBox.value = New-StopBlock 'Before tools or a substantive answer, ask Art one concise clarification question about the expected result.'
            return
        }
        if ($state.phase -eq 'needs_task_decision' -and -not $state.task) {
            if (Test-IsConciseClarification $last) {
                $state.phase = 'awaiting_clarification'
                $state.clarificationAsked = $true
                Write-State -Path $path -State $state
                return
            }
            $outputBox.value = New-StopBlock 'Decide the boundary: use StartTask -Continuation for an already clarified continuation, or ask one concise clarification question for a new task.'
            return
        }
        if (-not $state.task) { $outputBox.value = New-StopBlock 'Create a Task Lock with $first-pass-quality-gate before finishing the answer.'; return }
        if ($state.status -eq 'active') { $outputBox.value = New-StopBlock 'Set an explicit terminal quality status: ready, partial, blocked, or unknown. Active is not a final status.'; return }
        if ($state.status -eq 'ready') {
            $problems = @(Get-ReadinessProblems $state)
            if ($problems.Count -gt 0) { $outputBox.value = New-StopBlock ('Ready is not supported by evidence: ' + ($problems -join ' ')); return }
        }
        if ($state.status -in @('partial', 'blocked', 'unknown')) {
            if (-not $state.terminal.reason -or @($state.terminal.limitations).Count -eq 0 -or -not $state.terminal.nextAction) {
                $outputBox.value = New-StopBlock 'Partial/blocked/unknown requires a reason, limitations, and next action.'; return
            }
            if ($state.task.completionPolicy -eq 'wait-for-required-gates' -and -not $state.terminal.hardBlocker) {
                $outputBox.value = New-StopBlock 'This Task Lock requires waiting for required gates. Continue monitoring or mark a genuine hard blocker.'; return
            }
        }
        Write-Telemetry -Root $Root -Record @{
            sessionId = $state.sessionId; turnId = [string]$HookData.turn_id; model = $state.model; cwd = $state.cwd
            event = 'Stop'; action = 'completion'; result = $state.status; toolName = ''; phase = $state.phase; status = $state.status
            risk = $state.task.risk; userCorrectionDetected = $false
        }
    }
    $outputBox.value
}

function Invoke-Hook {
    $root = Get-DataRoot
    Initialize-DataRoot $root
    $raw = [Console]::In.ReadToEnd()
    if ([string]::IsNullOrWhiteSpace($raw)) { return }
    $hookData = $raw | ConvertFrom-Json -AsHashtable
    $event = [string]$hookData.hook_event_name
    try {
        $output = switch ($event) {
            'SessionStart' { Invoke-SessionStart -HookData $hookData -Root $root }
            'UserPromptSubmit' { Invoke-UserPromptSubmit -HookData $hookData -Root $root }
            'PreToolUse' { Invoke-PreToolUse -HookData $hookData -Root $root }
            'PermissionRequest' { Invoke-PermissionRequest -HookData $hookData -Root $root }
            'PostToolUse' { Invoke-PostToolUse -HookData $hookData -Root $root }
            'PreCompact' { Invoke-PreCompact -HookData $hookData -Root $root }
            'PostCompact' { Invoke-PostCompact -HookData $hookData -Root $root }
            'SubagentStart' { Invoke-SubagentStart -HookData $hookData -Root $root }
            'SubagentStop' { Invoke-SubagentStop -HookData $hookData }
            'Stop' { Invoke-Stop -HookData $hookData -Root $root }
            default { @{} }
        }
        Write-HookOutput $output
    } catch {
        $message = 'First-Pass Quality internal error: ' + (Get-NormalizedText $_.Exception.Message 300)
        $fail = switch ($event) {
            'PreToolUse' { New-PreToolDeny $message }
            'PermissionRequest' { New-PermissionDeny $message }
            'Stop' { New-StopBlock $message }
            'SubagentStop' { New-StopBlock $message }
            default { @{ systemMessage = $message } }
        }
        Write-HookOutput $fail
    }
}

function Invoke-StateAction {
    $root = Get-DataRoot
    Initialize-DataRoot $root
    $id = Get-SessionIdForAction -Root $root
    $resultBox = @{ value = $null }
    Invoke-WithSessionLock -Id $id -Operation {
        $path = Get-StatePath -Root $root -Id $id
        $state = Read-State $path
        if (-not $state) { throw 'Quality state is missing for this session.' }
        switch ($Action) {
            'StartTask' {
                if (-not $state.clarified -and -not $state.autoReview -and -not ($Continuation -and $state.phase -eq 'needs_task_decision')) {
                    throw 'Clarification gate is not passed. Ask Art one concise question and wait, or use -Continuation only for an already clarified continuation.'
                }
                if ($Mode -notin @('report-only', 'local-change', 'pr', 'production')) { throw 'Mode must be report-only, local-change, pr, or production.' }
                if ($Risk -notin @('low', 'medium', 'high')) { throw 'Risk must be low, medium, or high.' }
                if ($CompletionPolicy -notin @('deliver-current-state', 'wait-for-required-gates')) { throw 'Invalid completion policy.' }
                $criteriaText = @(Split-Values $DoneWhen)
                $prePublishText = @(Split-Values $PrePublishWhen)
                if (-not $Outcome -or $criteriaText.Count -eq 0) { throw 'Outcome and at least one DoneWhen criterion are required.' }
                $scopePaths = @(Split-Values $Scope)
                if ($scopePaths.Count -eq 0) { $scopePaths = @((Get-Location).Path) }
                $resolvedScope = @($scopePaths | ForEach-Object { [IO.Path]::GetFullPath($_) } | Select-Object -Unique)
                $writeScopePaths = @(Split-Values $WriteScope)
                if ($writeScopePaths.Count -eq 0) { $writeScopePaths = @($resolvedScope) }
                $resolvedWriteScope = @($writeScopePaths | ForEach-Object { [IO.Path]::GetFullPath($_) } | Select-Object -Unique)
                foreach ($writePath in $resolvedWriteScope) {
                    if (-not (Test-PathWithinScope -Candidate $writePath -Roots $resolvedScope)) { throw "WriteScope is outside Scope: $writePath" }
                }
                $criteria = @()
                for ($i = 0; $i -lt $criteriaText.Count; $i++) { $criteria += @{ id = ('C' + ($i + 1)); text = Get-NormalizedText $criteriaText[$i] 500 } }
                if ($Mode -eq 'pr' -and $prePublishText.Count -eq 0) { $prePublishText = @($criteriaText) }
                $prePublishCriteria = @()
                for ($i = 0; $i -lt $prePublishText.Count; $i++) { $prePublishCriteria += @{ id = ('P' + ($i + 1)); text = Get-NormalizedText $prePublishText[$i] 500 } }
                $workflowId = if ([string]::IsNullOrWhiteSpace($Workflow)) { 'none' } else { Get-NormalizedText $Workflow 80 }
                $workflowStageId = if ([string]::IsNullOrWhiteSpace($WorkflowStage)) { 'none' } else { Get-NormalizedText $WorkflowStage 80 }
                if ($workflowId -match '(?i)(^|[:/>,+\s-])feature($|[:/>,+\s-])' -and $workflowStageId -eq 'none') { throw 'Feature workflow requires an explicit WorkflowStage such as planning or implementation.' }
                $actions = @(Split-Values $AllowedActions)
                if ($actions.Count -eq 0) {
                    $actions = switch ($Mode) {
                        'report-only' { @('read', 'validate') }
                        'local-change' { @('read', 'write', 'execute', 'validate') }
                        'pr' { @('read', 'write', 'execute', 'validate', 'commit', 'push', 'pr') }
                        'production' { @('read', 'write', 'execute', 'validate', 'production') }
                    }
                }
                $validActions = @('read', 'write', 'execute', 'validate', 'commit', 'push', 'pr', 'production', 'delegate')
                $invalidActions = @($actions | Where-Object { $_ -notin $validActions })
                if ($invalidActions.Count -gt 0) { throw ('Invalid allowed action(s): ' + ($invalidActions -join ', ')) }
                if ($Mode -ne 'production' -and 'production' -in $actions) { throw 'The production action requires production mode.' }
                if ($Mode -ne 'pr' -and @($actions | Where-Object { $_ -in @('commit', 'push', 'pr') }).Count -gt 0) { throw 'Commit, push, and pr actions require pr mode.' }
                $reviewRequired = $Mode -eq 'pr' -or $workflowId -match '(?i)feature|deploy'
                $state.task = @{
                    outcome = Get-NormalizedText $Outcome 700
                    scopePaths = $resolvedScope
                    writeScopePaths = $resolvedWriteScope
                    outOfScope = @(Split-Values $OutOfScope)
                    mode = $Mode
                    risk = $Risk
                    completionPolicy = $CompletionPolicy
                    workflowId = $workflowId
                    workflowStage = $workflowStageId
                    allowedActions = $actions
                    allowDirty = [bool]$AllowDirty
                    doneWhen = $criteria
                    prePublishWhen = $prePublishCriteria
                    createdAt = Get-UtcNow
                    reviewRequired = [bool]$reviewRequired
                    authorityTurnIdHash = (Get-Hash ([string]$state.turnId)).Substring(0, 24)
                    productionAuthorized = $false
                    productionAuthorizationTurnIdHash = $null
                }
                $state.entityLocks = @()
                $state.evidence = @()
                $state.agentChangedFiles = @()
                $state.lastWriteToolUseId = $null
                $state.lastWriteAt = $null
                $state.failedWritePending = $false
                $state.pendingProduction = $null
                $state.lastProduction = $null
                $state.delegation = $null
                $state.clarified = $true
                $state.contextConfirmed = $true
                $state.phase = 'task_locked'
                $state.status = 'active'
                $state.stopOverride = $false
                $state.gates = @{
                    clarification = 'passed'
                    context = 'passed'
                    workflow = if ($workflowId -eq 'none') { 'not_required' } else { 'pending' }
                    risk = 'passed'
                    publish = if ($Mode -eq 'pr') { 'pending' } else { 'not_required' }
                    acceptance = 'pending'
                    selfReview = 'pending'
                    review = if ($reviewRequired) { 'pending' } else { 'not_required' }
                }
                $state.terminal = @{ reason = $null; limitations = @(); nextAction = $null; hardBlocker = $false }
                $resultBox.value = @{ action = 'StartTask'; sessionIdHash = (Get-Hash $id).Substring(0, 16); task = $state.task; gates = $state.gates }
            }
            'ConfirmContext' {
                if (-not $state.task) { throw 'Task Lock is missing.' }
                if ($ContextDisposition -notin @('unchanged', 'status-only')) { throw 'ContextDisposition must be unchanged or status-only. For replaced/extended scope, create a fresh Task Lock with -Continuation.' }
                if ([string]::IsNullOrWhiteSpace($ContextNote)) { throw 'ContextNote is required so the reconciliation is auditable.' }
                $state.contextConfirmed = $true
                $state.gates.context = 'passed'
                $state.contextHistory += @{
                    turnIdHash = (Get-Hash ([string]$state.turnId)).Substring(0, 24)
                    disposition = $ContextDisposition
                    noteHash = Get-Hash $ContextNote
                    confirmedAt = Get-UtcNow
                }
                $resultBox.value = @{ action = 'ConfirmContext'; status = 'passed'; disposition = $ContextDisposition }
            }
            'SetGate' {
                if ($Gate -notin @('workflow', 'publish', 'acceptance', 'selfReview', 'review')) { throw 'Gate must be workflow, publish, acceptance, selfReview, or review.' }
                if ($GateStatus -notin @('pending', 'passed', 'failed', 'not_required', 'unknown')) { throw 'Invalid gate status.' }
                if ($Gate -in @('publish', 'acceptance') -and $GateStatus -eq 'passed') {
                    $gateCriteria = if ($Gate -eq 'publish') { @($state.task.prePublishWhen) } else { @($state.task.doneWhen) }
                    foreach ($criterion in $gateCriteria) {
                        $latest = @($state.evidence | Where-Object {
                            $_.criterionId -eq $criterion.id -and
                            (-not $state.lastWriteAt -or [string]$_.observedAt -ge [string]$state.lastWriteAt)
                        } | Sort-Object observedAt -Descending | Select-Object -First 1)
                        if ($latest.Count -eq 0 -or $latest[0].status -ne 'passed') { throw "$Gate cannot pass: criterion $($criterion.id) lacks passed evidence." }
                    }
                }
                if ($Gate -eq 'selfReview' -and $GateStatus -eq 'passed' -and $state.gates.acceptance -ne 'passed' -and $state.gates.publish -ne 'passed') { throw 'Self-review cannot pass before acceptance or pre-publish evidence.' }
                if ($Gate -eq 'workflow' -and $GateStatus -eq 'not_required' -and $state.task.workflowId -ne 'none') { throw 'A named workflow cannot be changed to not_required.' }
                if ($Gate -eq 'publish' -and $GateStatus -eq 'not_required' -and $state.task.mode -eq 'pr') { throw 'A PR Task Lock cannot skip the publish gate.' }
                if ($Gate -eq 'review' -and $GateStatus -eq 'not_required' -and $state.task.reviewRequired) { throw 'Required review cannot be changed to not_required.' }
                $state.gates[$Gate] = $GateStatus
                $resultBox.value = @{ action = 'SetGate'; gate = $Gate; status = $GateStatus }
            }
            'SetEntityLock' {
                if (-not $state.task) { throw 'Task Lock is missing.' }
                if ($state.task.mode -ne 'production' -or $state.task.risk -ne 'high') { throw 'Entity Lock writes require a high-risk production Task Lock.' }
                if (-not $EntityType -or -not $StableId -or -not $Environment -or $Intent -notin @('read', 'write')) { throw 'EntityType, StableId, Environment, and Intent read/write are required.' }
                if ($Environment -ne 'production') { throw 'Production Task Locks require Environment production.' }
                if ($Intent -eq 'write' -and (-not $WrapperToolName -or -not $ExpectedBeforeHash -or -not $ChangeHash -or -not $StableIdField -or -not $ExpectedToolInputJson)) { throw 'A write Entity Lock requires wrapper name, before/change hashes, StableIdField, and exact ExpectedToolInputJson.' }
                if ($Intent -eq 'write' -and $WrapperToolName -notmatch '^(mcp__|codex_apps|[A-Za-z0-9_-]+__)') { throw 'Production wrapper must be a typed MCP/app tool name, not shell.' }
                if ($ProjectId -and -not $ProjectIdField) { throw 'ProjectIdField is required when ProjectId is supplied.' }
                $expectedInputHash = $null
                if ($Intent -eq 'write') {
                    try { $expectedInput = $ExpectedToolInputJson | ConvertFrom-Json -AsHashtable } catch { throw 'ExpectedToolInputJson must be valid JSON.' }
                    $inputStableId = Get-NestedValue -Value $expectedInput -Path $StableIdField
                    if ($null -eq $inputStableId -or [string]$inputStableId -ne $StableId) { throw 'StableIdField in ExpectedToolInputJson does not equal StableId.' }
                    if ($ProjectId) {
                        $inputProjectId = Get-NestedValue -Value $expectedInput -Path $ProjectIdField
                        if ($null -eq $inputProjectId -or [string]$inputProjectId -ne $ProjectId) { throw 'ProjectIdField in ExpectedToolInputJson does not equal ProjectId.' }
                    }
                    $expectedInputHash = Get-ToolInputHash $expectedInput
                    if (@($state.entityLocks | Where-Object { $_.wrapperToolName -eq $WrapperToolName -and $_.expectedToolInputHash -eq $expectedInputHash }).Count -gt 0) { throw 'An identical Entity Lock already exists.' }
                }
                $lock = @{
                    lockId = 'E' + (@($state.entityLocks).Count + 1)
                    type = Get-NormalizedText $EntityType 100
                    stableIdHash = Get-Hash $StableId
                    projectIdHash = Get-Hash $ProjectId
                    environment = Get-NormalizedText $Environment 80
                    intent = $Intent
                    wrapperToolName = Get-NormalizedText $WrapperToolName 180
                    stableIdField = Get-NormalizedText $StableIdField 180
                    projectIdField = Get-NormalizedText $ProjectIdField 180
                    expectedToolInputHash = $expectedInputHash
                    expectedBeforeHash = Get-Hash $ExpectedBeforeHash
                    changeHash = Get-Hash $ChangeHash
                    lockedAt = Get-UtcNow
                }
                $state.entityLocks += $lock
                $resultBox.value = @{ action = 'SetEntityLock'; lock = $lock }
            }
            'AuthorizeProduction' {
                if (-not $state.task -or $state.task.mode -ne 'production') { throw 'Production authorization requires a production Task Lock.' }
                if (-not $state.contextConfirmed -or $state.gates.context -ne 'passed') { throw 'Confirm the latest context before production authorization.' }
                if (-not $state.confirmationCandidate -or -not $state.confirmationTurnId) { throw 'No explicit user confirmation was detected in the latest prompt.' }
                if ([string]$state.confirmationTurnId -ne [string]$state.turnId) { throw 'Production confirmation is stale; it must be in the latest prompt.' }
                if (@($state.entityLocks | Where-Object { $_.intent -eq 'write' }).Count -eq 0) { throw 'A write Entity Lock must exist before production authorization.' }
                if ($state.pendingProduction) { throw 'A production operation is already pending or has unknown outcome.' }
                $state.task.productionAuthorized = $true
                $state.task.productionAuthorizationTurnIdHash = (Get-Hash ([string]$state.confirmationTurnId)).Substring(0, 24)
                $state.confirmationCandidate = $false
                $resultBox.value = @{ action = 'AuthorizeProduction'; authorized = $true; confirmationTurnIdHash = $state.task.productionAuthorizationTurnIdHash }
            }
            'AddEvidence' {
                if (-not $state.task) { throw 'Task Lock is missing.' }
                if ($EvidenceStatus -notin @('passed', 'failed', 'unavailable', 'unknown')) { throw 'EvidenceStatus must be passed, failed, unavailable, or unknown.' }
                $allCriteria = @($state.task.doneWhen) + @($state.task.prePublishWhen)
                if (-not @($allCriteria | Where-Object { $_.id -eq $CriterionId }).Count) { throw "Unknown criterion id: $CriterionId" }
                if ([string]::IsNullOrWhiteSpace($Validator) -or [string]::IsNullOrWhiteSpace($Subject)) { throw 'Validator and Subject are required.' }
                if ($EvidenceStatus -eq 'passed') {
                    if (-not $state.lastTool -or -not $state.lastTool.success) { throw 'Passed evidence must bind to a successful observed tool call.' }
                    if ([string]::IsNullOrWhiteSpace($ExpectedToolName) -or $ExpectedToolName -ne [string]$state.lastTool.toolName) { throw 'ExpectedToolName must exactly match the latest successful tool.' }
                    if ([string]$state.lastTool.kind -notin @('read', 'write', 'execute', 'validate', 'vcs-stage', 'commit', 'push', 'pr-write', 'external-write')) { throw 'Management, coordination, and delegation calls cannot serve as acceptance evidence.' }
                    if ([string]$state.lastTool.observedAt -lt [string]$state.task.createdAt) { throw 'Evidence tool result predates the current Task Lock.' }
                }
                $entry = @{
                    criterionId = $CriterionId
                    validator = Get-NormalizedText $Validator 160
                    status = $EvidenceStatus
                    subjectHash = Get-Hash $Subject
                    toolUseId = if ($state.lastTool) { $state.lastTool.toolUseId } else { $null }
                    toolName = if ($state.lastTool) { $state.lastTool.toolName } else { $null }
                    responseHash = if ($state.lastTool) { $state.lastTool.responseHash } else { $null }
                    observedAt = if ($state.lastTool) { $state.lastTool.observedAt } else { Get-UtcNow }
                }
                $state.evidence += $entry
                $resultBox.value = @{ action = 'AddEvidence'; evidence = $entry }
            }
            'SetStatus' {
                if (-not $state.task) { throw 'Task Lock is missing.' }
                if ($FinalStatus -notin @('ready', 'partial', 'blocked', 'unknown')) { throw 'FinalStatus must be ready, partial, blocked, or unknown.' }
                if ($FinalStatus -eq 'ready') {
                    $problems = @(Get-ReadinessProblems $state)
                    if ($problems.Count -gt 0) { throw ('Cannot set ready: ' + ($problems -join ' ')) }
                } else {
                    if (-not $Reason -or @(Split-Values $Limitations).Count -eq 0 -or -not $NextAction) { throw 'Partial/blocked/unknown requires Reason, at least one Limitation, and NextAction.' }
                    if ($state.task.completionPolicy -eq 'wait-for-required-gates' -and -not $HardBlocker) { throw 'wait-for-required-gates requires -HardBlocker for a non-ready terminal status.' }
                }
                $state.status = $FinalStatus
                $state.phase = 'terminal'
                $state.terminal = @{
                    reason = Get-NormalizedText $Reason 600
                    limitations = @(Split-Values $Limitations)
                    nextAction = Get-NormalizedText $NextAction 600
                    hardBlocker = [bool]$HardBlocker
                }
                $resultBox.value = @{ action = 'SetStatus'; status = $FinalStatus; terminal = $state.terminal }
            }
            'AuthorizeDelegation' {
                if (-not $state.task) { throw 'Task Lock is missing.' }
                if (-not $DelegationOutcome -or -not $DelegationScope) { throw 'DelegationOutcome and DelegationScope are required.' }
                if ('delegate' -notin @($state.task.allowedActions)) { throw 'The Task Lock does not allow delegation.' }
                if (-not $state.delegationCandidate) { throw 'The latest user prompt does not explicitly authorize delegation.' }
                if ($state.delegation -and -not $state.delegation.verified) { throw 'Existing delegated work must be verified before another delegation.' }
                $state.delegation = @{
                    outcome = Get-NormalizedText $DelegationOutcome 500
                    scope = Get-NormalizedText $DelegationScope 500
                    authorizedAt = Get-UtcNow
                    authorityTurnIdHash = (Get-Hash ([string]$state.turnId)).Substring(0, 24)
                    started = $false
                    completed = $false
                    verified = $false
                    toolUseId = $null
                    completedAt = $null
                    verifiedAt = $null
                }
                $state.delegationCandidate = $false
                $resultBox.value = @{ action = 'AuthorizeDelegation'; delegation = $state.delegation }
            }
            'VerifyDelegation' {
                if (-not $state.delegation -or -not $state.delegation.completed) { throw 'No completed delegated handoff is awaiting verification.' }
                if ([string]::IsNullOrWhiteSpace($DelegationEvidence)) { throw 'DelegationEvidence is required.' }
                if (-not $state.lastTool -or -not $state.lastTool.success -or [string]$state.lastTool.kind -notin @('read', 'execute', 'validate')) { throw 'Parent verification requires a successful non-delegated read, execution, or validator tool result.' }
                if ([string]$state.lastTool.observedAt -lt [string]$state.delegation.completedAt) { throw 'Parent verification tool result predates the delegated handoff.' }
                $state.delegation.verified = $true
                $state.delegation.verifiedAt = Get-UtcNow
                $state.delegation.verificationHash = Get-Hash $DelegationEvidence
                $state.delegation.verificationToolUseId = $state.lastTool.toolUseId
                $resultBox.value = @{ action = 'VerifyDelegation'; verified = $true; toolUseId = $state.lastTool.toolUseId }
            }
            'AcknowledgeWriteRecovery' {
                if (-not $state.failedWritePending) { throw 'No failed write is awaiting recovery.' }
                if ([string]::IsNullOrWhiteSpace($Reason)) { throw 'Reason is required for write recovery.' }
                if (-not $state.lastTool -or -not $state.lastTool.success -or [string]$state.lastTool.kind -notin @('read', 'validate')) { throw 'Write recovery requires a successful read or validator result.' }
                if ([string]$state.lastTool.observedAt -lt [string]$state.lastWriteAt) { throw 'Recovery evidence predates the failed write.' }
                $state.failedWritePending = $false
                $state.writeRecovery = @{ reasonHash = Get-Hash $Reason; toolUseId = $state.lastTool.toolUseId; recoveredAt = Get-UtcNow }
                $resultBox.value = @{ action = 'AcknowledgeWriteRecovery'; recovered = $true; toolUseId = $state.lastTool.toolUseId }
            }
            'ShowStatus' { $resultBox.value = $state }
            'ResetTask' {
                if ($state.status -notin @('ready', 'partial', 'blocked', 'unknown') -and -not $state.stopOverride) { throw 'An active task cannot be reset without a terminal status or stop override.' }
                $state = New-State @{ session_id = $id; turn_id = $state.turnId; model = $state.model; cwd = $state.cwd }
                $resultBox.value = @{ action = 'ResetTask'; phase = $state.phase }
            }
        }
        Write-State -Path $path -State $state
        Set-CurrentSessionIndex -Root $root -State $state
    }
    $resultBox.value | ConvertTo-Json -Depth 20
}

if ($Action -eq 'Hook') {
    Invoke-Hook
} elseif ($Action -eq 'Version') {
    @{ policyVersion = $script:PolicyVersion; schemaVersion = $script:SchemaVersion; codexContract = '0.144.3' } | ConvertTo-Json
} else {
    Invoke-StateAction
}
