[CmdletBinding()]
param(
    [ValidateSet('Validate', 'Status', 'Next', 'Run', 'Begin', 'Complete', 'Block', 'Unblock', 'Smoke')]
    [string]$Action = 'Status',
    [string]$TaskId,
    [string]$Evidence,
    [string]$Reason,
    [switch]$AcceptancePassed,
    [switch]$PreflightConfirmed,
    [switch]$IncludeOptional
)

$ErrorActionPreference = 'Stop'
$workspaceRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$tasksPath = Join-Path $workspaceRoot 'TASKS.json'
$logsPath = Join-Path $workspaceRoot 'logs'
$script:LogPath = Join-Path $logsPath ("controller-{0}.log" -f (Get-Date -Format 'yyyyMMdd-HHmmss'))
$script:LockHandle = $null
$script:PriorityRank = @{ critical = 4; high = 3; medium = 2; low = 1 }
$script:AllowedStatuses = @('pending', 'in_progress', 'verified', 'blocked', 'needs_decision')

function Write-ProjectLog {
    param([Parameter(Mandatory = $true)][string]$Message)
    if (-not (Test-Path -LiteralPath $logsPath)) {
        New-Item -ItemType Directory -Path $logsPath -Force | Out-Null
    }
    # Logs contain only action names and task IDs, never evidence, reasons, commands,
    # environment values, or source contents.
    $line = '{0} {1}' -f (Get-Date -Format 'yyyy-MM-ddTHH:mm:ssK'), $Message
    Add-Content -LiteralPath $script:LogPath -Value $line -Encoding UTF8
}

function Has-Property {
    param([object]$Object, [string]$Name)
    return ($null -ne $Object.PSObject.Properties[$Name])
}

function Assert-TaskGraph {
    param([Parameter(Mandatory = $true)][AllowEmptyCollection()][object[]]$GraphTasks)

    if ($GraphTasks.Count -eq 0) { throw 'TASKS.json must contain at least one task.' }
    $map = [System.Collections.Generic.Dictionary[string, object]]::new([System.StringComparer]::OrdinalIgnoreCase)

    foreach ($task in $GraphTasks) {
        foreach ($name in @('id', 'title', 'phase', 'priority', 'classification', 'status', 'dependencies', 'acceptance_criteria', 'verification_steps')) {
            if (-not (Has-Property -Object $task -Name $name)) { throw "A task is missing required property '$name'." }
        }
        $id = [string]$task.id
        if ([string]::IsNullOrWhiteSpace($id)) { throw 'Every task needs a non-empty id.' }
        if ($map.ContainsKey($id)) { throw "Duplicate task id: $id" }
        if ([string]::IsNullOrWhiteSpace([string]$task.title)) { throw "Task '$id' needs a title." }
        if ([string]$task.classification -notin @('required', 'optional')) { throw "Task '$id' has an invalid classification." }
        if ([string]$task.status -notin $script:AllowedStatuses) { throw "Task '$id' has an invalid status: $($task.status)" }
        if (-not $script:PriorityRank.ContainsKey([string]$task.priority)) { throw "Task '$id' has an invalid priority: $($task.priority)" }
        if ($null -eq $task.dependencies) { throw "Task '$id' needs a dependencies array (use [] when there are none)." }
        if (@($task.acceptance_criteria).Count -eq 0) { throw "Task '$id' needs acceptance criteria." }
        if (@($task.verification_steps).Count -eq 0) { throw "Task '$id' needs verification steps." }
        if ([string]$task.status -eq 'blocked' -and [string]::IsNullOrWhiteSpace([string]$task.blocked_reason)) {
            throw "Blocked task '$id' must record its exact blocked_reason."
        }
        $map.Add($id, $task)
    }

    foreach ($task in $GraphTasks) {
        $id = [string]$task.id
        foreach ($dependency in @($task.dependencies)) {
            $dependencyId = [string]$dependency
            if ([string]::IsNullOrWhiteSpace($dependencyId) -or -not $map.ContainsKey($dependencyId)) {
                throw "Task '$id' depends on unknown task '$dependencyId'."
            }
            if ([string]$task.status -in @('in_progress', 'verified')) {
                $prerequisite = $map[$dependencyId]
                if ([string]$prerequisite.status -ne 'verified') {
                    throw "Task '$id' has an unverified prerequisite '$dependencyId'."
                }
            }
        }
    }

    $activeTasks = @($GraphTasks | Where-Object { [string]$_.status -eq 'in_progress' })
    if ($activeTasks.Count -gt 1) { throw 'Only one task may be in_progress at a time.' }

    $visiting = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    $visited = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    foreach ($task in $GraphTasks) {
        Visit-TaskDependency -Id ([string]$task.id) -Map $map -Visiting $visiting -Visited $visited
    }
    return $map
}

