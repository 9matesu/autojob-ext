# scripts/package-release.ps1 — builds dist/resuMe-<ver>-windows-x64.zip
# Portable backend: embedded CPython (python-build-standalone) + pip deps + bundled Tectonic.
# Run from repo root:  powershell -ExecutionPolicy Bypass -File .\scripts\package-release.ps1
$ErrorActionPreference = "Stop"
$root  = Split-Path -Parent $PSScriptRoot
$ver   = (Get-Content "$root\extension\manifest.json" -Raw | ConvertFrom-Json).version
$stage = "$root\dist\resuMe-$ver"

# Pinned versions (update deliberately, verify tags on https://github.com/astral-sh/python-build-standalone/releases and tectonic releases)
$pyVer   = "3.14.7"
$pyTag   = "20260901"
$pySt    = "x86_64-pc-windows-msvc"
$tectVer = "0.17.0"

Write-Host "[1/7] Staging $stage" -ForegroundColor Yellow
Remove-Item $stage -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $stage | Out-Null

Write-Host "[2/7] Extension + docs" -ForegroundColor Yellow
Copy-Item "$root\extension" "$stage\extension" -Recurse
New-Item -ItemType Directory -Path "$stage\docs" -Force | Out-Null
Copy-Item "$root\docs\*" "$stage\docs"
Copy-Item "$root\README.md","$root\CHANGELOG.md" $stage -ErrorAction SilentlyContinue

Write-Host "[3/7] Embedded Python ($pyVer)" -ForegroundColor Yellow
$pyUrl  = "https://github.com/astral-sh/python-build-standalone/releases/download/$pyTag/cpython-$pyVer+$pyTag-$pySt-install_only.tar.gz"
$pyTar  = "$env:TEMP\resume-python.tar.gz"
Invoke-WebRequest $pyUrl -OutFile $pyTar
# System32 tar (bsdtar): git-bash GNU tar would parse "I:\..." as host:path.
& C:\Windows\System32\tar.exe -xzf $pyTar -C $stage
if ($LASTEXITCODE -ne 0) { throw "tar falhou ao extrair $pyTar" }
Rename-Item "$stage\python" "python-embedded"
& "$stage\python-embedded\python.exe" -m pip install -q --no-warn-script-location -r "$root\backend\requirements.txt"

Write-Host "[4/7] Backend sources" -ForegroundColor Yellow
Copy-Item "$root\backend" "$stage\backend" -Recurse
Remove-Item "$stage\backend\data" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "$stage\backend\.venv" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "$stage\backend\tests" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "$stage\backend\.env" -Force -ErrorAction SilentlyContinue
Get-ChildItem "$stage\backend" -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force
# ship the native-host ResumeHost sources + prebuilt exe
Copy-Item "$root\native-host" "$stage\native-host" -Recurse
Remove-Item "$stage\native-host\build" -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "[5/7] Tectonic ($tectVer)" -ForegroundColor Yellow
$tectUrl = "https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic@$tectVer/tectonic-$tectVer-$pySt.zip"
$tectZip = "$env:TEMP\tectonic.zip"
Invoke-WebRequest $tectUrl -OutFile $tectZip
New-Item -ItemType Directory -Path "$stage\backend\bin" -Force | Out-Null
Expand-Archive $tectZip -DestinationPath "$stage\backend\bin"
if (-not (Test-Path "$stage\backend\bin\tectonic.exe")) { throw "tectonic.exe nao encontrado no zip." }

Write-Host "[6/7] Launcher + LEIA-ME" -ForegroundColor Yellow
@'
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
& "$root\python-embedded\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8322 --app-dir "$root\backend"
'@ | Set-Content "$stage\start-engine.ps1" -Encoding UTF8
@'
resuMe 1.0 - instalacao
1. Descompacte esta pasta em um local FIXO (ex.: C:\resuMe) - o native host aponta caminhos absolutos.
2. Chrome: abra chrome://extensions, ative "Modo do desenvolvedor", clique "Carregar sem compactacao" e escolha a pasta extension\.
3. Uma vez so: powershell -ExecutionPolicy Bypass -File .\native-host\install-host.ps1
   (auto-inicia o motor ao abrir o painel lateral; log em backend\data\resume-backend.log)
   Sem o passo 3, execute start-engine.ps1 antes de usar.
4. Clique no icone da extensao -> painel lateral -> envie seu curriculo base -> capture uma vaga.
Fontes: Instrument Serif e Schibsted Grotesk (licencas OFL em extension\fonts\).
'@ | Set-Content "$stage\LEIA-ME.txt" -Encoding UTF8

Write-Host "[7/7] Zip" -ForegroundColor Yellow
New-Item -ItemType Directory -Path "$root\dist" -Force | Out-Null
Compress-Archive -Path "$stage\*" -DestinationPath "$root\dist\resuMe-$ver-windows-x64.zip" -Force
Write-Host "OK -> dist\resuMe-$ver-windows-x64.zip" -ForegroundColor Green
