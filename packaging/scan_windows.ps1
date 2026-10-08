param([Parameter(Mandatory=$true)][string]$Path)
$ErrorActionPreference = 'Stop'
$Target = (Resolve-Path $Path).Path
$ReportRoot = if ($env:RUNNER_TEMP) { $env:RUNNER_TEMP } else { [System.IO.Path]::GetTempPath() }
$ReportDir = Join-Path $ReportRoot 'Aula-Antivirus'
New-Item -ItemType Directory -Force -Path $ReportDir | Out-Null

# Scan only with the Microsoft-signed engine; never execute the target file.
Get-Command Get-MpComputerStatus -ErrorAction Stop | Out-Null
$Service = Get-Service WinDefend -ErrorAction Stop
if ($Service.Status -ne 'Running') {
    Start-Service WinDefend -ErrorAction Stop
}
$Status = Get-MpComputerStatus
if (-not $Status.AMServiceEnabled -or -not $Status.AntivirusEnabled) {
    throw 'Microsoft Defender no está activo. No se ha verificado el archivo y no se publicará.'
}
try {
    Update-MpSignature -ErrorAction Stop
} catch {
    # Use the supported Microsoft update source when Windows Update fails.
    Write-Host 'Windows Update no actualizó las firmas; se intenta el canal oficial MMPC.'
    Update-MpSignature -UpdateSource MMPC -ErrorAction Stop
}
$Status = Get-MpComputerStatus
$Status | Select-Object AMProductVersion,AMEngineVersion,AntivirusSignatureVersion,AntivirusSignatureLastUpdated |
    ConvertTo-Json | Set-Content (Join-Path $ReportDir 'motor.json') -Encoding utf8
Write-Host "Motor Defender: $($Status.AMEngineVersion); firmas: $($Status.AntivirusSignatureVersion)"
$Candidates = @(Get-ChildItem "$env:ProgramData/Microsoft/Windows Defender/Platform/*/MpCmdRun.exe" -ErrorAction SilentlyContinue | Sort-Object FullName -Descending)
$Scanner = if ($Candidates.Count) { $Candidates[0].FullName } else { "$env:ProgramFiles/Windows Defender/MpCmdRun.exe" }
$Signature = Get-AuthenticodeSignature $Scanner
if ($Signature.Status -ne 'Valid' -or $Signature.SignerCertificate.Subject -notmatch 'O=Microsoft Corporation') {
    throw 'El motor de análisis no tiene una firma válida de Microsoft.'
}
# Custom, synchronous scan. DisableRemediation preserves evidence and scans
# without applying cleanup actions; never add antivirus exclusions.
$Output = @(& $Scanner -Scan -ScanType 3 -File $Target -DisableRemediation 2>&1)
$ScanExit = $LASTEXITCODE
$Output | ForEach-Object { Write-Host $_ }
$Output | Set-Content (Join-Path $ReportDir 'resultado.txt') -Encoding utf8
Get-ChildItem $Target -Recurse -File | ForEach-Object {
    [PSCustomObject]@{name=$_.Name;sha256=(Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()}
} | ConvertTo-Json | Set-Content (Join-Path $ReportDir 'archivos.json') -Encoding utf8
if ($ScanExit -ne 0) {
    $Text = ($Output | ForEach-Object { "$_" }) -join "`n"
    $Details = $Text.Substring(0,[Math]::Min($Text.Length,3500)).Replace('%','%25').Replace("`r",'%0D').Replace("`n",'%0A')
    Write-Host "::error title=Microsoft Defender::$Details"
    throw "Defender devolvió el código $ScanExit. No se ejecutará ni publicará el archivo."
}
Write-Host 'El análisis terminó sin detecciones con el motor y las firmas registrados. No sustituye una revisión de Microsoft ni garantiza ausencia de malware.'
