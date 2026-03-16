. "$PSScriptRoot\common.ps1"

$serviceScript = Join-Path $PSScriptRoot 'frontend_service.ps1'
$result = Start-ServiceWindow -Name 'frontend' -ScriptPath $serviceScript -HealthUrl 'http://127.0.0.1:5173' -StartupTimeoutSec 40 -ResetExisting
Write-Host ("frontend: {0}" -f $result.Status)
if ($result.LogPath) {
    Write-Host ("frontend_log: {0}" -f $result.LogPath)
}
