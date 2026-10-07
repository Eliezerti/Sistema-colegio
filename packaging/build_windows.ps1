param([string]$Version = "1.0.0")
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
if ($env:OS -ne "Windows_NT") { throw "El ejecutable debe construirse en Windows." }
python -m pip install -r requirements-desktop.txt
if ($LASTEXITCODE -ne 0) { throw "No se pudieron instalar las dependencias." }
python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw "Fallaron las pruebas; no se generará el instalador." }
python -m PyInstaller --noconfirm --clean --onedir --windowed --name Aula --icon packaging/aula.ico --add-data "static;static" --add-data "colegio/fonts;colegio/fonts" --collect-all webview --hidden-import pystray._win32 desktop_entry.py
if ($LASTEXITCODE -ne 0) { throw "No se pudo construir Aula.exe." }
$Bootstrap = Join-Path $PWD "build\MicrosoftEdgeWebview2Setup.exe"
Invoke-WebRequest -Uri "https://go.microsoft.com/fwlink/p/?LinkId=2124703" -OutFile $Bootstrap
$Signature = Get-AuthenticodeSignature $Bootstrap
if ($Signature.Status -ne "Valid" -or $Signature.SignerCertificate.Subject -notmatch "O=Microsoft Corporation") {
    throw "El componente WebView2 no tiene una firma válida de Microsoft."
}
$Installer = Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"
if (-not (Test-Path $Installer)) { throw "Instala Inno Setup 6 para crear el instalador." }
& $Installer "/DAppVersion=$Version" "packaging\Aula.iss"
if ($LASTEXITCODE -ne 0) { throw "No se pudo generar el instalador." }
$Package = "dist\Aula-Colegio-Instalador-$Version.exe"
$Digest = (Get-FileHash $Package -Algorithm SHA256).Hash.ToLowerInvariant()
[System.IO.File]::WriteAllText("$Package.sha256", "$Digest  $(Split-Path $Package -Leaf)`n", [System.Text.UTF8Encoding]::new($false))
Write-Host "Instalador construido: $Package"
