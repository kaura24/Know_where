. "$PSScriptRoot\common.ps1"

$services = @(
    @{ Name = 'desktop_app'; Ports = @() },
    @{ Name = 'frontend'; Ports = @(5173) },
    @{ Name = 'worker'; Ports = @() },
    @{ Name = 'backend'; Ports = @(8000) }
)

foreach ($service in $services) {
    $result = Stop-ServiceWindow -Name $service.Name -Ports $service.Ports
    Write-Host ("{0}: {1}" -f $result.Name, $result.Status)
}
