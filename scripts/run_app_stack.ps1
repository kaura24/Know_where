# CONTRACT: scripts/RUN_STACK_CONTRACT.md
# 필수 단계: stop -> backend -> worker -> frontend -> run_desktop_app.ps1 -NoStartServices
# 5단계 생략 시 앱 창이 뜨지 않음 (LESSON.md 참고)

. "$PSScriptRoot\common.ps1"

$pwsh = 'C:\Program Files\PowerShell\7\pwsh.exe'
$stopScript = Join-Path $PSScriptRoot 'stop_app_stack.ps1'
$backendScript = Join-Path $PSScriptRoot 'run_backend.ps1'
$workerScript = Join-Path $PSScriptRoot 'run_worker.ps1'
$frontendScript = Join-Path $PSScriptRoot 'run_frontend.ps1'

function Invoke-StepScript {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Label,
        [Parameter(Mandatory = $true)]
        [string]$ScriptPath
    )

    & $pwsh -ExecutionPolicy Bypass -File $ScriptPath
    if ($LASTEXITCODE -ne 0) {
        throw ("{0} failed with exit code {1}" -f $Label, $LASTEXITCODE)
    }
}

Write-Host 'Checking existing tracked services...'
foreach ($name in @('backend', 'worker', 'frontend', 'desktop_app')) {
    $trackedPid = Get-TrackedProcessId -Name $name
    if ($trackedPid) {
        Write-Host ("{0}: tracked_pid={1}" -f $name, $trackedPid)
    }
    else {
        Write-Host ("{0}: not_tracked" -f $name)
    }
}

Write-Host 'Resetting existing app stack...'
Invoke-StepScript -Label 'stop_app_stack' -ScriptPath $stopScript

Write-Host 'Starting backend...'
Invoke-StepScript -Label 'run_backend' -ScriptPath $backendScript

Write-Host 'Starting worker...'
Invoke-StepScript -Label 'run_worker' -ScriptPath $workerScript

Write-Host 'Starting frontend...'
Invoke-StepScript -Label 'run_frontend' -ScriptPath $frontendScript

# CONTRACT step 5: 데스크톱 앱 창 실행 (생략 금지)
Write-Host 'Starting desktop app window...'
$desktopResult = Start-DesktopApp -NoStartServices -ResetExisting
Write-Host ("desktop_app: {0}" -f $desktopResult.Status)
if ($desktopResult.ProcessId) {
    Write-Host ("desktop_app_pid: {0}" -f $desktopResult.ProcessId)
}
if ($desktopResult.Status -ne 'started' -and $desktopResult.Status -ne 'already_running') {
    $message = if ($desktopResult.ErrorMessage) { $desktopResult.ErrorMessage } else { 'failed to start desktop app in run_app_stack' }
    throw $message
}
