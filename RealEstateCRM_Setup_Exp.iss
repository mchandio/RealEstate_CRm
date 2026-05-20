#define MyAppName "Real Estate CRM (Experimental)"
#define MyAppVersion "3.0.5"
#define MyAppPublisher "Muhammad Siddique"
#define MyAppURL "mailto:info@msxhan.online"
#define MyAppExeName "RealEstateCRM_Qt_Exp.exe"

[Setup]
AppId={{F1F861C2-1549-4D29-BD8C-225E3F92D8B8}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\Real Estate CRM Exp
DefaultGroupName=Real Estate CRM Exp
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=RealEstateCRM_Qt_Exp_Setup_v{#MyAppVersion}
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
VersionInfoDescription=Real Estate CRM Experimental Windows Installer
VersionInfoProductName={#MyAppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut for the desktop CRM"; GroupDescription: "Shortcuts:"

[Dirs]
Name: "{app}\outputs"
Name: "{app}\company_logo"

[Files]
Source: "installer_staging\dist\RealEstateCRM_Qt_Exp\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "installer_staging\real_estate_crm_exp.db"; DestDir: "{app}"; Flags: onlyifdoesntexist uninsneveruninstall skipifsourcedoesntexist
Source: "company_logo\RealEstateCRM.ico"; DestDir: "{app}\company_logo"; Flags: ignoreversion
Source: "company_logo\RealEstateCRM_logo.png"; DestDir: "{app}\company_logo"; Flags: ignoreversion

[Icons]
Name: "{group}\Real Estate CRM Desktop (Exp)"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\company_logo\RealEstateCRM.ico"
Name: "{group}\Uninstall Real Estate CRM (Exp)"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Real Estate CRM (Exp)"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\company_logo\RealEstateCRM.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Real Estate CRM now"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\outputs"
