param([Parameter(Mandatory=$true)][string]$Version)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$Data = Join-Path $env:LOCALAPPDATA 'AulaColegio'
if (Test-Path $Data) { throw 'La comprobación del instalador solo se permite en un usuario Windows de prueba sin datos anteriores.' }
$InstallDir = Join-Path $env:RUNNER_TEMP 'Aula-Instalacion-Prueba'
$Installer = "dist/Aula-Colegio-Instalador-$Version.exe"

function Execute-Checked([string]$File, [string[]]$Arguments, [int]$Timeout = 120000) {
    $Process = Start-Process -FilePath $File -ArgumentList $Arguments -PassThru
    if (-not $Process.WaitForExit($Timeout)) { $Process.Kill(); throw "La operación no terminó: $(Split-Path $File -Leaf)" }
    if ($Process.ExitCode -ne 0) { throw "La operación falló: $(Split-Path $File -Leaf), código $($Process.ExitCode)" }
}

# Verified Microsoft bootstrap was downloaded by build_windows.ps1.
Execute-Checked 'build/MicrosoftEdgeWebview2Setup.exe' @('/silent','/install')
# Fixture data lives outside the program, just like an existing school database.
python -c "from pathlib import Path; import os; from colegio.db import initialize; from colegio.storage import consistent_backup; p=Path(os.environ['LOCALAPPDATA'])/'AulaColegio'/'colegio.sqlite3'; initialize(p); consistent_backup(p,p.parent/'backups'/'instalador-prueba.sqlite3')"
if ($LASTEXITCODE -ne 0) { throw 'No se pudo preparar la base de prueba del instalador.' }
$Database = Join-Path $Data 'colegio.sqlite3'
$Backup = Join-Path $Data 'backups/instalador-prueba.sqlite3'
$Before = (Get-FileHash $Database -Algorithm SHA256).Hash
$BeforeBackup = (Get-FileHash $Backup -Algorithm SHA256).Hash

try {
    $Arguments = @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-',"/DIR=`"$InstallDir`"",'/TASKS=desktopicon')
    Execute-Checked $Installer $Arguments
    $Executable = Join-Path $InstallDir 'Aula.exe'
    if (-not (Test-Path $Executable)) { throw 'No se instaló Aula.exe.' }
    $Desktop = [Environment]::GetFolderPath('Desktop')
    $Shell = New-Object -ComObject WScript.Shell
    $ShortcutPath = Join-Path $Desktop 'Colegio Alejandro Von Humboldt.lnk'
    if (-not (Test-Path $ShortcutPath)) { throw 'No se creó el acceso directo del escritorio.' }
    $Shortcut = $Shell.CreateShortcut($ShortcutPath)
    if ($Shortcut.TargetPath -ne $Executable) { throw 'El acceso directo no abre el ejecutable instalado.' }
    $Trial = $Shell.CreateShortcut((Join-Path $Desktop 'Aula - Pruebas.lnk'))
    if ($Trial.Arguments -ne '--demo') { throw 'El acceso de pruebas no abre el modo aislado.' }
    Execute-Checked $Executable @('--self-test')
    Execute-Checked $Executable @('--self-test-demo')
    # Reinstall/update and uninstall must leave data and backups untouched.
    Execute-Checked $Installer $Arguments
    Execute-Checked (Join-Path $InstallDir 'unins000.exe') @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART')
    if ((Get-FileHash $Database -Algorithm SHA256).Hash -ne $Before) { throw 'Instalar o desinstalar modificó la base existente.' }
    if ((Get-FileHash $Backup -Algorithm SHA256).Hash -ne $BeforeBackup) { throw 'Instalar o desinstalar modificó los respaldos.' }
    Write-Host 'PASS: instalación, accesos directos, ventanas normal/pruebas, bandeja, actualización y desinstalación conservando datos.'
} finally {
    # This folder was created exclusively by this test on a disposable runner.
    Remove-Item $Data -Recurse -Force -ErrorAction SilentlyContinue
}
