. "$PSScriptRoot\common.ps1"

$serviceScript = Join-Path $PSScriptRoot 'worker_service.ps1'
$result = Start-ServiceWindow -Name 'worker' -ScriptPath $serviceScript -StartupTimeoutSec 5 -ResetExisting
Write-Host ("worker: {0}" -f $result.Status)
if ($result.LogPath) {
    Write-Host ("worker_log: {0}" -f $result.LogPath)
}
