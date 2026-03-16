. "$PSScriptRoot\common.ps1"

$result = Stop-ServiceWindow -Name 'frontend' -Ports @(5173)
Write-Host ("frontend: {0}" -f $result.Status)
