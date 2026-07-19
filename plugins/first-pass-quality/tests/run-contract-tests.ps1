[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$pluginRoot = Split-Path -Parent $PSScriptRoot
$control = Join-Path $pluginRoot 'skills/first-pass-quality-gate/scripts/quality-control.ps1'
$pwsh = (Get-Command pwsh -ErrorAction Stop).Source
$tempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
$testRoot = Join-Path $tempRoot ('first-pass-quality-contract-' + [guid]::NewGuid().ToString('N'))
$workspace = Join-Path $testRoot 'workspace'
$script:Assertions = 0

function Assert-True {
    param([bool]$Condition, [string]$Message)
    $script:Assertions++
    if (-not $Condition) { throw "Assertion failed: $Message" }
}

function Invoke-HookCase {
    param([hashtable]$Event)
    $json = $Event | ConvertTo-Json -Depth 16 -Compress
    $psi = [Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $pwsh
    foreach ($arg in @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $control, '-Action', 'Hook')) {
        [void]$psi.ArgumentList.Add($arg)
    }
    $psi.RedirectStandardInput = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.StandardInputEncoding = [Text.UTF8Encoding]::new($false)
    $psi.StandardOutputEncoding = [Text.UTF8Encoding]::new($false)
    $psi.StandardErrorEncoding = [Text.UTF8Encoding]::new($false)
    $process = [Diagnostics.Process]::Start($psi)
    $process.StandardInput.Write($json)
    $process.StandardInput.Close()
    $text = $process.StandardOutput.ReadToEnd().Trim()
    $errorText = $process.StandardError.ReadToEnd().Trim()
    $process.WaitForExit()
    if ($process.ExitCode -ne 0) { throw "Hook process failed for $($Event.hook_event_name): $errorText" }
    if (-not $text) { return $null }
    $text | ConvertFrom-Json -AsHashtable
}

function Invoke-StateCase {
    param([string]$Session, [string[]]$Arguments, [switch]$ExpectFailure)
    $previousThread = $env:CODEX_THREAD_ID
    $env:CODEX_THREAD_ID = $Session
    try {
        $output = @(& $pwsh -NoProfile -ExecutionPolicy Bypass -File $control @Arguments 2>&1)
        $code = $LASTEXITCODE
        if ($ExpectFailure) {
            Assert-True ($code -ne 0) "State action should fail: $($Arguments -join ' ')"
            return $null
        }
        if ($code -ne 0) { throw "State action failed: $($output -join [Environment]::NewLine)" }
        $text = ($output -join [Environment]::NewLine).Trim()
        if ($text) { return ($text | ConvertFrom-Json -AsHashtable) }
        $null
    } finally {
        if ($null -eq $previousThread) { Remove-Item Env:CODEX_THREAD_ID -ErrorAction SilentlyContinue } else { $env:CODEX_THREAD_ID = $previousThread }
    }
}

function New-BaseEvent {
    param([string]$Session, [string]$Turn, [string]$Event)
    @{
        session_id = $Session
        turn_id = $Turn
        transcript_path = $null
        cwd = $workspace
        hook_event_name = $Event
        model = 'contract-model'
        permission_mode = 'default'
    }
}

function Initialize-ClarifiedSession {
    param([string]$Session)
    $start = New-BaseEvent $Session 't0' 'SessionStart'
    $start.Remove('turn_id')
    $start.source = 'startup'
    $result = Invoke-HookCase $start
    Assert-True ($result.hookSpecificOutput.hookEventName -eq 'SessionStart') 'SessionStart must return typed context.'

    $prompt = New-BaseEvent $Session 't1' 'UserPromptSubmit'
    $prompt.prompt = 'Сделай проверяемое изменение.'
    $null = Invoke-HookCase $prompt

    $pre = New-BaseEvent $Session 't1' 'PreToolUse'
    $pre.tool_name = 'Bash'
    $pre.tool_input = @{ command = 'Get-Content README.md'; workdir = $workspace }
    $pre.tool_use_id = 'pre-clarification-read'
    $denied = Invoke-HookCase $pre
    Assert-True ($denied.hookSpecificOutput.permissionDecision -eq 'deny') 'Tools must be denied before clarification.'

    $stop = New-BaseEvent $Session 't1' 'Stop'
    $stop.stop_hook_active = $false
    $stop.last_assistant_message = 'Какой итог должен считаться готовым?'
    $allowedQuestion = Invoke-HookCase $stop
    Assert-True ($null -eq $allowedQuestion) 'A single clarification question must be allowed to finish.'

    $answer = New-BaseEvent $Session 't2' 'UserPromptSubmit'
    $answer.prompt = 'Готово, когда файл изменён и тесты прошли.'
    $clarified = Invoke-HookCase $answer
    Assert-True ($clarified.hookSpecificOutput.additionalContext -match 'Task Lock') 'Clarification answer must request Task Lock.'
}

try {
    New-Item -ItemType Directory -Path $workspace -Force | Out-Null
    $env:FIRST_PASS_QUALITY_TEST_DATA = $testRoot
    Assert-True ((Get-Content -LiteralPath $control -Raw) -match '--diff-filter=ACDMRTUXB') 'Staged-index discovery must include deleted files.'

    $management = 'contract-management-bootstrap'
    Initialize-ClarifiedSession $management
    $managementCall = New-BaseEvent $management 't2' 'PreToolUse'
    $managementCall.tool_name = 'Bash'
    $managementCall.tool_input = @{
        command = '& "$($env:PLUGIN_ROOT ?? $env:CLAUDE_PLUGIN_ROOT)/skills/first-pass-quality-gate/scripts/quality-control.ps1" -Action StartTask -Outcome test'
        workdir = $workspace
    }
    $managementCall.tool_use_id = 'management-start-task'
    Assert-True ($null -eq (Invoke-HookCase $managementCall)) 'The documented one-line StartTask command must bypass the missing-lock gate as management.'
    $managementCall.tool_input.command = 'pwsh -NoProfile -File "$PLUGIN_ROOT/skills/first-pass-quality-gate/scripts/quality-control.ps1" -Action StartTask -Outcome test'
    $managementCall.tool_use_id = 'management-posix-start-task'
    Assert-True ($null -eq (Invoke-HookCase $managementCall)) 'The documented POSIX pwsh StartTask command must bypass the missing-lock gate as management.'
    $managementCall.tool_input.command = '& "$($env:PLUGIN_ROOT ?? $env:CLAUDE_PLUGIN_ROOT)/skills/first-pass-quality-gate/scripts/quality-control.ps1" -Action StartTask -Outcome test'
    $managementCall.tool_input.command += '; Remove-Item outside.txt'
    $managementCall.tool_use_id = 'management-chained-command'
    Assert-True ((Invoke-HookCase $managementCall).hookSpecificOutput.permissionDecision -eq 'deny') 'A chained command must not inherit management bypass.'
    $managementCall.tool_input.command = '& "skills/first-pass-quality-gate/scripts/quality-control.ps1" -Action StartTask -Outcome test'
    $managementCall.tool_use_id = 'management-relative-lookalike'
    Assert-True ((Invoke-HookCase $managementCall).hookSpecificOutput.permissionDecision -eq 'deny') 'A relative look-alike controller path must not receive management bypass.'
    $managementLookalike = Join-Path $testRoot 'first-pass-quality/skills/first-pass-quality-gate/scripts/quality-control.ps1'
    $managementCall.tool_input.command = "& `"$managementLookalike`" -Action StartTask -Outcome test"
    $managementCall.tool_use_id = 'management-absolute-lookalike'
    Assert-True ((Invoke-HookCase $managementCall).hookSpecificOutput.permissionDecision -eq 'deny') 'An absolute look-alike controller path outside the plugin root must not receive management bypass.'
    $managementCall.tool_input.command = '& "$($env:PLUGIN_ROOT ?? $env:CLAUDE_PLUGIN_ROOT)/skills/first-pass-quality-gate/scripts/quality-control.ps1.evil" -Action StartTask -Outcome test'
    $managementCall.tool_use_id = 'management-powershell-suffix-lookalike'
    Assert-True ((Invoke-HookCase $managementCall).hookSpecificOutput.permissionDecision -eq 'deny') 'A suffixed PowerShell controller look-alike must not receive management bypass.'
    $managementCall.tool_input.command = 'pwsh -NoProfile -File "$PLUGIN_ROOT/skills/first-pass-quality-gate/scripts/quality-control.ps1.evil" -Action StartTask -Outcome test'
    $managementCall.tool_use_id = 'management-posix-suffix-lookalike'
    Assert-True ((Invoke-HookCase $managementCall).hookSpecificOutput.permissionDecision -eq 'deny') 'A suffixed POSIX controller look-alike must not receive management bypass.'

    $session = 'contract-local'
    Initialize-ClarifiedSession $session
    $startTask = Invoke-StateCase $session @(
        '-Action', 'StartTask', '-Outcome', 'Create a verified local file', '-Scope', $workspace,
        '-Mode', 'local-change', '-Risk', 'medium', '-CompletionPolicy', 'deliver-current-state',
        '-Workflow', 'none', '-DoneWhen', 'file changed~~tests pass', '-AllowDirty'
    )
    Assert-True ($startTask.gates.workflow -eq 'not_required') 'No-workflow task must use not_required.'

    $preWrite = New-BaseEvent $session 't2' 'PreToolUse'
    $preWrite.tool_name = 'apply_patch'
    $preWrite.tool_input = @{ patch = "*** Begin Patch`n*** Add File: result.txt`n+ok`n*** End Patch"; workdir = $workspace }
    $preWrite.tool_use_id = 'write-1'
    $preWriteDecision = Invoke-HookCase $preWrite
    Assert-True ($null -eq $preWriteDecision) ('In-scope patch must be allowed after Task Lock. Decision: ' + ($preWriteDecision | ConvertTo-Json -Depth 8 -Compress))

    $claudeEdit = New-BaseEvent $session 't2' 'PreToolUse'
    $claudeEdit.tool_name = 'Edit'; $claudeEdit.tool_input = @{ file_path = (Join-Path $workspace 'result.txt'); old_string = 'old'; new_string = 'new' }; $claudeEdit.tool_use_id = 'claude-edit'
    Assert-True ($null -eq (Invoke-HookCase $claudeEdit)) 'Claude Edit with an in-scope file_path must be allowed.'
    $claudeWrite = New-BaseEvent $session 't2' 'PreToolUse'
    $claudeWrite.tool_name = 'Write'; $claudeWrite.tool_input = @{ file_path = (Join-Path $workspace 'nested/result.txt'); content = 'new' }; $claudeWrite.tool_use_id = 'claude-write'
    Assert-True ($null -eq (Invoke-HookCase $claudeWrite)) 'Claude Write with an in-scope file_path must be allowed.'
    $claudeOutside = New-BaseEvent $session 't2' 'PreToolUse'
    $claudeOutside.tool_name = 'Edit'; $claudeOutside.tool_input = @{ file_path = (Join-Path $testRoot 'outside.txt'); old_string = 'old'; new_string = 'new' }; $claudeOutside.tool_use_id = 'claude-edit-outside'
    Assert-True ((Invoke-HookCase $claudeOutside).hookSpecificOutput.permissionDecision -eq 'deny') 'Claude Edit must not escape the locked write scope.'

    $moveGuard = 'contract-move-scope'
    Initialize-ClarifiedSession $moveGuard
    $docsScope = Join-Path $workspace 'docs'
    New-Item -ItemType Directory -Path $docsScope -Force | Out-Null
    $null = Invoke-StateCase $moveGuard @(
        '-Action', 'StartTask', '-Outcome', 'Move only inside docs', '-Scope', $workspace, '-WriteScope', $docsScope,
        '-Mode', 'local-change', '-Risk', 'medium', '-CompletionPolicy', 'deliver-current-state',
        '-Workflow', 'none', '-DoneWhen', 'plan moved', '-AllowDirty'
    )
    $moveOutside = New-BaseEvent $moveGuard 't2' 'PreToolUse'
    $moveOutside.tool_name = 'apply_patch'
    $moveOutsidePatch = @'
*** Begin Patch
*** Update File: docs/plan.md
*** Move to: outside.md
@@
-old
+new
*** End Patch
'@
    $moveOutside.tool_input = @{ patch = $moveOutsidePatch; workdir = $workspace }
    $moveOutside.tool_use_id = 'move-outside-write-scope'
    Assert-True ((Invoke-HookCase $moveOutside).hookSpecificOutput.permissionDecision -eq 'deny') 'apply_patch Move to destinations must remain inside WriteScope.'
    $moveInside = New-BaseEvent $moveGuard 't2' 'PreToolUse'
    $moveInside.tool_name = 'apply_patch'
    $moveInsidePatch = @'
*** Begin Patch
*** Update File: docs/plan.md
*** Move to: docs/renamed.md
@@
-old
+new
*** End Patch
'@
    $moveInside.tool_input = @{ patch = $moveInsidePatch; workdir = $workspace }
    $moveInside.tool_use_id = 'move-inside-write-scope'
    Assert-True ($null -eq (Invoke-HookCase $moveInside)) 'An in-scope apply_patch move must remain allowed.'

    $caseGuard = 'contract-case-sensitive-scope'
    Initialize-ClarifiedSession $caseGuard
    $caseScope = Join-Path $workspace 'case-scope'
    New-Item -ItemType Directory -Path $caseScope -Force | Out-Null
    $null = Invoke-StateCase $caseGuard @(
        '-Action', 'StartTask', '-Outcome', 'Respect exact path casing', '-Scope', $workspace, '-WriteScope', $caseScope,
        '-Mode', 'local-change', '-Risk', 'medium', '-CompletionPolicy', 'deliver-current-state',
        '-Workflow', 'none', '-DoneWhen', 'case boundary enforced', '-AllowDirty'
    )
    $casePatch = New-BaseEvent $caseGuard 't2' 'PreToolUse'
    $casePatch.tool_name = 'apply_patch'
    $casePatchText = @'
*** Begin Patch
*** Add File: CASE-SCOPE/result.txt
+wrong case
*** End Patch
'@
    $casePatch.tool_input = @{ patch = $casePatchText; workdir = $workspace }
    $casePatch.tool_use_id = 'case-sensitive-outside'
    $env:FIRST_PASS_QUALITY_FORCE_CASE_SENSITIVE = '1'
    try {
        Assert-True ((Invoke-HookCase $casePatch).hookSpecificOutput.permissionDecision -eq 'deny') 'Case-sensitive runtimes must not equate differently-cased scope paths.'
    } finally {
        Remove-Item Env:FIRST_PASS_QUALITY_FORCE_CASE_SENSITIVE -ErrorAction SilentlyContinue
    }

    $reparseGuard = 'contract-reparse-scope'
    Initialize-ClarifiedSession $reparseGuard
    $null = Invoke-StateCase $reparseGuard @(
        '-Action', 'StartTask', '-Outcome', 'Reject reparse escapes', '-Scope', $workspace, '-WriteScope', $workspace,
        '-Mode', 'local-change', '-Risk', 'medium', '-CompletionPolicy', 'deliver-current-state',
        '-Workflow', 'none', '-DoneWhen', 'reparse boundary enforced', '-AllowDirty'
    )
    $reparsePatch = New-BaseEvent $reparseGuard 't2' 'PreToolUse'
    $reparsePatch.tool_name = 'apply_patch'
    $reparsePatch.tool_input = @{ patch = "*** Begin Patch`n*** Add File: linked-out/escape.txt`n+outside`n*** End Patch"; workdir = $workspace }
    $reparsePatch.tool_use_id = 'reparse-component-outside'
    $env:FIRST_PASS_QUALITY_TEST_REPARSE_COMPONENT = Join-Path $workspace 'linked-out'
    try {
        Assert-True ((Invoke-HookCase $reparsePatch).hookSpecificOutput.permissionDecision -eq 'deny') 'A path through a symlink or junction component must not pass lexical WriteScope checks.'
    } finally {
        Remove-Item Env:FIRST_PASS_QUALITY_TEST_REPARSE_COMPONENT -ErrorAction SilentlyContinue
    }

    $postWrite = New-BaseEvent $session 't2' 'PostToolUse'
    $postWrite.tool_name = 'apply_patch'
    $postWrite.tool_input = $preWrite.tool_input
    $postWrite.tool_response = @{ success = $true }
    $postWrite.tool_use_id = 'write-1'
    $null = Invoke-HookCase $postWrite

    $null = Invoke-StateCase $session @('-Action', 'AddEvidence', '-CriterionId', 'C1', '-Validator', 'patch-result', '-EvidenceStatus', 'passed', '-Subject', 'result.txt', '-ExpectedToolName', 'apply_patch')
    $preTest = New-BaseEvent $session 't2' 'PreToolUse'
    $preTest.tool_name = 'Bash'; $preTest.tool_input = @{ command = '.\tests\run-contract-tests.ps1'; workdir = $workspace }; $preTest.tool_use_id = 'test-1'
    Assert-True ($null -eq (Invoke-HookCase $preTest)) 'Validator command must be allowed.'
    $postTest = New-BaseEvent $session 't2' 'PostToolUse'
    $postTest.tool_name = 'Bash'; $postTest.tool_input = $preTest.tool_input; $postTest.tool_response = @{ exit_code = 0 }; $postTest.tool_use_id = 'test-1'
    $null = Invoke-HookCase $postTest
    $null = Invoke-StateCase $session @('-Action', 'AddEvidence', '-CriterionId', 'C2', '-Validator', 'contract-test', '-EvidenceStatus', 'passed', '-Subject', 'contract', '-ExpectedToolName', 'Bash')
    $null = Invoke-StateCase $session @('-Action', 'SetGate', '-Gate', 'acceptance', '-GateStatus', 'passed')
    $null = Invoke-StateCase $session @('-Action', 'SetGate', '-Gate', 'selfReview', '-GateStatus', 'passed')
    $null = Invoke-StateCase $session @('-Action', 'SetStatus', '-FinalStatus', 'ready')

    $readyStop = New-BaseEvent $session 't2' 'Stop'
    $readyStop.stop_hook_active = $false
    $readyStop.last_assistant_message = 'Готово: критерии и проверки подтверждены.'
    Assert-True ($null -eq (Invoke-HookCase $readyStop)) 'Evidence-backed ready must be allowed.'
    Assert-True ((Invoke-HookCase $preTest).hookSpecificOutput.permissionDecision -eq 'deny') 'No tools may run after a terminal status.'

    $incomplete = 'contract-incomplete'
    Initialize-ClarifiedSession $incomplete
    $null = Invoke-StateCase $incomplete @(
        '-Action', 'StartTask', '-Outcome', 'Incomplete task', '-Scope', $workspace,
        '-Mode', 'local-change', '-Risk', 'medium', '-CompletionPolicy', 'deliver-current-state',
        '-Workflow', 'none', '-DoneWhen', 'must pass', '-AllowDirty'
    )
    $null = Invoke-StateCase $incomplete @('-Action', 'SetStatus', '-FinalStatus', 'ready') -ExpectFailure
    $activeStop = New-BaseEvent $incomplete 't2' 'Stop'
    $activeStop.stop_hook_active = $false
    $activeStop.last_assistant_message = 'Готово.'
    $blockedReady = Invoke-HookCase $activeStop
    Assert-True ($blockedReady.decision -eq 'block') 'False-ready must be blocked.'
    $null = Invoke-StateCase $incomplete @('-Action', 'SetStatus', '-FinalStatus', 'partial', '-Reason', 'Validator unavailable', '-NextAction', 'Run visual validator') -ExpectFailure
    $null = Invoke-StateCase $incomplete @('-Action', 'SetStatus', '-FinalStatus', 'partial', '-Reason', 'Validator unavailable', '-Limitations', 'visual layer', '-NextAction', 'Run visual validator')
    Assert-True ($null -eq (Invoke-HookCase $activeStop)) 'Honest partial status must be allowed for deliver-current-state.'

    $compact = 'contract-compact'
    Initialize-ClarifiedSession $compact
    $null = Invoke-StateCase $compact @(
        '-Action', 'StartTask', '-Outcome', 'Compaction-safe task', '-Scope', $workspace,
        '-Mode', 'local-change', '-Risk', 'medium', '-CompletionPolicy', 'deliver-current-state',
        '-Workflow', 'none', '-DoneWhen', 'state restored', '-AllowDirty'
    )
    $preCompact = New-BaseEvent $compact 't2' 'PreCompact'; $preCompact.trigger = 'auto'
    $postCompact = New-BaseEvent $compact 't2' 'PostCompact'; $postCompact.trigger = 'auto'
    $null = Invoke-HookCase $preCompact
    $restore = Invoke-HookCase $postCompact
    Assert-True ($restore.systemMessage -match 'ConfirmContext') 'PostCompact must require context confirmation.'
    $compactWrite = New-BaseEvent $compact 't2' 'PreToolUse'
    $compactWrite.tool_name = 'apply_patch'; $compactWrite.tool_input = $preWrite.tool_input; $compactWrite.tool_use_id = 'compact-write'
    Assert-True ((Invoke-HookCase $compactWrite).hookSpecificOutput.permissionDecision -eq 'deny') 'Write must be blocked after compaction.'
    $null = Invoke-StateCase $compact @('-Action', 'ConfirmContext', '-ContextDisposition', 'unchanged', '-ContextNote', 'Task Lock survived compaction unchanged.')
    Assert-True ($null -eq (Invoke-HookCase $compactWrite)) 'Write must resume after ConfirmContext.'

    $production = 'contract-production'
    Initialize-ClarifiedSession $production
    $null = Invoke-StateCase $production @(
        '-Action', 'StartTask', '-Outcome', 'Typed production mutation', '-Scope', $workspace,
        '-Mode', 'production', '-Risk', 'high', '-CompletionPolicy', 'deliver-current-state',
        '-Workflow', 'none', '-DoneWhen', 'target changed'
    )
    $shellProd = New-BaseEvent $production 't2' 'PreToolUse'
    $shellProd.tool_name = 'Bash'; $shellProd.tool_input = @{ command = 'kubectl apply -f release.yaml'; workdir = $workspace }; $shellProd.tool_use_id = 'prod-shell'
    Assert-True ((Invoke-HookCase $shellProd).hookSpecificOutput.permissionDecision -eq 'deny') 'Direct production shell mutation must be blocked.'

    $typedProd = New-BaseEvent $production 't2' 'PreToolUse'
    $typedProd.tool_name = 'mcp__prod__write'; $typedProd.tool_input = @{ entity = '42'; project = '7'; value = 'new' }; $typedProd.tool_use_id = 'prod-typed'
    Assert-True ((Invoke-HookCase $typedProd).hookSpecificOutput.permissionDecision -eq 'deny') 'Production wrapper must be blocked before Entity Lock.'
    $null = Invoke-StateCase $production @(
        '-Action', 'SetEntityLock', '-EntityType', 'counterparty', '-StableId', '42', '-ProjectId', '7',
        '-Environment', 'production', '-Intent', 'write', '-WrapperToolName', 'mcp__prod__write',
        '-ExpectedBeforeHash', 'before', '-ChangeHash', 'change', '-StableIdField', 'entity', '-ProjectIdField', 'project',
        '-ExpectedToolInputJson', '{"entity":"42","project":"7","value":"new"}'
    )
    $wrongTyped = $typedProd.Clone(); $wrongTyped.tool_use_id = 'prod-wrong'; $wrongTyped.tool_input = @{ entity = '43'; project = '7'; value = 'new' }
    Assert-True ((Invoke-HookCase $wrongTyped).hookSpecificOutput.permissionDecision -eq 'deny') 'Entity Lock must reject a different stable id or input.'
    $negativeConfirm = New-BaseEvent $production 't3-negative' 'UserPromptSubmit'; $negativeConfirm.prompt = 'Не подтверждаю выполнение в production.'
    $null = Invoke-HookCase $negativeConfirm
    $negativeConfirmState = Invoke-StateCase $production @('-Action', 'ShowStatus')
    Assert-True (-not [bool]$negativeConfirmState.confirmationCandidate) 'A negated production confirmation must not create an authorization candidate.'
    $confirm = New-BaseEvent $production 't3' 'UserPromptSubmit'
    $confirm.prompt = 'Подтверждаю выполнение в production.'
    $null = Invoke-HookCase $confirm
    $statusPrompt = New-BaseEvent $production 't4' 'UserPromptSubmit'; $statusPrompt.prompt = 'Покажи статус без выполнения.'
    $null = Invoke-HookCase $statusPrompt
    $null = Invoke-StateCase $production @('-Action', 'ConfirmContext', '-ContextDisposition', 'status-only', '-ContextNote', 'Status request does not authorize production.')
    $null = Invoke-StateCase $production @('-Action', 'AuthorizeProduction') -ExpectFailure
    $confirm = New-BaseEvent $production 't5' 'UserPromptSubmit'; $confirm.prompt = 'Подтверждаю выполнение в production.'
    $null = Invoke-HookCase $confirm
    $null = Invoke-StateCase $production @('-Action', 'ConfirmContext', '-ContextDisposition', 'unchanged', '-ContextNote', 'Exact Entity Lock and production operation remain unchanged.')
    $null = Invoke-StateCase $production @('-Action', 'AuthorizeProduction')
    Assert-True ($null -eq (Invoke-HookCase $typedProd)) 'Matching typed production wrapper must be allowed after confirmation.'
    $repeatProd = $typedProd.Clone(); $repeatProd.tool_use_id = 'prod-repeat'
    Assert-True ((Invoke-HookCase $repeatProd).hookSpecificOutput.permissionDecision -eq 'deny') 'Production confirmation must be one-shot and reject replay.'

    $delegation = 'contract-delegation'
    Initialize-ClarifiedSession $delegation
    $null = Invoke-StateCase $delegation @(
        '-Action', 'StartTask', '-Outcome', 'Bounded delegation', '-Scope', $workspace,
        '-Mode', 'local-change', '-Risk', 'medium', '-CompletionPolicy', 'deliver-current-state',
        '-Workflow', 'none', '-DoneWhen', 'handoff verified', '-AllowedActions', 'read~~write~~execute~~validate~~delegate', '-AllowDirty'
    )
    $agentCall = New-BaseEvent $delegation 't2' 'PreToolUse'
    $agentCall.tool_name = 'Agent'; $agentCall.tool_input = @{ task = 'inspect' }; $agentCall.tool_use_id = 'agent-1'
    Assert-True ((Invoke-HookCase $agentCall).hookSpecificOutput.permissionDecision -eq 'deny') 'Unbounded delegation must be blocked.'
    $null = Invoke-StateCase $delegation @('-Action', 'AuthorizeDelegation', '-DelegationOutcome', 'Inspect one file', '-DelegationScope', $workspace) -ExpectFailure
    $delegatePrompt = New-BaseEvent $delegation 't3' 'UserPromptSubmit'; $delegatePrompt.prompt = 'Используй одного субагента только для проверки файла.'
    $null = Invoke-HookCase $delegatePrompt
    $null = Invoke-StateCase $delegation @('-Action', 'ConfirmContext', '-ContextDisposition', 'unchanged', '-ContextNote', 'Delegation was already included in the bounded task outcome.')
    $null = Invoke-StateCase $delegation @('-Action', 'AuthorizeDelegation', '-DelegationOutcome', 'Inspect one file', '-DelegationScope', $workspace)
    Assert-True ($null -eq (Invoke-HookCase $agentCall)) 'Bounded delegation must be allowed.'
    $postAgent = New-BaseEvent $delegation 't3' 'PostToolUse'; $postAgent.tool_name = 'Agent'; $postAgent.tool_input = $agentCall.tool_input; $postAgent.tool_response = @{ success = $true }; $postAgent.tool_use_id = 'agent-1'
    $null = Invoke-HookCase $postAgent
    $delegationWrite = New-BaseEvent $delegation 't3' 'PreToolUse'; $delegationWrite.tool_name = 'apply_patch'; $delegationWrite.tool_input = $preWrite.tool_input; $delegationWrite.tool_use_id = 'delegation-write'
    Assert-True ((Invoke-HookCase $delegationWrite).hookSpecificOutput.permissionDecision -eq 'deny') 'Mutation must wait for parent verification after delegation.'
    $parentRead = New-BaseEvent $delegation 't3' 'PostToolUse'; $parentRead.tool_name = 'Bash'; $parentRead.tool_input = @{ command = 'Get-Content result.txt'; workdir = $workspace }; $parentRead.tool_response = @{ exit_code = 0 }; $parentRead.tool_use_id = 'parent-read'
    $null = Invoke-HookCase $parentRead
    $null = Invoke-StateCase $delegation @('-Action', 'VerifyDelegation', '-DelegationEvidence', 'Parent inspected the delegated result.')
    Assert-True ($null -eq (Invoke-HookCase $delegationWrite)) 'Mutation may resume only after parent verification.'

    $badHandoff = New-BaseEvent $delegation 't3' 'SubagentStop'; $badHandoff.last_assistant_message = 'Done.'
    Assert-True ((Invoke-HookCase $badHandoff).decision -eq 'block') 'Subagent handoff must use the required structure.'
    $goodHandoff = New-BaseEvent $delegation 't3' 'SubagentStop'; $goodHandoff.last_assistant_message = "OUTCOME:`nchecked`nEVIDENCE:`nfile`nCHANGED_FILES:`nnone`nLIMITATIONS:`nnone`nPARENT_VERIFY:`nfile"
    Assert-True ($null -eq (Invoke-HookCase $goodHandoff)) 'Structured subagent handoff must be allowed.'

    $dirtyGuard = 'contract-dirty-guard'
    Initialize-ClarifiedSession $dirtyGuard
    $null = Invoke-StateCase $dirtyGuard @(
        '-Action', 'StartTask', '-Outcome', 'Safe non-Git edit', '-Scope', $workspace,
        '-Mode', 'local-change', '-Risk', 'medium', '-CompletionPolicy', 'deliver-current-state',
        '-Workflow', 'none', '-DoneWhen', 'file changed'
    )
    $dirtyWrite = New-BaseEvent $dirtyGuard 't2' 'PreToolUse'; $dirtyWrite.tool_name = 'apply_patch'; $dirtyWrite.tool_input = $preWrite.tool_input; $dirtyWrite.tool_use_id = 'dirty-write'
    Assert-True ((Invoke-HookCase $dirtyWrite).hookSpecificOutput.permissionDecision -eq 'deny') 'Non-Git writes must fail closed without explicit AllowDirty.'

    $actionGuard = 'contract-actions'
    Initialize-ClarifiedSession $actionGuard
    $null = Invoke-StateCase $actionGuard @(
        '-Action', 'StartTask', '-Outcome', 'Read and validate only', '-Scope', $workspace,
        '-Mode', 'local-change', '-Risk', 'medium', '-CompletionPolicy', 'deliver-current-state',
        '-Workflow', 'none', '-DoneWhen', 'report produced', '-AllowedActions', 'read~~validate', '-AllowDirty'
    )
    $actionWrite = New-BaseEvent $actionGuard 't2' 'PreToolUse'; $actionWrite.tool_name = 'apply_patch'; $actionWrite.tool_input = $preWrite.tool_input; $actionWrite.tool_use_id = 'action-write'
    Assert-True ((Invoke-HookCase $actionWrite).hookSpecificOutput.permissionDecision -eq 'deny') 'AllowedActions must mechanically block an unauthorized write.'
    $getOrCreate = New-BaseEvent $actionGuard 't2' 'PreToolUse'; $getOrCreate.tool_name = 'mcp__crm__get_or_create_customer'; $getOrCreate.tool_input = @{ id = '42' }; $getOrCreate.tool_use_id = 'get-or-create'
    Assert-True ((Invoke-HookCase $getOrCreate).hookSpecificOutput.permissionDecision -eq 'deny') 'get_or_create must be classified as an external write, not a read.'
    $ghApiRead = New-BaseEvent $actionGuard 't2' 'PreToolUse'; $ghApiRead.tool_name = 'Bash'; $ghApiRead.tool_input = @{ command = 'gh api repos/o/r/pulls/1'; workdir = $workspace }; $ghApiRead.tool_use_id = 'gh-api-read'
    Assert-True ($null -eq (Invoke-HookCase $ghApiRead)) 'Default GET gh api calls must remain readable.'
    $ghApiWrite = New-BaseEvent $actionGuard 't2' 'PreToolUse'; $ghApiWrite.tool_name = 'Bash'; $ghApiWrite.tool_input = @{ command = 'gh api repos/o/r/issues/1 -X PATCH -f title=changed'; workdir = $workspace }; $ghApiWrite.tool_use_id = 'gh-api-write'
    Assert-True ((Invoke-HookCase $ghApiWrite).hookSpecificOutput.permissionDecision -eq 'deny') 'Mutating gh api calls must not be misclassified as reads.'

    $shellGuard = 'contract-shell-classification'
    Initialize-ClarifiedSession $shellGuard
    $null = Invoke-StateCase $shellGuard @(
        '-Action', 'StartTask', '-Outcome', 'Allow execution but block unscoped mutations', '-Scope', $workspace,
        '-Mode', 'local-change', '-Risk', 'medium', '-CompletionPolicy', 'deliver-current-state',
        '-Workflow', 'none', '-DoneWhen', 'classification enforced', '-AllowedActions', 'read~~write~~execute~~validate', '-AllowDirty'
    )
    foreach ($case in @(
        @{ id = 'rm'; command = 'rm result.txt' },
        @{ id = 'mv'; command = 'mv old.txt new.txt' },
        @{ id = 'cp'; command = 'cp source.txt copy.txt' },
        @{ id = 'mkdir'; command = 'mkdir output' },
        @{ id = 'touch'; command = 'touch created.txt' },
        @{ id = 'sed'; command = 'sed -i.bak s/old/new/ result.txt' }
    )) {
        $event = New-BaseEvent $shellGuard 't2' 'PreToolUse'
        $event.tool_name = 'Bash'; $event.tool_input = @{ command = $case.command; workdir = $workspace }; $event.tool_use_id = "posix-$($case.id)"
        Assert-True ((Invoke-HookCase $event).hookSpecificOutput.permissionDecision -eq 'deny') "POSIX mutation '$($case.command)' must not fall through as execute."
    }
    $curlData = New-BaseEvent $shellGuard 't2' 'PreToolUse'; $curlData.tool_name = 'Bash'; $curlData.tool_input = @{ command = "curl -d '{}' https://api.example/items"; workdir = $workspace }; $curlData.tool_use_id = 'curl-data'
    Assert-True ((Invoke-HookCase $curlData).hookSpecificOutput.permissionDecision -eq 'deny') 'curl -d must be classified as an external write.'
    $curlJson = New-BaseEvent $shellGuard 't2' 'PreToolUse'; $curlJson.tool_name = 'Bash'; $curlJson.tool_input = @{ command = 'curl --json @body.json https://api.example/items'; workdir = $workspace }; $curlJson.tool_use_id = 'curl-json'
    Assert-True ((Invoke-HookCase $curlJson).hookSpecificOutput.permissionDecision -eq 'deny') 'curl --json must be classified as an external write.'
    $curlAttachedMethod = New-BaseEvent $shellGuard 't2' 'PreToolUse'; $curlAttachedMethod.tool_name = 'Bash'; $curlAttachedMethod.tool_input = @{ command = 'curl -XPOST https://api.example/items'; workdir = $workspace }; $curlAttachedMethod.tool_use_id = 'curl-attached-method'
    Assert-True ((Invoke-HookCase $curlAttachedMethod).hookSpecificOutput.permissionDecision -eq 'deny') 'curl -XPOST must be classified as an external write.'
    $curlHead = New-BaseEvent $shellGuard 't2' 'PreToolUse'; $curlHead.tool_name = 'Bash'; $curlHead.tool_input = @{ command = 'curl -I https://api.example/items'; workdir = $workspace }; $curlHead.tool_use_id = 'curl-head'
    Assert-True ($null -eq (Invoke-HookCase $curlHead)) 'A curl header read without data or a mutating method must remain executable.'
    $ghFieldWrite = New-BaseEvent $shellGuard 't2' 'PreToolUse'; $ghFieldWrite.tool_name = 'Bash'; $ghFieldWrite.tool_input = @{ command = 'gh api repos/o/r/issues/1/comments -f body=hello'; workdir = $workspace }; $ghFieldWrite.tool_use_id = 'gh-field-write'
    Assert-True ((Invoke-HookCase $ghFieldWrite).hookSpecificOutput.permissionDecision -eq 'deny') 'gh api fields without explicit GET must be classified as an external write.'
    $ghFieldRead = New-BaseEvent $shellGuard 't2' 'PreToolUse'; $ghFieldRead.tool_name = 'Bash'; $ghFieldRead.tool_input = @{ command = 'gh api repos/o/r/issues/1 --method GET -f per_page=1'; workdir = $workspace }; $ghFieldRead.tool_use_id = 'gh-field-get'
    Assert-True ($null -eq (Invoke-HookCase $ghFieldRead)) 'gh api fields with explicit GET must remain readable.'
    foreach ($case in @(
        @{ id = 'reset-hard'; command = 'git reset --hard HEAD' },
        @{ id = 'clean-force'; command = 'git clean -fd' }
    )) {
        $event = New-BaseEvent $shellGuard 't2' 'PreToolUse'; $event.tool_name = 'Bash'; $event.tool_input = @{ command = $case.command; workdir = $workspace }; $event.tool_use_id = $case.id
        Assert-True ((Invoke-HookCase $event).hookSpecificOutput.permissionDecision -eq 'deny') "Destructive Git command '$($case.command)' must be denied."
    }
    foreach ($case in @(
        @{ id = 'gh-release-create'; command = 'gh release create v1.2.3' },
        @{ id = 'gh-workflow-run'; command = 'gh workflow run deploy.yml' },
        @{ id = 'gh-secret-set'; command = 'gh secret set TOKEN' }
    )) {
        $event = New-BaseEvent $shellGuard 't2' 'PreToolUse'; $event.tool_name = 'Bash'; $event.tool_input = @{ command = $case.command; workdir = $workspace }; $event.tool_use_id = $case.id
        Assert-True ((Invoke-HookCase $event).hookSpecificOutput.permissionDecision -eq 'deny') "Non-PR GitHub mutation '$($case.command)' must require production authorization."
    }
    $updateBranchOutsidePr = New-BaseEvent $shellGuard 't2' 'PreToolUse'; $updateBranchOutsidePr.tool_name = 'Bash'; $updateBranchOutsidePr.tool_input = @{ command = 'gh pr update-branch 23'; workdir = $workspace }; $updateBranchOutsidePr.tool_use_id = 'gh-pr-update-branch-outside-pr'
    Assert-True ((Invoke-HookCase $updateBranchOutsidePr).hookSpecificOutput.permissionDecision -eq 'deny') 'gh pr update-branch must not run outside a PR Task Lock.'
    $readThenWrite = New-BaseEvent $shellGuard 't2' 'PreToolUse'; $readThenWrite.tool_name = 'Bash'; $readThenWrite.tool_input = @{ command = 'Get-Content result.txt; gh release create v1.2.3'; workdir = $workspace }; $readThenWrite.tool_use_id = 'read-then-write-chain'
    Assert-True ((Invoke-HookCase $readThenWrite).hookSpecificOutput.permissionDecision -eq 'deny') 'A command starting as a read must not hide a chained mutation.'

    $freshness = 'contract-freshness'
    Initialize-ClarifiedSession $freshness
    $null = Invoke-StateCase $freshness @(
        '-Action', 'StartTask', '-Outcome', 'Fresh evidence after final write', '-Scope', $workspace,
        '-Mode', 'local-change', '-Risk', 'medium', '-CompletionPolicy', 'deliver-current-state',
        '-Workflow', 'none', '-DoneWhen', 'file changed~~tests pass', '-AllowDirty'
    )
    $freshWrite = New-BaseEvent $freshness 't2' 'PostToolUse'; $freshWrite.tool_name = 'apply_patch'; $freshWrite.tool_input = $preWrite.tool_input; $freshWrite.tool_response = @{ success = $true }; $freshWrite.tool_use_id = 'fresh-write-1'
    $null = Invoke-HookCase $freshWrite
    $null = Invoke-StateCase $freshness @('-Action', 'AddEvidence', '-CriterionId', 'C1', '-Validator', 'patch', '-EvidenceStatus', 'passed', '-Subject', 'file', '-ExpectedToolName', 'apply_patch')
    $freshTest = New-BaseEvent $freshness 't2' 'PostToolUse'; $freshTest.tool_name = 'Bash'; $freshTest.tool_input = @{ command = '.\tests\run-contract-tests.ps1'; workdir = $workspace }; $freshTest.tool_response = @{ exit_code = 0 }; $freshTest.tool_use_id = 'fresh-test-1'
    $null = Invoke-HookCase $freshTest
    $null = Invoke-StateCase $freshness @('-Action', 'AddEvidence', '-CriterionId', 'C2', '-Validator', 'test', '-EvidenceStatus', 'passed', '-Subject', 'suite', '-ExpectedToolName', 'Bash')
    $null = Invoke-StateCase $freshness @('-Action', 'SetGate', '-Gate', 'acceptance', '-GateStatus', 'passed')
    $freshWrite.tool_use_id = 'fresh-write-2'; $null = Invoke-HookCase $freshWrite
    $null = Invoke-StateCase $freshness @('-Action', 'SetGate', '-Gate', 'acceptance', '-GateStatus', 'passed') -ExpectFailure

    $recovery = 'contract-write-recovery'
    Initialize-ClarifiedSession $recovery
    $null = Invoke-StateCase $recovery @(
        '-Action', 'StartTask', '-Outcome', 'Recover from failed write', '-Scope', $workspace,
        '-Mode', 'local-change', '-Risk', 'medium', '-CompletionPolicy', 'deliver-current-state',
        '-Workflow', 'none', '-DoneWhen', 'write recovered', '-AllowDirty'
    )
    $failedWrite = New-BaseEvent $recovery 't2' 'PostToolUse'; $failedWrite.tool_name = 'apply_patch'; $failedWrite.tool_input = $preWrite.tool_input; $failedWrite.tool_response = @{ success = $false }; $failedWrite.tool_use_id = 'failed-write'
    $null = Invoke-HookCase $failedWrite
    $retryWrite = New-BaseEvent $recovery 't2' 'PreToolUse'; $retryWrite.tool_name = 'apply_patch'; $retryWrite.tool_input = $preWrite.tool_input; $retryWrite.tool_use_id = 'retry-write'
    Assert-True ((Invoke-HookCase $retryWrite).hookSpecificOutput.permissionDecision -eq 'deny') 'A failed write must block another mutation.'
    $recoveryRead = New-BaseEvent $recovery 't2' 'PostToolUse'; $recoveryRead.tool_name = 'Bash'; $recoveryRead.tool_input = @{ command = 'Get-Content result.txt'; workdir = $workspace }; $recoveryRead.tool_response = @{ exit_code = 0 }; $recoveryRead.tool_use_id = 'recovery-read'
    $null = Invoke-HookCase $recoveryRead
    $null = Invoke-StateCase $recovery @('-Action', 'AcknowledgeWriteRecovery', '-Reason', 'Parent inspected the current file state after failure.')
    Assert-True ($null -eq (Invoke-HookCase $retryWrite)) 'Mutation may resume after explicit recovery evidence.'

    $prFlow = 'contract-feature-pr'
    Initialize-ClarifiedSession $prFlow
    $null = Invoke-StateCase $prFlow @(
        '-Action', 'StartTask', '-Outcome', 'Invalid feature task without a stage', '-Scope', $workspace,
        '-Mode', 'pr', '-Risk', 'medium', '-CompletionPolicy', 'wait-for-required-gates',
        '-Workflow', 'feature', '-DoneWhen', 'must fail', '-AllowDirty'
    ) -ExpectFailure
    $planFile = Join-Path $workspace 'docs/plan-feature.md'
    $prTask = Invoke-StateCase $prFlow @(
        '-Action', 'StartTask', '-Outcome', 'Publish and review a planning-only feature PR', '-Scope', $workspace,
        '-WriteScope', $planFile, '-Mode', 'pr', '-Risk', 'medium', '-CompletionPolicy', 'wait-for-required-gates',
        '-Workflow', 'feature', '-WorkflowStage', 'planning', '-PrePublishWhen', 'plan validated',
        '-DoneWhen', 'planning PR published and reviewed', '-AllowDirty'
    )
    Assert-True ($prTask.task.workflowId -eq 'feature') 'Feature Task Lock must preserve the selected project workflow.'
    Assert-True ($prTask.task.workflowStage -eq 'planning') 'Feature Task Lock must record its workflow stage.'
    Assert-True ($prTask.gates.publish -eq 'pending') 'PR Task Lock must start with a pending publish gate.'
    $null = Invoke-StateCase $prFlow @('-Action', 'SetGate', '-Gate', 'workflow', '-GateStatus', 'passed')

    $wrongPlanWrite = New-BaseEvent $prFlow 't2' 'PreToolUse'; $wrongPlanWrite.tool_name = 'apply_patch'; $wrongPlanWrite.tool_input = $preWrite.tool_input; $wrongPlanWrite.tool_use_id = 'wrong-plan-write'
    Assert-True ((Invoke-HookCase $wrongPlanWrite).hookSpecificOutput.permissionDecision -eq 'deny') 'Planning write scope must block production-code or unrelated file edits.'
    $planPatch = New-BaseEvent $prFlow 't2' 'PreToolUse'; $planPatch.tool_name = 'apply_patch'; $planPatch.tool_input = @{ patch = "*** Begin Patch`n*** Add File: docs/plan-feature.md`n+# Plan`n*** End Patch"; workdir = $workspace }; $planPatch.tool_use_id = 'plan-write'
    Assert-True ($null -eq (Invoke-HookCase $planPatch)) 'Planning write scope must allow the exact plan document.'
    $planPost = New-BaseEvent $prFlow 't2' 'PostToolUse'; $planPost.tool_name = 'apply_patch'; $planPost.tool_input = $planPatch.tool_input; $planPost.tool_response = @{ success = $true }; $planPost.tool_use_id = 'plan-write'
    $null = Invoke-HookCase $planPost
    $null = Invoke-StateCase $prFlow @('-Action', 'AddEvidence', '-CriterionId', 'P1', '-Validator', 'plan-review', '-EvidenceStatus', 'passed', '-Subject', $planFile, '-ExpectedToolName', 'apply_patch')
    $null = Invoke-StateCase $prFlow @('-Action', 'SetGate', '-Gate', 'publish', '-GateStatus', 'passed')
    $null = Invoke-StateCase $prFlow @('-Action', 'SetGate', '-Gate', 'selfReview', '-GateStatus', 'passed')

    $gitAdd = New-BaseEvent $prFlow 't2' 'PreToolUse'; $gitAdd.tool_name = 'Bash'; $gitAdd.tool_input = @{ command = 'git add docs/plan-feature.md'; workdir = $workspace }; $gitAdd.tool_use_id = 'git-add'
    Assert-True ($null -eq (Invoke-HookCase $gitAdd)) 'git add must be allowed after pre-publish gates.'
    foreach ($case in @(
        @{ id = 'git-add-dot'; command = 'git add .' },
        @{ id = 'git-add-directory'; command = 'git add docs' },
        @{ id = 'git-add-outside'; command = 'git add ../outside.txt' },
        @{ id = 'git-add-chain'; command = 'git add docs/plan-feature.md; git add ../outside.txt' }
    )) {
        $event = New-BaseEvent $prFlow 't2' 'PreToolUse'; $event.tool_name = 'Bash'; $event.tool_input = @{ command = $case.command; workdir = $workspace }; $event.tool_use_id = $case.id
        Assert-True ((Invoke-HookCase $event).hookSpecificOutput.permissionDecision -eq 'deny') "Unscoped staging command '$($case.command)' must be denied."
    }
    $directoryStage = New-BaseEvent $prFlow 't2' 'PreToolUse'; $directoryStage.tool_name = 'Bash'; $directoryStage.tool_input = @{ command = 'git add docs'; workdir = $workspace }; $directoryStage.tool_use_id = 'git-add-directory-reason'
    Assert-True ((Invoke-HookCase $directoryStage).hookSpecificOutput.permissionDecisionReason -match 'explicit, non-glob') 'An existing directory pathspec must fail parsing instead of being accepted under a broad write scope.'
    $gitAddPost = New-BaseEvent $prFlow 't2' 'PostToolUse'; $gitAddPost.tool_name = 'Bash'; $gitAddPost.tool_input = $gitAdd.tool_input; $gitAddPost.tool_response = @{ exit_code = 0 }; $gitAddPost.tool_use_id = 'git-add'
    $null = Invoke-HookCase $gitAddPost
    $commit = New-BaseEvent $prFlow 't2' 'PreToolUse'; $commit.tool_name = 'Bash'; $commit.tool_input = @{ command = 'git commit -m plan'; workdir = $workspace }; $commit.tool_use_id = 'git-commit'
    foreach ($case in @(
        @{ id = 'commit-all'; command = 'git commit -a -m plan' },
        @{ id = 'commit-amend'; command = 'git commit --amend -m plan' },
        @{ id = 'commit-pathspec'; command = 'git commit -m plan ../outside.txt' }
    )) {
        $event = New-BaseEvent $prFlow 't2' 'PreToolUse'; $event.tool_name = 'Bash'; $event.tool_input = @{ command = $case.command; workdir = $workspace }; $event.tool_use_id = $case.id
        Assert-True ((Invoke-HookCase $event).hookSpecificOutput.permissionDecision -eq 'deny') "Unscoped commit form '$($case.command)' must be denied."
    }
    $env:FIRST_PASS_QUALITY_TEST_STAGED_FILES = Join-Path $workspace 'unrelated.txt'
    Assert-True ((Invoke-HookCase $commit).hookSpecificOutput.permissionDecision -eq 'deny') 'Commit must reject a staged file outside WriteScope.'
    $env:FIRST_PASS_QUALITY_TEST_STAGED_FILES = $planFile
    try {
        Assert-True ($null -eq (Invoke-HookCase $commit)) 'A successful scoped git add must not invalidate publish evidence before commit.'
    } finally {
        Remove-Item Env:FIRST_PASS_QUALITY_TEST_STAGED_FILES -ErrorAction SilentlyContinue
    }
    $commitPost = New-BaseEvent $prFlow 't2' 'PostToolUse'; $commitPost.tool_name = 'Bash'; $commitPost.tool_input = $commit.tool_input; $commitPost.tool_response = @{ exit_code = 0 }; $commitPost.tool_use_id = 'git-commit'
    $null = Invoke-HookCase $commitPost
    $push = New-BaseEvent $prFlow 't2' 'PreToolUse'; $push.tool_name = 'Bash'; $push.tool_input = @{ command = 'git push -u origin feature/example'; workdir = $workspace }; $push.tool_use_id = 'git-push'
    $env:FIRST_PASS_QUALITY_TEST_BRANCH = 'feature/example'
    try {
        Assert-True ($null -eq (Invoke-HookCase $push)) 'A successful commit must not invalidate publish evidence before a same-branch push.'
        foreach ($case in @(
            @{ id = 'cross-branch-push'; command = 'git push origin HEAD:main' },
            @{ id = 'other-branch-push'; command = 'git push origin other-branch' }
        )) {
            $event = New-BaseEvent $prFlow 't2' 'PreToolUse'; $event.tool_name = 'Bash'; $event.tool_input = @{ command = $case.command; workdir = $workspace }; $event.tool_use_id = $case.id
            Assert-True ((Invoke-HookCase $event).hookSpecificOutput.permissionDecision -eq 'deny') "Cross-branch push '$($case.command)' must be denied."
        }
    } finally {
        Remove-Item Env:FIRST_PASS_QUALITY_TEST_BRANCH -ErrorAction SilentlyContinue
    }
    $pushPost = New-BaseEvent $prFlow 't2' 'PostToolUse'; $pushPost.tool_name = 'Bash'; $pushPost.tool_input = $push.tool_input; $pushPost.tool_response = @{ exit_code = 0 }; $pushPost.tool_use_id = 'git-push'
    $null = Invoke-HookCase $pushPost
    $afterPush = Invoke-StateCase $prFlow @('-Action', 'ShowStatus')
    Assert-True ($afterPush.gates.publish -eq 'passed' -and $afterPush.gates.selfReview -eq 'passed') 'Normal push must preserve content validation gates.'
    Assert-True ($afterPush.gates.review -eq 'pending') 'Every successful push must reopen required review.'

    $createPr = New-BaseEvent $prFlow 't2' 'PreToolUse'; $createPr.tool_name = 'Bash'; $createPr.tool_input = @{ command = 'gh pr create --title plan --body planning-only'; workdir = $workspace }; $createPr.tool_use_id = 'gh-pr-create'
    Assert-True ($null -eq (Invoke-HookCase $createPr)) 'gh pr create must be a PR action, not a production external write.'
    $typedCreatePr = New-BaseEvent $prFlow 't2' 'PreToolUse'; $typedCreatePr.tool_name = 'mcp__codex_apps__github_create_pull_request'; $typedCreatePr.tool_input = @{ owner = 'o'; repo = 'r'; head = 'feature/example'; base = 'main' }; $typedCreatePr.tool_use_id = 'typed-pr-create'
    Assert-True ($null -eq (Invoke-HookCase $typedCreatePr)) 'Typed GitHub create_pull_request must be allowed by PR mode.'
    $typedMerge = New-BaseEvent $prFlow 't2' 'PreToolUse'; $typedMerge.tool_name = 'mcp__codex_apps__github_merge_pull_request'; $typedMerge.tool_input = @{ owner = 'o'; repo = 'r'; number = 1 }; $typedMerge.tool_use_id = 'typed-pr-merge'
    Assert-True ((Invoke-HookCase $typedMerge).hookSpecificOutput.permissionDecision -eq 'deny') 'PR mode must not authorize merge.'
    $forcePush = New-BaseEvent $prFlow 't2' 'PreToolUse'; $forcePush.tool_name = 'Bash'; $forcePush.tool_input = @{ command = 'git push --force origin feature/example'; workdir = $workspace }; $forcePush.tool_use_id = 'force-push'
    Assert-True ((Invoke-HookCase $forcePush).hookSpecificOutput.permissionDecision -eq 'deny') 'PR mode must not authorize force-push.'
    $plusForcePush = New-BaseEvent $prFlow 't2' 'PreToolUse'; $plusForcePush.tool_name = 'Bash'; $plusForcePush.tool_input = @{ command = 'git push origin +HEAD:main'; workdir = $workspace }; $plusForcePush.tool_use_id = 'plus-force-push'
    Assert-True ((Invoke-HookCase $plusForcePush).hookSpecificOutput.permissionDecision -eq 'deny') 'PR mode must not authorize a plus-prefixed force-push refspec.'
    foreach ($case in @(
        @{ id = 'delete-push'; command = 'git push --delete origin main' },
        @{ id = 'mirror-push'; command = 'git push --mirror origin' },
        @{ id = 'prune-push'; command = 'git push --prune origin' },
        @{ id = 'empty-source-push'; command = 'git push origin :main' }
    )) {
        $event = New-BaseEvent $prFlow 't2' 'PreToolUse'; $event.tool_name = 'Bash'; $event.tool_input = @{ command = $case.command; workdir = $workspace }; $event.tool_use_id = $case.id
        Assert-True ((Invoke-HookCase $event).hookSpecificOutput.permissionDecision -eq 'deny') "Destructive push '$($case.command)' must not be authorized by PR mode."
    }
    $updateBranch = New-BaseEvent $prFlow 't2' 'PreToolUse'; $updateBranch.tool_name = 'Bash'; $updateBranch.tool_input = @{ command = 'gh pr update-branch 23'; workdir = $workspace }; $updateBranch.tool_use_id = 'gh-pr-update-branch'
    Assert-True ($null -eq (Invoke-HookCase $updateBranch)) 'gh pr update-branch must require and honor PR publish gates as a push-equivalent action.'
    $createPrPost = New-BaseEvent $prFlow 't2' 'PostToolUse'; $createPrPost.tool_name = 'Bash'; $createPrPost.tool_input = $createPr.tool_input; $createPrPost.tool_response = @{ exit_code = 0 }; $createPrPost.tool_use_id = 'gh-pr-create'
    $null = Invoke-HookCase $createPrPost
    $null = Invoke-StateCase $prFlow @('-Action', 'AddEvidence', '-CriterionId', 'C1', '-Validator', 'pr-created', '-EvidenceStatus', 'passed', '-Subject', 'https://github.test/o/r/pull/1', '-ExpectedToolName', 'Bash')
    $null = Invoke-StateCase $prFlow @('-Action', 'SetGate', '-Gate', 'acceptance', '-GateStatus', 'passed')
    $null = Invoke-StateCase $prFlow @('-Action', 'SetStatus', '-FinalStatus', 'ready') -ExpectFailure
    $null = Invoke-StateCase $prFlow @('-Action', 'SetGate', '-Gate', 'review', '-GateStatus', 'not_required') -ExpectFailure
    $null = Invoke-StateCase $prFlow @('-Action', 'SetGate', '-Gate', 'review', '-GateStatus', 'passed')
    $failedPushPost = New-BaseEvent $prFlow 't2' 'PostToolUse'; $failedPushPost.tool_name = 'Bash'; $failedPushPost.tool_input = $push.tool_input; $failedPushPost.tool_response = @{ exit_code = 1 }; $failedPushPost.tool_use_id = 'git-push-failed'
    $null = Invoke-HookCase $failedPushPost
    $afterFailedPush = Invoke-StateCase $prFlow @('-Action', 'ShowStatus')
    Assert-True ($afterFailedPush.gates.review -eq 'passed') 'A failed push must not reopen review because the remote diff did not change.'
    Assert-True ([bool]$afterFailedPush.failedWritePending) 'A failed push must pause later mutations until recovery is acknowledged.'
    $pushRecoveryRead = New-BaseEvent $prFlow 't2' 'PostToolUse'; $pushRecoveryRead.tool_name = 'Bash'; $pushRecoveryRead.tool_input = @{ command = 'git status --short'; workdir = $workspace }; $pushRecoveryRead.tool_response = @{ exit_code = 0 }; $pushRecoveryRead.tool_use_id = 'push-recovery-read'
    $null = Invoke-HookCase $pushRecoveryRead
    $null = Invoke-StateCase $prFlow @('-Action', 'AcknowledgeWriteRecovery', '-Reason', 'Parent verified the branch state after the failed push.')
    $afterPushRecovery = Invoke-StateCase $prFlow @('-Action', 'ShowStatus')
    Assert-True (-not [bool]$afterPushRecovery.failedWritePending) 'Verified recovery must clear the failed-write mutation pause.'
    $null = Invoke-StateCase $prFlow @('-Action', 'SetStatus', '-FinalStatus', 'ready')

    $stagedDeletion = 'contract-staged-deletion'
    $gitWorkspace = Join-Path $testRoot 'git-workspace'
    New-Item -ItemType Directory -Path $gitWorkspace -Force | Out-Null
    & git -C $gitWorkspace init --quiet
    & git -C $gitWorkspace config user.name 'Contract Test'
    & git -C $gitWorkspace config user.email 'contract@example.invalid'
    [IO.File]::WriteAllText((Join-Path $gitWorkspace 'allowed.txt'), "baseline`n", [Text.UTF8Encoding]::new($false))
    [IO.File]::WriteAllText((Join-Path $gitWorkspace 'outside.txt'), "baseline`n", [Text.UTF8Encoding]::new($false))
    & git -C $gitWorkspace add allowed.txt outside.txt
    & git -C $gitWorkspace commit --quiet -m baseline
    [IO.File]::AppendAllText((Join-Path $gitWorkspace 'allowed.txt'), "changed`n", [Text.UTF8Encoding]::new($false))
    Remove-Item -LiteralPath (Join-Path $gitWorkspace 'outside.txt') -Force
    & git -C $gitWorkspace add -- allowed.txt outside.txt
    $actualStaged = @(& git -C $gitWorkspace diff --cached --name-only --no-renames --diff-filter=ACDMRTUXB)
    if ($actualStaged.Count -ne 2 -or 'outside.txt' -notin $actualStaged) { throw 'Temporary Git index did not contain the expected modified file and staged deletion.' }
    Initialize-ClarifiedSession $stagedDeletion
    $null = Invoke-StateCase $stagedDeletion @(
        '-Action', 'StartTask', '-Outcome', 'Reject an out-of-scope staged deletion', '-Scope', $gitWorkspace,
        '-WriteScope', (Join-Path $gitWorkspace 'allowed.txt'), '-Mode', 'pr', '-Risk', 'medium',
        '-CompletionPolicy', 'wait-for-required-gates', '-Workflow', 'none', '-PrePublishWhen', 'staged index reviewed',
        '-DoneWhen', 'unsafe commit rejected', '-AllowDirty'
    )
    $stagedValidation = New-BaseEvent $stagedDeletion 't2' 'PostToolUse'; $stagedValidation.cwd = $gitWorkspace; $stagedValidation.tool_name = 'Bash'; $stagedValidation.tool_input = @{ command = 'git diff --cached --check'; workdir = $gitWorkspace }; $stagedValidation.tool_response = @{ exit_code = 0 }; $stagedValidation.tool_use_id = 'staged-deletion-validation'
    $null = Invoke-HookCase $stagedValidation
    $null = Invoke-StateCase $stagedDeletion @('-Action', 'AddEvidence', '-CriterionId', 'P1', '-Validator', 'staged diff', '-EvidenceStatus', 'passed', '-Subject', $gitWorkspace, '-ExpectedToolName', 'Bash')
    $null = Invoke-StateCase $stagedDeletion @('-Action', 'SetGate', '-Gate', 'publish', '-GateStatus', 'passed')
    $null = Invoke-StateCase $stagedDeletion @('-Action', 'SetGate', '-Gate', 'selfReview', '-GateStatus', 'passed')
    $unsafeCommit = New-BaseEvent $stagedDeletion 't2' 'PreToolUse'; $unsafeCommit.cwd = $gitWorkspace; $unsafeCommit.tool_name = 'Bash'; $unsafeCommit.tool_input = @{ command = 'git commit -m unsafe'; workdir = $gitWorkspace }; $unsafeCommit.tool_use_id = 'staged-deletion-commit'
    $env:FIRST_PASS_QUALITY_TEST_STAGED_FILES = @($actualStaged | ForEach-Object { Join-Path $gitWorkspace $_ }) -join '~~'
    try {
        $unsafeCommitDecision = Invoke-HookCase $unsafeCommit
        Assert-True ($unsafeCommitDecision.hookSpecificOutput.permissionDecisionReason -match 'outside the Task Lock write scope') ('Commit scope-checking must include staged deletions alongside allowed staged files. Decision: ' + ($unsafeCommitDecision | ConvertTo-Json -Depth 8 -Compress))
    } finally {
        Remove-Item Env:FIRST_PASS_QUALITY_TEST_STAGED_FILES -ErrorAction SilentlyContinue
    }

    $stopSession = 'contract-stop'
    Initialize-ClarifiedSession $stopSession
    $nonStopPrompt = New-BaseEvent $stopSession 't2' 'UserPromptSubmit'; $nonStopPrompt.prompt = 'Это стопка документов, продолжай.'
    $null = Invoke-HookCase $nonStopPrompt
    $nonStopState = Invoke-StateCase $stopSession @('-Action', 'ShowStatus')
    Assert-True (-not [bool]$nonStopState.stopOverride) 'A word containing стоп must not trigger the stop override.'
    $negatedStopPrompt = New-BaseEvent $stopSession 't2' 'UserPromptSubmit'; $negatedStopPrompt.prompt = "don't stop until the tests pass"
    $null = Invoke-HookCase $negatedStopPrompt
    $negatedStopState = Invoke-StateCase $stopSession @('-Action', 'ShowStatus')
    Assert-True (-not [bool]$negatedStopState.stopOverride) 'A negated stop phrase must request continuation, not activate stopOverride.'
    $stopPrompt = New-BaseEvent $stopSession 't2' 'UserPromptSubmit'; $stopPrompt.prompt = 'стоп'
    $null = Invoke-HookCase $stopPrompt
    $stopState = Invoke-StateCase $stopSession @('-Action', 'ShowStatus')
    Assert-True ([bool]$stopState.stopOverride) 'An explicit stop phrase must trigger the stop override.'
    $stopTool = New-BaseEvent $stopSession 't2' 'PreToolUse'; $stopTool.tool_name = 'Bash'; $stopTool.tool_input = @{ command = 'Get-Content README.md'; workdir = $workspace }; $stopTool.tool_use_id = 'after-stop'
    Assert-True ((Invoke-HookCase $stopTool).hookSpecificOutput.permissionDecision -eq 'deny') 'All tools must be blocked after stop.'

    [pscustomobject]@{
        status = 'passed'
        assertions = $script:Assertions
        policyVersion = '0.3.0'
        codexContract = '0.144.3'
    } | ConvertTo-Json
} finally {
    Remove-Item Env:FIRST_PASS_QUALITY_TEST_DATA -ErrorAction SilentlyContinue
    Remove-Item Env:FIRST_PASS_QUALITY_POINTER -ErrorAction SilentlyContinue
    $resolvedTest = [IO.Path]::GetFullPath($testRoot)
    $relativeToTemp = [IO.Path]::GetRelativePath($tempRoot, $resolvedTest)
    if ((Test-Path -LiteralPath $resolvedTest) -and -not [IO.Path]::IsPathRooted($relativeToTemp) -and -not $relativeToTemp.StartsWith('..')) {
        Remove-Item -LiteralPath $resolvedTest -Recurse -Force
    }
}
