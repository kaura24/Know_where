$chromePath = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
$appUrl = 'http://127.0.0.1:5173'

if (Test-Path $chromePath) {
    Start-Process -FilePath $chromePath -ArgumentList @('--new-window', $appUrl)
    exit 0
}

Start-Process $appUrl