function Visit-TaskDependency {
    param(
        [Parameter(Mandatory = $true)][string]$Id,
        [Parameter(Mandatory = $true)][System.Collections.Generic.Dictionary[string, object]]$Map,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][System.Collections.Generic.HashSet[string]]$Visiting,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][System.Collections.Generic.HashSet[string]]$Visited
    )
    if ($Visited.Contains($Id)) { return }
    if ($Visiting.Contains($Id)) { throw "Dependency cycle detected at task '$Id'." }
    [void]$Visiting.Add($Id)
    foreach ($dependency in @($Map[$Id].dependencies)) {
        Visit-TaskDependency -Id ([string]$dependency) -Map $Map -Visiting $Visiting -Visited $Visited
    }
    [void]$Visiting.Remove($Id)
    [void]$Visited.Add($Id)
}

function Read-TaskDocument {
    if (-not (Test-Path -LiteralPath $tasksPath -PathType Leaf)) { throw "Missing task ledger: $tasksPath" }
    $document = Get-Content -LiteralPath $tasksPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($null -eq $document.meta -or $null -eq $document.meta.total_tasks) { throw 'TASKS.json needs meta.total_tasks.' }
    if ($null -eq $document.tasks) { throw 'TASKS.json must define a tasks array.' }
    $taskList = @($document.tasks)
    if ([int]$document.meta.total_tasks -ne $taskList.Count) {
        throw "meta.total_tasks says $($document.meta.total_tasks), but the ledger contains $($taskList.Count) tasks."
    }
    $map = Assert-TaskGraph -GraphTasks $taskList
    return [pscustomobject]@{ Document = $document; Tasks = $taskList; Map = $map }
}

function Get-ReadyTasks {
    param([Parameter(Mandatory = $true)][object[]]$TaskList, [switch]$AllowOptional)
    $ready = @()
    foreach ($task in $TaskList) {
        if ([string]$task.status -ne 'pending') { continue }
        if ([string]$task.classification -eq 'optional' -and -not $AllowOptional) { continue }
        $prerequisitesPassed = $true
        foreach ($dependency in @($task.dependencies)) {
            $prerequisite = @($TaskList | Where-Object { [string]$_.id -eq [string]$dependency } | Select-Object -First 1)
            if ($prerequisite.Count -eq 0 -or [string]$prerequisite[0].status -ne 'verified') {
                $prerequisitesPassed = $false
                break
            }
        }
        if ($prerequisitesPassed) { $ready += $task }
    }
    $requiredReady = @($ready | Where-Object { [string]$_.classification -eq 'required' } | Sort-Object -Property @{ Expression = { $script:PriorityRank[[string]$_.priority] }; Descending = $true }, @{ Expression = { [string]$_.id }; Descending = $false })
    if ($requiredReady.Count -gt 0) { return $requiredReady }
    if ($AllowOptional) {
        return @($ready | Sort-Object -Property @{ Expression = { $script:PriorityRank[[string]$_.priority] }; Descending = $true }, @{ Expression = { [string]$_.id }; Descending = $false })
    }
    return @()
}

