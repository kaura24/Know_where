$pwsh = 'C:\Program Files\PowerShell\7\pwsh.exe'
$stackScript = Join-Path $PSScriptRoot 'run_app_stack.ps1'
$openBrowserScript = Join-Path $PSScriptRoot 'open_browser.ps1'

& $pwsh -ExecutionPolicy Bypass -File $stackScript
Start-Sleep -Seconds 2
& $pwsh -ExecutionPolicy Bypass -File $openBrowserScript
