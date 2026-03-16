$script:RuntimeDir = Join-Path $PSScriptRoot '.runtime'
$script:Pwsh = 'C:\Program Files\PowerShell\7\pwsh.exe'
$script:DefaultStartupTimeoutSec = 45

function Ensure-RuntimeDir {
    if (-not (Test-Path $script:RuntimeDir)) {
        New-Item -ItemType Directory -Path $script:RuntimeDir | Out-Null
    }
}

function Get-PidFilePath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    Ensure-RuntimeDir
    return (Join-Path $script:RuntimeDir "$Name.pid")
}

function Get-LogFilePath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    Ensure-RuntimeDir
    return (Join-Path $script:RuntimeDir "$Name.log")
}

function Get-ErrorLogFilePath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    Ensure-RuntimeDir
    return (Join-Path $script:RuntimeDir "$Name.error.log")
}

function Get-TrackedProcessId {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    $pidFile = Get-PidFilePath -Name $Name
    if (-not (Test-Path $pidFile)) {
        return $null
    }

    $raw = (Get-Content $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
    if (-not $raw) {
        Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
        return $null
    }

    $pidValue = 0
    if (-not [int]::TryParse($raw, [ref]$pidValue)) {
        Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
        return $null
    }

    try {
        $process = Get-Process -Id $pidValue -ErrorAction Stop
        return $process.Id
    }
    catch {
        Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
        return $null
    }
}

function Set-TrackedProcessId {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [int]$ProcessId
    )

    $pidFile = Get-PidFilePath -Name $Name
    Set-Content -Path $pidFile -Value $ProcessId
}

function Remove-TrackedProcessId {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    $pidFile = Get-PidFilePath -Name $Name
    if (Test-Path $pidFile) {
        Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    }
}

function Reset-ServiceArtifacts {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    Remove-TrackedProcessId -Name $Name
    $logPath = Get-LogFilePath -Name $Name
    if (Test-Path $logPath) {
        Remove-Item $logPath -Force -ErrorAction SilentlyContinue
    }
    $errorLogPath = Get-ErrorLogFilePath -Name $Name
    if (Test-Path $errorLogPath) {
        Remove-Item $errorLogPath -Force -ErrorAction SilentlyContinue
    }
}

function Wait-ForServiceReady {
    param(
        [Parameter(Mandatory = $true)]
        [System.Diagnostics.Process]$Process,
        [string]$HealthUrl,
        [int]$TimeoutSec = $script:DefaultStartupTimeoutSec
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if ($Process.HasExited) {
            return $false
        }

        if ([string]::IsNullOrWhiteSpace($HealthUrl)) {
            Start-Sleep -Seconds 2
            return (-not $Process.HasExited)
        }

        try {
            $response = Invoke-WebRequest -Uri $HealthUrl -UseBasicParsing -TimeoutSec 3
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                return $true
            }
        }
        catch {
        }

        Start-Sleep -Milliseconds 800
    }

    return $false
}

function Get-ListeningProcessIdsByPort {
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [int[]]$Ports
    )

    if (-not $Ports -or $Ports.Count -eq 0) {
        return @()
    }

    $results = @()
    $netstatOutput = netstat -ano -p tcp
    foreach ($port in $Ports) {
        $pattern = "[:\.]$port\s+.*LISTENING\s+(\d+)$"
        foreach ($line in $netstatOutput) {
            if ($line -match $pattern) {
                $results += [int]$matches[1]
            }
        }
    }
    return $results | Sort-Object -Unique
}

function Wait-ForPortsReleased {
    param(
        [int[]]$Ports,
        [int]$TimeoutSec = 10
    )

    if (-not $Ports -or $Ports.Count -eq 0) {
        return $true
    }

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        $pids = Get-ListeningProcessIdsByPort -Ports $Ports
        if (-not $pids -or $pids.Count -eq 0) {
            return $true
        }
        Start-Sleep -Milliseconds 500
    }

    return $false
}

