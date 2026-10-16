param([Parameter(Mandatory=$true)][string]$Version)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'Solo se ejecuta en un runner Windows desechable.' }
$History = Join-Path $env:RUNNER_TEMP 'Aula-B1-Historico'
New-Item -ItemType Directory -Force $History | Out-Null
gh release download desktop-1.0.13 --dir $History --pattern 'Aula-Colegio-Instalador-1.0.13.exe*'
if ($LASTEXITCODE -ne 0) { throw 'No se descargó la versión realmente publicada.' }
gh release download desktop-1.0.67 --dir $History --pattern 'Aula-Colegio-Instalador-1.0.67.exe'
if ($LASTEXITCODE -ne 0) { throw 'No se descargó el instalador anterior 1.0.67 auditado.' }
$Old = Join-Path $History 'Aula-Colegio-Instalador-1.0.13.exe'
if ((Get-FileHash $Old -Algorithm SHA256).Hash.ToLowerInvariant() -ne '9714be7b6edaa03eab71a247c51219de6c425b5cd72d3b7fb7f1fbe23ab08d3c') { throw 'La huella histórica no coincide.' }
./packaging/scan_windows.ps1 -Path $History -ReportDir (Join-Path $env:RUNNER_TEMP 'defender-b1-historical')
python tests/windows_upgrade.py --version $Version --historical-dir $History
if ($LASTEXITCODE -ne 0) { throw 'Falló la instalación limpia o actualización histórica.' }

