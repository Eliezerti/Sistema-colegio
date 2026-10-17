param([string]$Version = "1.0.0", [switch]$Review)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
if ($env:OS -ne "Windows_NT") { throw "El ejecutable debe construirse en Windows." }
python -m pip install -r requirements-desktop.txt
if ($LASTEXITCODE -ne 0) { throw "No se pudieron instalar las dependencias." }
$TestOutput = @(python -m unittest discover -s tests -v 2>&1)
$TestExitCode = $LASTEXITCODE
$TestOutput | ForEach-Object { Write-Host $_ }
if ($TestExitCode -ne 0) {
    $Text = ($TestOutput | ForEach-Object { "$_" }) -join "`n"
    foreach ($Match in [regex]::Matches($Text, '(?ms)^(ERROR|FAIL): .*?(?=^={20,}|^-{20,}\r?\nRan|\z)')) {
        $Details = $Match.Value.Substring(0, [Math]::Min(3600, $Match.Value.Length))
        $Details = $Details.Replace('%','%25').Replace("`r",'%0D').Replace("`n",'%0A')
        Write-Host "::error title=Pruebas de Windows::$Details"
    }
    throw "Fallaron las pruebas; no se generará el instalador."
}
if ($Review) {
    if ($Version -notmatch 'borrador') { throw 'La revisión requiere una versión marcada borrador.' }
    $env:AULA_REVIEW_BUILD = '1'
} else { Remove-Item Env:AULA_REVIEW_BUILD -ErrorAction SilentlyContinue }
python -m PyInstaller --noconfirm --clean packaging/Aula.spec
if ($LASTEXITCODE -ne 0) { throw "No se pudo construir Aula.exe." }
python packaging/bundle_inventory.py dist/Aula --output "$env:RUNNER_TEMP/aula-b2-after.json" --verify
if ($LASTEXITCODE -ne 0) { throw "El paquete contiene módulos prohibidos o le faltan componentes necesarios." }
$Bootstrap = Join-Path $PWD "build\MicrosoftEdgeWebview2Setup.exe"
Invoke-WebRequest -Uri "https://go.microsoft.com/fwlink/p/?LinkId=2124703" -OutFile $Bootstrap
$Signature = Get-AuthenticodeSignature $Bootstrap
if ($Signature.Status -ne "Valid" -or $Signature.SignerCertificate.Subject -notmatch "O=Microsoft Corporation") {
    throw "El componente WebView2 no tiene una firma válida de Microsoft."
}
$Installer = Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"
if (-not (Test-Path $Installer)) { throw "Instala Inno Setup 6 para crear el instalador." }
$InstallerSource = if ($Review) { 'packaging\Aula-Revision.iss' } else { 'packaging\Aula.iss' }
& $Installer "/DAppVersion=$Version" $InstallerSource
if ($LASTEXITCODE -ne 0) { throw "No se pudo generar el instalador." }
$Package = "dist\Aula-Colegio-Instalador-$Version.exe"
$Digest = (Get-FileHash $Package -Algorithm SHA256).Hash.ToLowerInvariant()
[System.IO.File]::WriteAllText("$Package.sha256", "$Digest  $(Split-Path $Package -Leaf)`n", [System.Text.UTF8Encoding]::new($false))
Write-Host "Instalador construido: $Package"
