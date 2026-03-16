. "$PSScriptRoot\common.ps1"

$result = Stop-ServiceWindow -Name 'worker'
Write-Host ("worker: {0}" -f $result.Status)
