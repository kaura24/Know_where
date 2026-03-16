. "$PSScriptRoot\common.ps1"

$result = Stop-ServiceWindow -Name 'backend' -Ports @(8000)
Write-Host ("backend: {0}" -f $result.Status)
