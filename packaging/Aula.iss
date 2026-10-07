#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

[Setup]
AppId={{55F5F949-F16B-47B4-964A-D75AF4DF8DE2}
AppName=Unidad Educativa Colegio Alejandro Von Humboldt
AppVersion={#AppVersion}
AppPublisher=ALEJANDRO VON HUMBOLDT, C.A.
DefaultDirName={localappdata}\Programs\AulaColegio
DefaultGroupName=Colegio Alejandro Von Humboldt
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
CloseApplications=yes
CloseApplicationsFilter=Aula.exe
RestartApplications=no
AppMutex=AulaColegioDesktop,AulaColegioPruebas
DisableProgramGroupPage=yes

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; Flags: checkedonce
Name: "startup"; Description: "Abrir Aula al iniciar sesión en Windows"; Flags: unchecked

[Files]
Source: "..\dist\Aula\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\build\MicrosoftEdgeWebview2Setup.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Icons]
Name: "{group}\Colegio Alejandro Von Humboldt"; Filename: "{app}\Aula.exe"
Name: "{group}\Aula - Pruebas"; Filename: "{app}\Aula.exe"; Parameters: "--demo"
Name: "{group}\Configurar Aula"; Filename: "{app}\Aula.exe"; Parameters: "--configure"
Name: "{group}\Restaurar respaldo"; Filename: "{app}\Aula.exe"; Parameters: "--restore"
Name: "{group}\Recuperar clave del administrador"; Filename: "{app}\Aula.exe"; Parameters: "--reset-password"
Name: "{group}\Abrir carpeta de datos"; Filename: "{app}\Aula.exe"; Parameters: "--data-folder"
Name: "{userdesktop}\Colegio Alejandro Von Humboldt"; Filename: "{app}\Aula.exe"; Tasks: desktopicon
Name: "{userdesktop}\Aula - Pruebas"; Filename: "{app}\Aula.exe"; Parameters: "--demo"; Tasks: desktopicon
Name: "{userstartup}\Colegio Alejandro Von Humboldt"; Filename: "{app}\Aula.exe"; Tasks: startup

[Run]
Filename: "{tmp}\MicrosoftEdgeWebview2Setup.exe"; Parameters: "/silent /install"; StatusMsg: "Preparando el componente de ventanas de Microsoft..."; Flags: waituntilterminated; Check: NeedsWebView2
Filename: "{app}\Aula.exe"; Description: "Abrir el sistema del colegio"; Flags: nowait postinstall skipifsilent

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
  Result := not (HasWebView2(HKCU, 'Software' + Client) or
                 HasWebView2(HKLM64, 'Software' + Client) or
                 HasWebView2(HKLM32, 'Software' + Client));
end;
