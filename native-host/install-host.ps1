# Registers the resuMe native messaging host for Chrome.
# Run once: powershell -ExecutionPolicy Bypass -File .\native-host\install-host.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$nativeDir = Join-Path $root "native-host"
$backendDir = Join-Path $root "backend"
$pythonExe = Join-Path $backendDir ".venv\Scripts\python.exe"
$hostExe = Join-Path $nativeDir "ResumeHost.exe"

# 1. Ensure venv + pyinstaller
if (-not (Test-Path $pythonExe)) {
    Write-Host "[1/5] Creating backend venv..." -ForegroundColor Yellow
    python -m venv (Join-Path $backendDir ".venv")
    & $pythonExe -m pip install -q -r (Join-Path $backendDir "requirements.txt")
} else {
    Write-Host "[1/5] Backend venv present." -ForegroundColor Green
}

# 2. Build the host exe
if (-not (Test-Path $hostExe)) {
    Write-Host "[2/5] Building ResumeHost.exe (pyinstaller)..." -ForegroundColor Yellow
    & $pythonExe -m pip install -q pyinstaller
    & $pythonExe -m PyInstaller --onefile --noconsole --name ResumeHost `
        --distpath $nativeDir --workpath (Join-Path $nativeDir "build") `
        --specpath (Join-Path $nativeDir "build") -y (Join-Path $nativeDir "host_main.py")
    if (-not (Test-Path $hostExe)) { throw "ResumeHost.exe nao foi gerado." }
} else {
    Write-Host "[2/5] ResumeHost.exe already built." -ForegroundColor Green
}

# 3. Host config (machine-specific paths)
$config = [ordered]@{
    python       = $pythonExe
    backend_dir  = $backendDir
    port         = 8322
    log          = Join-Path $backendDir "data\resume-backend.log"
    startup_timeout = 12
}
$config | ConvertTo-Json | ForEach-Object { [System.IO.File]::WriteAllText((Join-Path $nativeDir "resume-host.json"), $_, (New-Object System.Text.UTF8Encoding($false))) }
Write-Host "[3/5] Wrote resume-host.json" -ForegroundColor Green

# 4. Derive extension ID from the pinned manifest key and write the host manifest
$manifest = Get-Content (Join-Path $root "extension\manifest.json") -Raw | ConvertFrom-Json
$pubDer = [Convert]::FromBase64String($manifest.key)
$sha = [System.Security.Cryptography.SHA256]::Create().ComputeHash($pubDer)
$hex = ($sha | ForEach-Object { $_.ToString("x2") }) -join ""
$letters = "abcdefghijklmnop"
$extId = -join ($hex.Substring(0, 32).ToCharArray() | ForEach-Object { $letters[[Convert]::ToInt32($_.ToString(), 16)] })

$hostManifest = [ordered]@{
    name           = "com.resume.host"
    description    = "Garante que o motor local do resuMe esteja rodando"
    path           = $hostExe
    type           = "stdio"
    allowed_origins = @("chrome-extension://$extId/")
}
$hostManifestPath = Join-Path $nativeDir "com.resume.host.json"
$hostManifest | ConvertTo-Json | ForEach-Object { [System.IO.File]::WriteAllText($hostManifestPath, $_, (New-Object System.Text.UTF8Encoding($false))) }
Write-Host "[4/5] Host manifest written. Extension ID: $extId" -ForegroundColor Green

# 5. Register in HKCU for Chrome
$regPath = "HKCU:\Software\Google\Chrome\NativeMessagingHosts\com.resume.host"
if (-not (Test-Path $regPath)) { New-Item -Path $regPath -Force | Out-Null }
Set-ItemProperty -Path $regPath -Name "(Default)" -Value $hostManifestPath
Write-Host "[5/5] Registered $regPath" -ForegroundColor Green

Write-Host ""
Write-Host "Concluido. Carregue a pasta 'extension\' sem compactar no Chrome;" -ForegroundColor Cyan
Write-Host "o painel lateral iniciara o backend automaticamente." -ForegroundColor Cyan
