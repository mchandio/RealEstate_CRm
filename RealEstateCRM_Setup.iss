#define MyAppName "Real Estate CRM"
#define MyAppVersion "2.0.1"
#define MyAppPublisher "Muhammad Siddique"
#define MyAppURL "mailto:info@msxhan.online"
#define MyAppExeName "RealEstateCRM_Qt.exe"
#define MyLanExeName "RealEstateCRM_LAN_Server.exe"

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
OutputBaseFilename=RealEstateCRM_Setup_v{#MyAppVersion}
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

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut for the desktop CRM"; GroupDescription: "Shortcuts:"
Name: "serverdesktopicon"; Description: "Create a desktop shortcut for the LAN web server"; GroupDescription: "Shortcuts:"

[Dirs]
Name: "{app}\outputs"
Name: "{app}\company_logo"

[Files]
Source: "installer_staging\dist\RealEstateCRM_Qt\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "installer_staging\dist\{#MyLanExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "installer_staging\real_estate_crm.db"; DestDir: "{app}"; Flags: onlyifdoesntexist uninsneveruninstall
Source: "company_logo\RealEstateCRM.ico"; DestDir: "{app}\company_logo"; Flags: ignoreversion
Source: "company_logo\RealEstateCRM_logo.png"; DestDir: "{app}\company_logo"; Flags: ignoreversion
Source: "LAN_MULTIUSER_SETUP.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "enable_crm_firewall_6090.bat"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Real Estate CRM Desktop"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\company_logo\RealEstateCRM.ico"
Name: "{group}\Start CRM LAN Web Server"; Filename: "{app}\{#MyLanExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\company_logo\RealEstateCRM.ico"
Name: "{group}\Open CRM Web Login"; Filename: "{cmd}"; Parameters: "/c start http://127.0.0.1:6090"; WorkingDir: "{app}"; IconFilename: "{app}\company_logo\RealEstateCRM.ico"
Name: "{group}\Enable CRM Firewall Port 6090"; Filename: "{app}\enable_crm_firewall_6090.bat"; WorkingDir: "{app}"; Comment: "Right-click and choose Run as administrator if other computers cannot connect"
Name: "{group}\Multiuser LAN Setup Notes"; Filename: "{app}\LAN_MULTIUSER_SETUP.md"; WorkingDir: "{app}"
Name: "{group}\Uninstall Real Estate CRM"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Real Estate CRM"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\company_logo\RealEstateCRM.ico"; Tasks: desktopicon
Name: "{autodesktop}\CRM LAN Web Server"; Filename: "{app}\{#MyLanExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\company_logo\RealEstateCRM.ico"; Tasks: serverdesktopicon

[Run]
Filename: "{app}\{#MyLanExeName}"; Description: "Start CRM LAN web server now"; Flags: nowait postinstall skipifsilent unchecked
Filename: "{cmd}"; Parameters: "/c start http://127.0.0.1:6090"; Description: "Open CRM web login page"; Flags: nowait postinstall skipifsilent unchecked

[UninstallDelete]
Type: filesandordirs; Name: "{app}\outputs"
