; Installateur Windows de Truite Retranscription (version cliente : bouton Gregre)
; Compilation : ISCC.exe installer.iss

#define MyAppName "Truite Retranscription"
#define MyAppVersion "1.3.0"
#define MyAppPublisher "YouthSeiko"
#define MyAppExeName "TruiteRetranscription.exe"
#define MyAppId "{{8C3B0F5E-2E4A-4B7F-9E51-2C7D9A6B4F10}"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\TruiteRetranscription
DefaultGroupName={#MyAppName}
DisableDirPage=yes
DisableProgramGroupPage=yes
DisableWelcomePage=no
PrivilegesRequired=lowest
OutputDir=installer_out
OutputBaseFilename=Installateur Truite Retranscription
SetupIconFile=app\icon.ico
UninstallDisplayIcon={app}\TruiteRetranscription\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
ShowLanguageDialog=no
CloseApplications=yes
RestartApplications=no
VersionInfoVersion=1.3.0.0
VersionInfoProductName={#MyAppName}
VersionInfoDescription=Installateur de {#MyAppName}
VersionInfoCompany={#MyAppPublisher}
VersionInfoCopyright=YouthSeiko

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "Creer un raccourci sur le Bureau"; GroupDescription: "Raccourcis :"; Flags: checkedonce

[Files]
Source: "TruiteRetranscription\*"; DestDir: "{app}\TruiteRetranscription"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "offer.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "TUTO - Connexion sur Gregre.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\TruiteRetranscription\{#MyAppExeName}"; WorkingDir: "{app}\TruiteRetranscription"; IconFilename: "{app}\TruiteRetranscription\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\TruiteRetranscription\{#MyAppExeName}"; WorkingDir: "{app}\TruiteRetranscription"; IconFilename: "{app}\TruiteRetranscription\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\TruiteRetranscription\{#MyAppExeName}"; Description: "Lancer {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: files; Name: "{app}\journal.txt"
Type: files; Name: "{app}\config.json"
Type: files; Name: "{app}\remote_config.json"
Type: files; Name: "{app}\relay_config.json"
Type: files; Name: "{app}\TruiteRetranscription\offer.json"
Type: files; Name: "{app}\TruiteRetranscription\journal.txt"

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    if not DirExists(ExpandConstant('{app}\transcriptions')) then
      RemoveDir(ExpandConstant('{app}'));
  end;
end;

procedure InitializeWizard();
begin
  WizardForm.WelcomeLabel2.Caption :=
    'Cet assistant va installer ' + '{#MyAppName}' + ' sur cet ordinateur.' + #13#10#13#10 +
    'Aucun dossier ne sera cree sur le Bureau : seule une icone de lancement y sera placee.' + #13#10#13#10 +
    'Une fois installe, le bouton "Connexion sur Gregre" permet de transcrire avec les ressources du PC gregre (quota de 300 minutes).';
end;
