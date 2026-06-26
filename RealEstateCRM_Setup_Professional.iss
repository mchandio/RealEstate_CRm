#define MyAppName "Real Estate CRM"
#ifndef MyAppVersion
  #define MyAppVersion "2.1.0"
#endif
#define MyAppPublisher "Muhammad Siddique"
#define MyAppURL "mailto:info@msxhan.online"
#define MyAppExeName "RealEstateCRM_Qt.exe"
#define MyLanExeName "RealEstateCRM_LAN_Server.exe"
#define SourcePath "installer_staging"

[Setup]
AppId={{7B09DE77-CFB7-46E1-9693-262D4A0E3B55}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\Real Estate CRM
DefaultGroupName=Real Estate CRM
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=RealEstateCRM_v{#MyAppVersion}_Setup
SetupIconFile=company_logo\RealEstateCRM.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Real Estate CRM Windows Installer
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
CloseApplications=yes
RestartApplications=no
ChangesAssociations=no
ShowLanguageDialog=yes
WizardImageFile=compiler:wizmodernimage.bmp
WizardSmallImageFile=compiler:wizmodernsmallimage.bmp
; Use quiet mode for automated installations
AllowCancelDuringInstall=yes
AllowNoIcons=yes
CreateUninstallRegKey=yes
Uninstallable=yes
UsedUserAreasWarning=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut for the CRM"; GroupDescription: "Additional Icons:"; Flags: unchecked
Name: "quicklaunchicon"; Description: "Create a &Quick Launch icon"; GroupDescription: "Additional Icons:"; OnlyBelowVersion: 6.1; Flags: unchecked
Name: "serverdesktopicon"; Description: "Create a desktop shortcut for the &LAN web server"; GroupDescription: "Additional Icons:"; Flags: unchecked
Name: "runserver"; Description: "Auto-start LAN server on system startup"; GroupDescription: "System Integration:"

[Dirs]
Name: "{app}\outputs"
Name: "{app}\company_logo"
Name: "{app}\tools"
Name: "{app}\database_backups"

[Files]
; Main Qt Application
Source: "{#SourcePath}\dist\RealEstateCRM_Qt\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs solidbreak

; LAN Server
Source: "{#SourcePath}\dist\RealEstateCRM_LAN_Server.exe"; DestDir: "{app}"; Flags: ignoreversion

; Database (preserve existing)
Source: "{#SourcePath}\real_estate_crm.db"; DestDir: "{app}"; Flags: onlyifdoesntexist uninsneveruninstall

; Assets
Source: "company_logo\RealEstateCRM.ico"; DestDir: "{app}\company_logo"; Flags: ignoreversion
Source: "company_logo\RealEstateCRM_logo.png"; DestDir: "{app}\company_logo"; Flags: ignoreversion

; Documentation
Source: "LAN_MULTIUSER_SETUP.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "QUICKSTART.md"; DestDir: "{app}"; Flags: ignoreversion

; Utilities
Source: "enable_crm_firewall_6090.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "tools\cloudflared.exe"; DestDir: "{app}\tools"; Flags: ignoreversion
Source: "tools\start_crm_cloud_tunnel.ps1"; DestDir: "{app}\tools"; Flags: ignoreversion
Source: "tools\stop_crm_cloud_tunnel.ps1"; DestDir: "{app}\tools"; Flags: ignoreversion
Source: "tools\install_crm_cloud_tunnel_startup.ps1"; DestDir: "{app}\tools"; Flags: ignoreversion
Source: "tools\uninstall_crm_cloud_tunnel_startup.ps1"; DestDir: "{app}\tools"; Flags: ignoreversion

[Icons]
; Start Menu Icons
Name: "{group}\Real Estate CRM"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\company_logo\RealEstateCRM.ico"; Comment: "Launch the CRM desktop application"
Name: "{group}\LAN Web Server"; Filename: "{app}\{#MyLanExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\company_logo\RealEstateCRM.ico"; Comment: "Start the CRM LAN web server"
Name: "{group}\Open CRM Web (Local)"; Filename: "http://127.0.0.1:6090"; WorkingDir: "{app}"; Comment: "Open the CRM web interface"
Name: "{group}\Setup Remote Tunnel"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\tools\install_crm_cloud_tunnel_startup.ps1"""; WorkingDir: "{app}"; Comment: "Enable remote access via Cloudflare tunnel"
Name: "{group}\Firewall Configuration"; Filename: "{app}\enable_crm_firewall_6090.bat"; WorkingDir: "{app}"; Comment: "Enable firewall port for LAN access"
Name: "{group}\Documentation"; Filename: "{app}\README.md"; WorkingDir: "{app}"; Comment: "Read the documentation"
Name: "{group}\Multiuser Setup"; Filename: "{app}\LAN_MULTIUSER_SETUP.md"; WorkingDir: "{app}"; Comment: "Configure for multiuser access"
Name: "{group}\Uninstall"; Filename: "{uninstallexe}"; IconFilename: "{app}\company_logo\RealEstateCRM.ico"

; Desktop Icons
Name: "{autodesktop}\Real Estate CRM"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\company_logo\RealEstateCRM.ico"; Tasks: desktopicon; Comment: "Real Estate CRM"
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\Real Estate CRM"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\company_logo\RealEstateCRM.ico"; Tasks: quicklaunchicon; Comment: "Real Estate CRM"
Name: "{autodesktop}\CRM LAN Server"; Filename: "{app}\{#MyLanExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\company_logo\RealEstateCRM.ico"; Tasks: serverdesktopicon; Comment: "CRM LAN Web Server"

[Run]
; Post-install setup scripts
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\tools\install_crm_cloud_tunnel_startup.ps1"""; Flags: runhidden; Description: "Installing remote tunnel support..."
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\tools\start_crm_cloud_tunnel.ps1"""; Flags: runhidden nowait; Description: "Starting remote tunnel service..."; Tasks: runserver

; Post-install user options
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Real Estate CRM now"; Flags: nowait postinstall skipifsilent
Filename: "http://127.0.0.1:6090"; Description: "Open CRM web login (start server first)"; Flags: shellexec nowait postinstall skipifsilent unchecked
Filename: "notepad.exe"; Parameters: "{app}\README.md"; Description: "Read the README"; Flags: nowait postinstall skipifsilent unchecked

[UninstallRun]
; Cleanup on uninstall
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\tools\stop_crm_cloud_tunnel.ps1"""; Flags: runhidden
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\tools\uninstall_crm_cloud_tunnel_startup.ps1"""; Flags: runhidden

[InstallDelete]
; Clean up old versions
Type: filesandordirs; Name: "{app}\_internal"
Type: filesandordirs; Name: "{app}\QT_CRM_MBM"
Type: filesandordirs; Name: "{app}\base_library.zip"
Type: files; Name: "{app}\QT_CRM_MBM.exe"
Type: files; Name: "{app}\*.dll"

[UninstallDelete]
; Preserve user data on uninstall
; Type: filesandordirs; Name: "{app}\outputs"
; Type: files; Name: "{app}\real_estate_crm.db"

[Registry]
; Register file associations if needed
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\App Paths\RealEstateCRM_Qt.exe"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName}"
Root: HKCU; Subkey: "Software\Real Estate CRM"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"
Root: HKCU; Subkey: "Software\Real Estate CRM"; ValueType: string; ValueName: "Version"; ValueData: "{#MyAppVersion}"

[Code]
// Custom code for advanced installation features

// Check if .NET Framework is installed (if needed)
function InitializeSetup(): Boolean;
begin
  Result := True;
end;

// Post-install actions
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Installation completed - post-install scripts handle additional setup
  end;
end;

// Disable Next button until license is accepted (if you add a license)
procedure UpdateNextButtonState();
begin
  // Custom validation logic can go here
end;
