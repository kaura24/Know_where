param(
    [switch]$NoStartServices
)

. "$PSScriptRoot\common.ps1"

$result = Start-DesktopApp -NoStartServices:$NoStartServices -ResetExisting
Write-Host ("desktop_app: {0}" -f $result.Status)
if ($result.ProcessId) {
    Write-Host ("desktop_app_pid: {0}" -f $result.ProcessId)
}
if ($result.Status -ne 'started' -and $result.Status -ne 'already_running') {
    $message = if ($result.ErrorMessage) { $result.ErrorMessage } else { 'failed to start desktop app' }
    throw $message
}