function Save-TaskDocument {
    param([Parameter(Mandatory = $true)][object]$Document)
    if (-not (Test-Path -LiteralPath $logsPath)) { New-Item -ItemType Directory -Path $logsPath -Force | Out-Null }
    $tempPath = Join-Path $logsPath ("TASKS-{0}-{1}.tmp" -f $PID, [guid]::NewGuid().ToString('N'))
    $json = ConvertTo-Json -InputObject $Document -Depth 100
    [System.IO.File]::WriteAllText($tempPath, $json + [Environment]::NewLine, [System.Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $tempPath -Destination $tasksPath -Force
}

function Write-GitPreflight {
    Write-Host 'Git state at task start:'
    $gitOutput = & git -C $workspaceRoot status --short --branch 2>$null
    if ($LASTEXITCODE -eq 0) {
        if ($gitOutput) { $gitOutput | ForEach-Object { Write-Host "  $_" } }
        else { Write-Host '  clean working tree' }
    }
    else { Write-Host '  Git status unavailable.' }
    Write-Host 'The project agent must review the task scope and relevant files before implementation.'
}

function Start-Task {
    param([object]$Document, [object]$Task)
    Write-GitPreflight
    $Task.status = 'in_progress'
    Save-TaskDocument -Document $Document
    Write-ProjectLog -Message ("task-started id={0}" -f [string]$Task.id)
    Write-Host ("Started task '{0}': {1}" -f $Task.id, $Task.title)
    Write-Host 'The controller records task state; the project agent performs implementation and acceptance checks.'
}

function Show-Blockers {
    param([object[]]$TaskList)
    $blocked = @($TaskList | Where-Object { [string]$_.status -in @('blocked', 'needs_decision') })
    if ($blocked.Count -eq 0) {
        Write-Host 'No task is ready. Pending tasks may be waiting on unfinished prerequisites.'
        return
    }
    Write-Host 'Blocked or decision tasks:'
    foreach ($task in $blocked) {
        $reason = if (-not [string]::IsNullOrWhiteSpace([string]$task.blocked_reason)) { [string]$task.blocked_reason } else { 'needs a recorded decision' }
        Write-Host ("- {0} [{1}]: {2}" -f $task.id, $task.status, $reason)
    }
}

function New-SmokeTask {
    param([string]$Id, [string[]]$Dependencies = @(), [string]$Status = 'pending', [string]$Priority = 'medium', [string]$Classification = 'required')
    return [pscustomobject]@{
        id = $Id; phase = 0; title = "Smoke $Id"; description = 'safe smoke task'
        priority = $Priority; classification = $Classification; status = $Status
        dependencies = @($Dependencies); expected_files = @('smoke.txt')
        acceptance_criteria = @('safe smoke criterion'); verification_steps = @('smoke only')
        verification_evidence = if ($Status -eq 'verified') { 'smoke only' } else { $null }
    }
}

function Assert-GraphRejected {
    param([string]$Name, [object[]]$Graph)
    try { [void](Assert-TaskGraph -GraphTasks $Graph) }
    catch { Write-Host ("  passed: rejected {0}" -f $Name); return }
    throw "Smoke check failed: controller accepted invalid graph case '$Name'."
}

function Enter-ControllerLock {
    if (-not (Test-Path -LiteralPath $logsPath)) { New-Item -ItemType Directory -Path $logsPath -Force | Out-Null }
    $lockPath = Join-Path $logsPath 'controller.lock'
    try { $script:LockHandle = [System.IO.File]::Open($lockPath, [System.IO.FileMode]::OpenOrCreate, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None) }
    catch { throw 'Another controller state change is running. Wait for it to finish, then retry.' }
}

try {
    if ($Action -in @('Run', 'Begin', 'Complete', 'Block', 'Unblock')) { Enter-ControllerLock }
    $state = Read-TaskDocument
    switch ($Action) {
        'Validate' {
            Write-Host ("Task graph valid: {0} tasks; IDs are unique, dependencies exist, and the graph is acyclic." -f $state.Tasks.Count)
            Write-ProjectLog -Message 'action=validate result=passed'
        }
        'Status' {
            foreach ($task in $state.Tasks) {
                $suffix = if ([string]$task.status -eq 'blocked') { " - $($task.blocked_reason)" } else { '' }
                Write-Host ("{0,-8} {1,-14} {2,-12} priority={3}{4}" -f $task.id, $task.status, $task.classification, $task.priority, $suffix)
            }
            Write-ProjectLog -Message 'action=status result=reported'
        }
        'Next' {
            $next = @(Get-ReadyTasks -TaskList $state.Tasks -AllowOptional:$IncludeOptional) | Select-Object -First 1
            if ($null -eq $next) { Show-Blockers -TaskList $state.Tasks }
            else { Write-Host ("Next ready task: {0} (priority {1}) - {2}" -f $next.id, $next.priority, $next.title) }
            Write-ProjectLog -Message 'action=next result=reported'
        }
        'Run' {
            $active = @($state.Tasks | Where-Object { [string]$_.status -eq 'in_progress' })
            if ($active.Count -gt 0) { Write-Host ("Resume task '{0}'; no second task was started." -f $active[0].id) }
            else {
                $next = @(Get-ReadyTasks -TaskList $state.Tasks -AllowOptional:$IncludeOptional) | Select-Object -First 1
                if ($null -eq $next) { Show-Blockers -TaskList $state.Tasks; Write-Host 'No task state was changed.' }
                elseif (-not $PreflightConfirmed) {
                    Write-Host ("Next ready task: {0} - {1}" -f $next.id, $next.title)
                    Write-Host 'Review PROJECT.md, relevant files, and Git state, then rerun with -PreflightConfirmed.'
                    Write-Host 'No task state was changed.'
                }
                else { Start-Task -Document $state.Document -Task $next }
            }
            Write-ProjectLog -Message 'action=run result=processed'
        }
        'Begin' {
            if ([string]::IsNullOrWhiteSpace($TaskId)) { throw 'Begin requires -TaskId.' }
            if (-not $PreflightConfirmed) { throw 'Begin requires -PreflightConfirmed after reviewing the task scope, relevant files, and Git state.' }
            if (@($state.Tasks | Where-Object { [string]$_.status -eq 'in_progress' }).Count -gt 0) { throw 'A task is already in_progress; finish or block it before starting another.' }
            $selected = @($state.Tasks | Where-Object { [string]$_.id -eq $TaskId } | Select-Object -First 1)
            if ($selected.Count -eq 0) { throw "Unknown task id '$TaskId'." }
            $ready = @(Get-ReadyTasks -TaskList $state.Tasks -AllowOptional:$IncludeOptional)
            if (-not ($ready | Where-Object { [string]$_.id -eq $TaskId })) { throw "Task '$TaskId' is not ready under current dependency and classification rules." }
            if ([string]$ready[0].id -ne $TaskId) { throw "Start the highest-priority ready task '$($ready[0].id)' first." }
            Start-Task -Document $state.Document -Task $selected[0]
        }
        'Complete' {
            if ([string]::IsNullOrWhiteSpace($TaskId)) { throw 'Complete requires -TaskId.' }
            if (-not $AcceptancePassed) { throw 'Complete requires -AcceptancePassed after checking acceptance criteria.' }
            if ([string]::IsNullOrWhiteSpace($Evidence)) { throw 'Complete requires -Evidence with verification results.' }
            $selected = @($state.Tasks | Where-Object { [string]$_.id -eq $TaskId } | Select-Object -First 1)
            if ($selected.Count -eq 0) { throw "Unknown task id '$TaskId'." }
            if ([string]$selected[0].status -ne 'in_progress') { throw "Task '$TaskId' must be in_progress before completion." }
            $selected[0].status = 'verified'
            $selected[0] | Add-Member -NotePropertyName verification_evidence -NotePropertyValue $Evidence -Force
            $selected[0] | Add-Member -NotePropertyName verified_at -NotePropertyValue (Get-Date -Format 'yyyy-MM-dd') -Force
            if (Has-Property -Object $selected[0] -Name 'blocked_reason') { $selected[0].blocked_reason = $null }
            Save-TaskDocument -Document $state.Document
            Write-ProjectLog -Message ("task-verified id={0}" -f $TaskId)
            Write-Host ("Verified task '{0}'. Update PLAN.md, STATE.md, and HANDOFF.md, review the diff, stage only its intended files, commit, pull --rebase, and push to main as authorized by D18." -f $TaskId)
        }
        'Block' {
            if ([string]::IsNullOrWhiteSpace($TaskId)) { throw 'Block requires -TaskId.' }
            if ([string]::IsNullOrWhiteSpace($Reason)) { throw 'Block requires -Reason with the exact blocker.' }
            $selected = @($state.Tasks | Where-Object { [string]$_.id -eq $TaskId } | Select-Object -First 1)
            if ($selected.Count -eq 0) { throw "Unknown task id '$TaskId'." }
            if ([string]$selected[0].status -eq 'verified') { throw "Verified task '$TaskId' cannot be marked blocked." }
            $selected[0].status = 'blocked'
            $selected[0] | Add-Member -NotePropertyName blocked_reason -NotePropertyValue $Reason -Force
            Save-TaskDocument -Document $state.Document
            Write-ProjectLog -Message ("task-blocked id={0}" -f $TaskId)
            Write-Host ("Recorded blocker for task '{0}'." -f $TaskId)
        }
        'Unblock' {
            if ([string]::IsNullOrWhiteSpace($TaskId)) { throw 'Unblock requires -TaskId.' }
            $selected = @($state.Tasks | Where-Object { [string]$_.id -eq $TaskId } | Select-Object -First 1)
            if ($selected.Count -eq 0) { throw "Unknown task id '$TaskId'." }
            if ([string]$selected[0].status -notin @('blocked', 'needs_decision')) { throw "Task '$TaskId' is not blocked or awaiting a decision." }
            $selected[0].status = 'pending'
            if (Has-Property -Object $selected[0] -Name 'blocked_reason') { $selected[0].blocked_reason = $null }
            Save-TaskDocument -Document $state.Document
            Write-ProjectLog -Message ("task-unblocked id={0}" -f $TaskId)
            Write-Host ("Returned task '{0}' to pending. Recheck dependencies with Validate." -f $TaskId)
        }
        'Smoke' {
            $beforeHash = (Get-FileHash -LiteralPath $tasksPath -Algorithm SHA256).Hash
            Write-Host ("Current graph valid: {0} tasks." -f $state.Tasks.Count)
            Write-Host 'Checking graph rejection cases without changing TASKS.json:'
            $duplicateA = New-SmokeTask -Id 'duplicate'
            $duplicateB = New-SmokeTask -Id 'duplicate'
            Assert-GraphRejected -Name 'duplicate IDs' -Graph @($duplicateA, $duplicateB)
            $missing = New-SmokeTask -Id 'child' -Dependencies @('missing-parent')
            Assert-GraphRejected -Name 'missing dependencies' -Graph @($missing)
            $cycleA = New-SmokeTask -Id 'cycle-a' -Dependencies @('cycle-b')
            $cycleB = New-SmokeTask -Id 'cycle-b' -Dependencies @('cycle-a')
            Assert-GraphRejected -Name 'dependency cycles' -Graph @($cycleA, $cycleB)
            $parent = New-SmokeTask -Id 'pending-parent'
            $activeChild = New-SmokeTask -Id 'active-child' -Dependencies @('pending-parent') -Status 'in_progress'
            Assert-GraphRejected -Name 'unverified active prerequisite' -Graph @($parent, $activeChild)
            $verifiedChild = New-SmokeTask -Id 'verified-child' -Dependencies @('pending-parent') -Status 'verified'
            Assert-GraphRejected -Name 'completion with unverified prerequisite' -Graph @($parent, $verifiedChild)
            $low = New-SmokeTask -Id 'required-medium' -Priority 'medium'
            $high = New-SmokeTask -Id 'required-critical' -Priority 'critical'
            $optional = New-SmokeTask -Id 'optional-critical' -Priority 'critical' -Classification 'optional'
            $requiredSelection = @(Get-ReadyTasks -TaskList @($low, $high, $optional))
            if ($requiredSelection.Count -ne 2 -or [string]$requiredSelection[0].id -ne 'required-critical') { throw 'Smoke check failed: priority selection is incorrect.' }
            $optionalSelection = @(Get-ReadyTasks -TaskList @($optional) -AllowOptional)
            if ($optionalSelection.Count -ne 1 -or [string]$optionalSelection[0].id -ne 'optional-critical') { throw 'Smoke check failed: optional selection is incorrect.' }
            Write-Host '  passed: highest-priority required task is selected; optional work stays separate'
            $afterHash = (Get-FileHash -LiteralPath $tasksPath -Algorithm SHA256).Hash
            if ($beforeHash -ne $afterHash) { throw 'Smoke check failed: TASKS.json changed.' }
            Write-Host 'SAFE SMOKE PASSED. No project commands ran; TASKS.json is unchanged.'
            Write-ProjectLog -Message 'action=smoke result=passed'
        }
    }
}
catch {
    Write-ProjectLog -Message ("action={0} result=failed" -f $Action)
    Write-Error $_
    exit 1
}
finally {
    if ($null -ne $script:LockHandle) { $script:LockHandle.Dispose() }
}
