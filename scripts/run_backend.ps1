. "$PSScriptRoot\common.ps1"

$serviceScript = Join-Path $PSScriptRoot 'backend_service.ps1'
$result = Start-ServiceWindow -Name 'backend' -ScriptPath $serviceScript -HealthUrl 'http://127.0.0.1:8000/api/health/' -StartupTimeoutSec 40 -ResetExisting
Write-Host ("backend: {0}" -f $result.Status)
if ($result.LogPath) {
    Write-Host ("backend_log: {0}" -f $result.LogPath)
}
