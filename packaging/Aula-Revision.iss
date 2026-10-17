#ifndef AppVersion
  #error Falta version de revision
#endif

[Setup]
AppId={{0F80627C-25D9-4328-948D-E869A691F361}
AppName=Aula - BORRADOR ingresos y facturas
AppVersion={#AppVersion}
AppPublisher=Aula
DefaultDirName={localappdata}\Programs\AulaRevisionIngresos
DefaultGroupName=Aula - Revision ingresos
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.19041
OutputDir=..\dist
OutputBaseFilename=Aula-Colegio-Instalador-{#AppVersion}
SetupIconFile=aula.ico
UninstallDisplayIcon={app}\Aula.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=no
DisableProgramGroupPage=yes

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
Source: "..\dist\Aula\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\build\MicrosoftEdgeWebview2Setup.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "..\docs\cuentas-ingresos.html"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\docs\conciliacion-bancaria.html"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\docs\control-ingresos-cierre-mensual.html"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\docs\facturas-preimpresas.html"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\docs\cifrado-respaldos.html"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\docs\consulta-copias.html"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\docs\restauracion-segura.html"; DestDir: "{app}\docs"; Flags: ignoreversion

[Icons]
Name: "{group}\Aula BORRADOR"; Filename: "{app}\Aula.exe"
Name: "{group}\Aula BORRADOR - Pruebas"; Filename: "{app}\Aula.exe"; Parameters: "--demo"
Name: "{group}\Abrir carpeta de revision"; Filename: "{app}\Aula.exe"; Parameters: "--data-folder"
Name: "{group}\Abrir copia en solo lectura"; Filename: "{app}\Aula.exe"; Parameters: "--view-copy"
Name: "{group}\Probar respaldo"; Filename: "{app}\Aula.exe"; Parameters: "--test-backup"
Name: "{group}\Calibrar facturas"; Filename: "{app}\docs\facturas-preimpresas.html"

[Run]
Filename: "{tmp}\MicrosoftEdgeWebview2Setup.exe"; Parameters: "/silent /install"; StatusMsg: "Preparando WebView2..."; Flags: waituntilterminated; Check: NeedsWebView2

[Code]
function HasWebView2(RootKey: Integer; Key: String): Boolean;
var Version: String;
begin
  Result := RegQueryStringValue(RootKey, Key, 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0');
end;

function NeedsWebView2: Boolean;
var Client: String;
begin
  Client := '\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';
  Result := not (HasWebView2(HKCU, 'Software' + Client) or HasWebView2(HKLM64, 'Software' + Client) or HasWebView2(HKLM32, 'Software' + Client));
end;