$Name = 'AulaB1' + [Guid]::NewGuid().ToString('N').Substring(0,8)
$Shared = Join-Path $env:PUBLIC $Name
New-Item -ItemType Directory $Shared | Out-Null
Set-Content (Join-Path $Shared 'disposable-b1-only.txt') 'Solo datos ficticios B1'
Copy-Item "dist/Aula-Colegio-Instalador-$Version.exe" (Join-Path $Shared 'installer.exe')
Copy-Item tests/windows_upgrade.py,tests/windows_other_account.py,tests/windows_portability.py $Shared
Copy-Item colegio (Join-Path $Shared 'colegio') -Recurse
python tests/create_portable_fixture.py --output $Shared
if ($LASTEXITCODE -ne 0) { throw 'No se creó la copia cifrada portátil ficticia.' }
@'
param([string]$Python,[string]$Root,[string]$Sid)
$ErrorActionPreference='Stop'
# Credential processes can initially inherit the caller's temporary directory.
# Compile the bridge in the explicitly permitted, fictional test area only.
$BootstrapTemp=Join-Path $Root 'compile-temp'
New-Item -ItemType Directory -Force $BootstrapTemp | Out-Null
$env:TEMP=$BootstrapTemp
$env:TMP=$BootstrapTemp
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class B1UserEnvironment {
 [DllImport("userenv.dll", SetLastError=true)] public static extern bool CreateEnvironmentBlock(out IntPtr block, IntPtr token, bool inherit);
 [DllImport("userenv.dll", SetLastError=true)] public static extern bool DestroyEnvironmentBlock(IntPtr block);
}
"@
$Block=[IntPtr]::Zero
$Identity=[Security.Principal.WindowsIdentity]::GetCurrent()
if (-not [B1UserEnvironment]::CreateEnvironmentBlock([ref]$Block,$Identity.Token,$false)) { throw 'Windows no creó el entorno del usuario real.' }
try {
 $Offset=0
 $UserEnvironment=@{}
 while ($true) {
  $Entry=[Runtime.InteropServices.Marshal]::PtrToStringUni([IntPtr]::Add($Block,$Offset))
  if (-not $Entry) { break }
  $Offset+=($Entry.Length+1)*2
  $Split=$Entry.IndexOf('=')
  if ($Split -gt 0) { $UserEnvironment[$Entry.Substring(0,$Split)]=$Entry.Substring($Split+1) }
 }
 # Replace the inherited environment with the actual Windows token/profile block.
 foreach ($Key in @([Environment]::GetEnvironmentVariables('Process').Keys)) { [Environment]::SetEnvironmentVariable($Key,$null,'Process') }
 foreach ($Key in $UserEnvironment.Keys) { [Environment]::SetEnvironmentVariable($Key,$UserEnvironment[$Key],'Process') }
} finally { [B1UserEnvironment]::DestroyEnvironmentBlock($Block) | Out-Null; $Identity.Dispose() }
& $Python "$Root/windows_other_account.py" --root $Root --expected-sid $Sid
exit $LASTEXITCODE
'@ | Set-Content (Join-Path $Shared 'launch-other-account.ps1') -Encoding UTF8
$Python = (Get-Command python).Source
$Password = ConvertTo-SecureString ('A!b1-' + [Guid]::NewGuid().ToString('N')) -AsPlainText -Force
$Account = $null
$HostData = Join-Path $env:LOCALAPPDATA 'AulaColegio'
if (Test-Path $HostData) { throw 'La cuenta principal todavía tiene datos; no se modificaron.' }
New-Item -ItemType Directory $HostData | Out-Null
$Sentinel = Join-Path $HostData 'sentinel-b1.txt'
Set-Content $Sentinel 'Ficticio: pertenece a la cuenta principal'
$HostHash = (Get-FileHash $Sentinel -Algorithm SHA256).Hash
$HostDatabase = Join-Path $HostData 'colegio.sqlite3'
Copy-Item 'tests/fixtures/restore/desktop-1.0.13.sqlite3' $HostDatabase
$HostDatabaseHash = (Get-FileHash $HostDatabase -Algorithm SHA256).Hash
try {
    $Account = New-LocalUser -Name $Name -Password $Password -Description 'Cuenta estándar desechable para B1'
    Add-LocalGroupMember -Group (Get-LocalGroup -SID 'S-1-5-32-545') -Member $Name
    $Sid = $Account.SID.Value
    icacls $Shared /grant "*${Sid}:(OI)(CI)M" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo preparar únicamente el área ficticia compartida.' }
    $Command = "& '$Shared/launch-other-account.ps1' -Python '$Python' -Root '$Shared' -Sid '$Sid'; exit `$LASTEXITCODE"
    $Encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($Command))
    $Credential = [PSCredential]::new("$env:COMPUTERNAME\$Name", $Password)
    $Process = Start-Process powershell.exe -Credential $Credential -LoadUserProfile -PassThru -ArgumentList @('-NoProfile','-ExecutionPolicy','RemoteSigned','-EncodedCommand',$Encoded) -WorkingDirectory $Shared -RedirectStandardOutput (Join-Path $Shared 'stdout.txt') -RedirectStandardError (Join-Path $Shared 'stderr.txt')
    if (-not $Process.WaitForExit(240000)) { taskkill /PID $Process.Id /T /F | Out-Null; throw 'La prueba de la segunda cuenta no terminó.' }
    if ($Process.ExitCode -ne 0) { throw ('Falló la segunda cuenta: ' + (Get-Content (Join-Path $Shared 'stderr.txt') -Raw)) }
    $Proof = Get-Content (Join-Path $Shared 'other-account-result.json') -Raw | ConvertFrom-Json
    if ($Proof.sid -ne $Sid -or $Proof.localappdata -eq $env:LOCALAPPDATA) { throw 'No se comprobó una cuenta y carpeta realmente distintas.' }
    $Profile = Get-CimInstance Win32_UserProfile | Where-Object SID -eq $Sid
    if (-not $Profile -or -not $Proof.data_path.StartsWith($Profile.LocalPath,[StringComparison]::OrdinalIgnoreCase)) { throw 'La carpeta no corresponde al perfil real de Windows.' }
    if ((Get-FileHash $Sentinel -Algorithm SHA256).Hash -ne $HostHash) { throw 'La segunda cuenta modificó datos de la principal.' }
    if ((Get-FileHash $HostDatabase -Algorithm SHA256).Hash -ne $HostDatabaseHash) { throw 'La segunda cuenta modificó la base de la principal.' }
    Copy-Item (Join-Path $Shared 'other-account-result.json') (Join-Path $env:RUNNER_TEMP 'aula-b1-other-account.json')
    Write-Host 'PASS B1: otra cuenta estándar real, instalación/inicio sin fichas previas, perfil distinto y desinstalación conserva sus datos; cuenta principal intacta.'
} finally {
    $Diagnostic = Join-Path $env:RUNNER_TEMP 'aula-b1-diagnostic'
    New-Item -ItemType Directory -Force $Diagnostic | Out-Null
    Copy-Item (Join-Path $Shared 'stderr.txt'),(Join-Path $Shared 'stdout.txt') $Diagnostic -ErrorAction SilentlyContinue
    if ($Account) {
        Get-CimInstance Win32_UserProfile | Where-Object SID -eq $Account.SID.Value | Remove-CimInstance -ErrorAction SilentlyContinue
        Remove-LocalUser -Name $Name -ErrorAction SilentlyContinue
    }
    Remove-Item $Shared -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item $HostData -Recurse -Force -ErrorAction SilentlyContinue
}
