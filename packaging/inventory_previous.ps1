# Disposable Windows runner only. Read the published 1.0.49 before exclusions.
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'Solo se permite en un runner desechable.' }
if (Test-Path (Join-Path $env:LOCALAPPDATA 'AulaColegio')) { throw 'La cuenta ya tiene datos de Aula.' }
Set-Location (Split-Path $PSScriptRoot -Parent)
python -m pip install -r requirements-desktop.txt
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron preparar las herramientas fijadas.' }
$Source = Join-Path $env:RUNNER_TEMP 'Aula-B2-Publicado'
New-Item $Source -ItemType Directory -Force | Out-Null
gh release download desktop-1.0.49 --pattern '*.exe*' --dir $Source
if ($LASTEXITCODE -ne 0) { throw 'No se pudo descargar la versión publicada.' }
$Installer = Join-Path $Source 'Aula-Colegio-Instalador-1.0.49.exe'
$Digest = (Get-FileHash $Installer -Algorithm SHA256).Hash.ToLowerInvariant()
if ($Digest -ne '3d4846ab01e76a96c3e3dc738a1945dfde1aa0d3fb845173e7fc18cf3e0ead2b') { throw 'Huella del instalador anterior incorrecta.' }
$Sidecar = (Get-Content "$Installer.sha256").Split(' ')[0]
if ($Sidecar -ne $Digest) { throw 'La huella publicada no coincide.' }
./packaging/scan_windows.ps1 -Path $Source -ReportDir "$env:RUNNER_TEMP/defender-b2-previous"
$Destination = Join-Path $env:RUNNER_TEMP 'Aula-B2-Inventario'
$Process = Start-Process $Installer -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-',"/DIR=`"$Destination`"",'/TASKS=') -PassThru -Wait
if ($Process.ExitCode -ne 0) { throw 'No se pudo instalar la versión anterior para inventariar.' }
try {
    python packaging/bundle_inventory.py $Destination --output "$env:RUNNER_TEMP/aula-b2-before.json"
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo leer el PYZ real anterior.' }
} finally {
    $Uninstaller = (python -c "from pathlib import Path; from tests.windows_upgrade import registered_uninstaller; print(registered_uninstaller(Path(r'$Destination')))" | Select-Object -Last 1)
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo identificar el desinstalador.' }
    $Process = Start-Process $Uninstaller -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART') -PassThru -Wait
    if ($Process.ExitCode -ne 0) { throw 'No se pudo retirar la instalación de inventario.' }
}
