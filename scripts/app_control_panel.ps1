Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$pwsh = 'C:\Program Files\PowerShell\7\pwsh.exe'

function Invoke-ScriptFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ScriptName
    )

    $scriptPath = Join-Path $PSScriptRoot $ScriptName
    Start-Process -FilePath $pwsh -ArgumentList @(
        '-ExecutionPolicy', 'Bypass',
        '-File', $scriptPath
    ) -WindowStyle Hidden | Out-Null
}

$form = New-Object System.Windows.Forms.Form
$form.Text = 'Know Where Control'
$form.StartPosition = 'CenterScreen'
$form.Size = New-Object System.Drawing.Size(380, 300)
$form.FormBorderStyle = 'FixedDialog'
$form.MaximizeBox = $false
$form.MinimizeBox = $false
$form.TopMost = $true

$label = New-Object System.Windows.Forms.Label
$label.Text = '실행과 종료를 이 패널에서 제어합니다.'
$label.Location = New-Object System.Drawing.Point(20, 20)
$label.Size = New-Object System.Drawing.Size(320, 24)
$form.Controls.Add($label)

$startAll = New-Object System.Windows.Forms.Button
$startAll.Text = '웹앱 실행(기본)'
$startAll.Location = New-Object System.Drawing.Point(20, 60)
$startAll.Size = New-Object System.Drawing.Size(150, 40)
$startAll.Add_Click({ Invoke-ScriptFile -ScriptName 'run_app_stack.ps1' })
$form.Controls.Add($startAll)

$runDesktop = New-Object System.Windows.Forms.Button
$runDesktop.Text = '브라우저 모드'
$runDesktop.Location = New-Object System.Drawing.Point(190, 60)
$runDesktop.Size = New-Object System.Drawing.Size(150, 40)
$runDesktop.Add_Click({ Invoke-ScriptFile -ScriptName 'run_browser_stack.ps1' })
$form.Controls.Add($runDesktop)

$openBrowser = New-Object System.Windows.Forms.Button
$openBrowser.Text = '브라우저 새 창'
$openBrowser.Location = New-Object System.Drawing.Point(20, 108)
$openBrowser.Size = New-Object System.Drawing.Size(320, 40)
$openBrowser.Add_Click({ Invoke-ScriptFile -ScriptName 'open_browser.ps1' })
$form.Controls.Add($openBrowser)

$stopAll = New-Object System.Windows.Forms.Button
$stopAll.Text = '안전 종료'
$stopAll.Location = New-Object System.Drawing.Point(20, 158)
$stopAll.Size = New-Object System.Drawing.Size(320, 44)
$stopAll.Add_Click({ Invoke-ScriptFile -ScriptName 'stop_app_stack.ps1' })
$form.Controls.Add($stopAll)

$closePanel = New-Object System.Windows.Forms.Button
$closePanel.Text = '패널 닫기'
$closePanel.Location = New-Object System.Drawing.Point(20, 208)
$closePanel.Size = New-Object System.Drawing.Size(320, 32)
$closePanel.Add_Click({ $form.Close() })
$form.Controls.Add($closePanel)

[void]$form.ShowDialog()