function Start-ServiceWindow {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [string]$ScriptPath,
        [string]$HealthUrl,
        [int]$StartupTimeoutSec = $script:DefaultStartupTimeoutSec,
        [switch]$ResetExisting
    )

    $existingPid = Get-TrackedProcessId -Name $Name
    if ($existingPid) {
        if ($ResetExisting) {
            $null = Stop-ServiceWindow -Name $Name
        }
        else {
            return @{
                Name = $Name
                Status = 'already_running'
                ProcessId = $existingPid
                LogPath = Get-LogFilePath -Name $Name
            }
        }
    }

    Reset-ServiceArtifacts -Name $Name
    $logPath = Get-LogFilePath -Name $Name
    $errorLogPath = Get-ErrorLogFilePath -Name $Name
    try {
        $process = Start-Process -FilePath $script:Pwsh -ArgumentList @(
            '-NoProfile',
            '-ExecutionPolicy', 'Bypass',
            '-File', """$ScriptPath"""
        ) -WorkingDirectory $PSScriptRoot -PassThru -WindowStyle Hidden -RedirectStandardOutput $logPath -RedirectStandardError $errorLogPath
    }
    catch {
        Reset-ServiceArtifacts -Name $Name
        return @{
            Name = $Name
            Status = 'failed'
            ProcessId = $null
            LogPath = $logPath
            ErrorLogPath = $errorLogPath
            ErrorMessage = $_.Exception.Message
        }
    }

    Set-TrackedProcessId -Name $Name -ProcessId $process.Id

    $isReady = Wait-ForServiceReady -Process $process -HealthUrl $HealthUrl -TimeoutSec $StartupTimeoutSec
    if (-not $isReady) {
        try {
            if (-not $process.HasExited) {
                Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            }
        }
        catch {
        }
        finally {
            Remove-TrackedProcessId -Name $Name
        }

        return @{
            Name = $Name
            Status = 'failed'
            ProcessId = $process.Id
            LogPath = $logPath
            ErrorLogPath = $errorLogPath
        }
    }

    return @{
        Name = $Name
        Status = 'started'
        ProcessId = $process.Id
        LogPath = $logPath
        ErrorLogPath = $errorLogPath
    }
}

function Stop-ServiceWindow {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [int[]]$Ports
    )

    $trackedPid = Get-TrackedProcessId -Name $Name
    if (-not $trackedPid) {
        return @{
            Name = $Name
            Status = 'not_running'
        }
    }

    try {
        $process = Get-Process -Id $trackedPid -ErrorAction Stop
        if ($process.MainWindowHandle -ne 0) {
            $null = $process.CloseMainWindow()
            $process.WaitForExit(4000) | Out-Null
        }

        if (-not $process.HasExited) {
            Stop-Process -Id $process.Id -ErrorAction SilentlyContinue
        }
    }
    catch {
    }
    finally {
        Remove-TrackedProcessId -Name $Name
    }

    $lingeringPids = Get-ListeningProcessIdsByPort -Ports $Ports
    foreach ($pidValue in $lingeringPids) {
        try {
            Stop-Process -Id $pidValue -Force -ErrorAction SilentlyContinue
        }
        catch {
        }
    }
    $portsReleased = Wait-ForPortsReleased -Ports $Ports

    return @{
        Name = $Name
        Status = if ($portsReleased) { 'stopped' } else { 'stopped_with_lingering_ports' }
    }
}

function Start-DesktopApp {
    param(
        [switch]$NoStartServices,
        [switch]$ResetExisting,
        [int]$StartupDelayMs = 1200
    )

    $name = 'desktop_app'
    $rootDir = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
    $desktopAppPath = Join-Path $rootDir 'desktop_app.py'
    if (-not (Test-Path $desktopAppPath)) {
        return @{
            Name = $name
            Status = 'failed'
            ErrorMessage = "desktop_app.py not found: $desktopAppPath"
        }
    }

    $existingPid = Get-TrackedProcessId -Name $name
    if ($existingPid) {
        if ($ResetExisting) {
            $null = Stop-DesktopApp
        }
        else {
            return @{
                Name = $name
                Status = 'already_running'
                ProcessId = $existingPid
            }
        }
    }

    Reset-ServiceArtifacts -Name $name

    $arguments = @('.\desktop_app.py')
    if ($NoStartServices) {
        $arguments += '--no-start-services'
    }

    try {
        $process = Start-Process -FilePath 'pythonw' -ArgumentList $arguments -WorkingDirectory $rootDir -PassThru
    }
    catch {
        return @{
            Name = $name
            Status = 'failed'
            ErrorMessage = $_.Exception.Message
        }
    }

    Set-TrackedProcessId -Name $name -ProcessId $process.Id
    Start-Sleep -Milliseconds $StartupDelayMs
    $process.Refresh()
    if ($process.HasExited) {
        Remove-TrackedProcessId -Name $name
        return @{
            Name = $name
            Status = 'failed'
            ProcessId = $process.Id
            ExitCode = $process.ExitCode
            ErrorMessage = 'desktop app process exited immediately'
        }
    }

    return @{
        Name = $name
        Status = 'started'
        ProcessId = $process.Id
    }
}

function Stop-DesktopApp {
    return Stop-ServiceWindow -Name 'desktop_app' -Ports @()
}
