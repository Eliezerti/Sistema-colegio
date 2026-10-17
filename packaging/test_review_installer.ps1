param([Parameter(Mandatory=$true)][string]$Version)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$Production = Join-Path $env:LOCALAPPDATA 'AulaColegio'
$Review = Join-Path $env:LOCALAPPDATA 'AulaRevisionIngresos/AulaColegio'
if ((Test-Path $Production) -or (Test-Path $Review)) { throw 'Esta prueba exige un usuario Windows desechable sin carpetas de Aula.' }
$InstallDir = Join-Path $env:RUNNER_TEMP 'Aula-Revision-Instalada'
$Installer = "dist/Aula-Colegio-Instalador-$Version.exe"
function Execute-Checked([string]$File, [string[]]$Arguments, [int]$Timeout = 180000) {
    $Process = Start-Process -FilePath $File -ArgumentList $Arguments -PassThru
    if (-not $Process.WaitForExit($Timeout)) { $Process.Kill(); throw "No terminó $(Split-Path $File -Leaf)." }
    if ($Process.ExitCode -ne 0) { throw "Falló $(Split-Path $File -Leaf): $($Process.ExitCode)." }
}
# These are exclusively fixtures in a disposable runner, never a user's folder.
python -c "from pathlib import Path; import os; from colegio.db import initialize; from colegio.storage import consistent_backup; r=Path(os.environ['LOCALAPPDATA']); [(initialize(r/p/'colegio.sqlite3'),consistent_backup(r/p/'colegio.sqlite3',r/p/'backups'/'FICTICIO.sqlite3')) for p in ('AulaColegio','AulaRevisionIngresos/AulaColegio')]"
if ($LASTEXITCODE -ne 0) { throw 'No se prepararon las dos carpetas ficticias.' }
$Files = @((Join-Path $Production 'colegio.sqlite3'),(Join-Path $Production 'backups/FICTICIO.sqlite3'),(Join-Path $Review 'colegio.sqlite3'),(Join-Path $Review 'backups/FICTICIO.sqlite3'))
$Before = @{}
foreach ($File in $Files) { $Before[$File]=(Get-FileHash $File -Algorithm SHA256).Hash }
Execute-Checked 'build/MicrosoftEdgeWebview2Setup.exe' @('/silent','/install')
$Arguments = @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-',"/DIR=`"$InstallDir`"")
Execute-Checked $Installer $Arguments
$Executable=Join-Path $InstallDir 'Aula.exe'
if (-not (Test-Path $Executable)) { throw 'Falta el ejecutable instalado.' }
foreach ($Forbidden in @('*.sqlite3','*.aulabak','*.db')) {
    if (Get-ChildItem $InstallDir -Recurse -Filter $Forbidden) { throw 'El paquete incluye una base o respaldo.' }
}
$Group=Join-Path ([Environment]::GetFolderPath('Programs')) 'Aula - Revision ingresos'
$Shell=New-Object -ComObject WScript.Shell
$Shortcut=$Shell.CreateShortcut((Join-Path $Group 'Aula BORRADOR.lnk'))
if ($Shortcut.TargetPath -ne $Executable) { throw 'El acceso de revisión no abre su propio ejecutable.' }
Execute-Checked $Executable @('--self-test')
Execute-Checked $Executable @('--self-test-demo')
Execute-Checked $Executable @('--self-test-copy')
$Logs=@(Get-Content "$env:TEMP/AulaColegio-Compilacion/logs/*.log")
foreach ($Prefix in @('PASS LIMPIEZA:','PASS COPIA:','PASS B2:','PASS RECIBO:')) {
    if (@($Logs | Where-Object { $_.StartsWith($Prefix) }).Count -lt 1) { throw "Falta evidencia nativa: $Prefix" }
}
Execute-Checked $Installer $Arguments
Execute-Checked (Join-Path $InstallDir 'unins000.exe') @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART')
foreach ($File in $Files) {
    if ((Get-FileHash $File -Algorithm SHA256).Hash -ne $Before[$File]) { throw "Instalar o desinstalar cambió el fixture: $File" }
}
Write-Output '::notice title=Instalador BORRADOR::Instalación separada, accesos, tres autopruebas nativas, reinstalación y desinstalación correctas; bases y respaldos ficticios de producción/revisión conservados. No es actualización del producto publicado ni prueba física de impresora.'
