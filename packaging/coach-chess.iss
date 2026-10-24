#ifndef Payload
  #error Payload must point to the clean distribution directory
#endif
#ifndef AppVersion
  #define AppVersion "0.2.2"
#endif
[Setup]
AppId={{A26AF3F6-F396-4C70-9701-862FA9B44C81}
AppName=Coach Chess
AppVersion={#AppVersion}
AppPublisher=Coach Chess
DefaultDirName={autopf}\Coach Chess
DefaultGroupName=Coach Chess
OutputDir=..\dist
OutputBaseFilename=CoachChess-Setup-{#AppVersion}-Windows-x64
SetupIconFile=..\assets\acervo-chess.ico
UninstallDisplayIcon={app}\app\assets\acervo-chess.ico
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=commandline
Compression=lzma2/fast
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
CloseApplications=force
RestartApplications=no
VersionInfoVersion={#AppVersion}
[Languages]
Name: "portuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
[Tasks]
Name: "desktopicon"; Description: "Criar atalho na Área de Trabalho"; Flags: checkedonce
[Files]
Source: "{#Payload}\*"; DestDir: "{app}"; Excludes: "*\__pycache__\*,*.pyc,*\.agents\*"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\.build-tools\vc_redist.x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall; Check: NeedVCRuntime
[Icons]
Name: "{group}\Coach Chess"; Filename: "{app}\runtime\pythonw.exe"; Parameters: """{app}\app\installed_entry.py"""; WorkingDir: "{app}\app"; IconFilename: "{app}\app\assets\acervo-chess.ico"
Name: "{autodesktop}\Coach Chess"; Filename: "{app}\runtime\pythonw.exe"; Parameters: """{app}\app\installed_entry.py"""; WorkingDir: "{app}\app"; IconFilename: "{app}\app\assets\acervo-chess.ico"; Tasks: desktopicon
[Run]
Filename: "{tmp}\vc_redist.x64.exe"; Parameters: "/install /quiet /norestart"; Flags: waituntilterminated runhidden; Check: NeedVCRuntime
Filename: "{app}\runtime\pythonw.exe"; Parameters: """{app}\app\installed_entry.py"""; WorkingDir: "{app}\app"; Description: "Abrir Coach Chess"; Flags: nowait postinstall skipifsilent runasoriginaluser
[Code]
function NeedVCRuntime: Boolean;
var Installed: Cardinal;
begin
  Result := not (RegQueryDWordValue(HKLM64, 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64', 'Installed', Installed) and (Installed = 1));
end;
