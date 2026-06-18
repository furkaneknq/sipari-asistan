; ====================================================================
;  Sipariş Asistanı - Inno Setup script
;  Inno Setup 6.x ile derleyin (build.bat otomatik çağırır):
;     "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
;  Çıktı: installer\windows\Output\SiparisAsistaniSetup.exe
; ====================================================================

#define AppName        "Sipariş Asistanı"
#define AppVersion     "0.1.0"
#define AppPublisher   "Sipariş Asistanı"
#define AppExeName     "SiparisAsistani.exe"
#define AppId          "{{A2C5F7E4-9B3D-4E12-A1F2-3D8E6C5B9A21}"

[Setup]
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL=
DefaultDirName={autopf}\SiparisAsistani
DefaultGroupName=Sipariş Asistanı
DisableProgramGroupPage=no
LicenseFile=
OutputDir=Output
OutputBaseFilename=SiparisAsistaniSetup
Compression=lzma2/ultra
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
SetupIconFile=app.ico
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName} {#AppVersion}
ShowLanguageDialog=auto
AllowNoIcons=yes

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1

[InstallDelete]
; Güncelleme kurulumunda eski dosyaları temizle (.env hariç — Code bölümünde yedeklenir)
Type: filesandordirs; Name: "{app}\*"

[Files]
; Ana uygulama klasörü (PyInstaller çıktısı)
Source: "..\..\dist\SiparisAsistani\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; .env şablonu (kullanıcı düzenlesin diye)
Source: "..\..\order_tracking\.env.example"; DestDir: "{app}"; Flags: ignoreversion
; SQL migration dosyaları (referans olarak)
Source: "..\..\database\sql\*.sql"; DestDir: "{app}\sql"; Flags: ignoreversion

[Dirs]
; Kullanıcı bazlı .env için klasör (programın da yazabileceği yer)
Name: "{userappdata}\SiparisAsistani"; Flags: uninsneveruninstall

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\{#AppExeName}"
Name: "{group}\Ayarları Düzenle (.env)"; Filename: "notepad.exe"; Parameters: """{app}\.env"""; Comment: "Supabase URL/Key ve yazıcı ayarları"
Name: "{group}\Kurulum Klasörünü Aç"; Filename: "{app}"; IconFilename: "{app}\{#AppExeName}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
; Kurulum sonrası ayar dosyasını aç (kullanıcı Supabase URL/Key girsin)
Filename: "notepad.exe"; Parameters: """{app}\.env"""; Description: "Ayarları şimdi düzenle (.env)"; Flags: postinstall skipifsilent unchecked
; Programı doğrudan başlat
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
{
  Kurulum öncesi: önceki sürüm çalışıyorsa kullanıcıyı uyar.
}
var
  EnvBackupPath: String;

function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;
  if Exec('tasklist.exe', '/FI "IMAGENAME eq SiparisAsistani.exe"', '',
          SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    // sessiz devam — gerçek kontrol için ek IPC gerekir
  end;
end;

{
  Kurulum öncesi: .env varsa geçici yere yedekle ([InstallDelete] silmeden önce).
}
procedure CurStepChanged(CurStep: TSetupStep);
var
  EnvSrc, EnvDst: String;
begin
  if CurStep = ssInstall then
  begin
    EnvSrc := ExpandConstant('{app}\.env');
    EnvBackupPath := ExpandConstant('{tmp}\.env.backup');
    if FileExists(EnvSrc) then
      FileCopy(EnvSrc, EnvBackupPath, False);
  end;

  { Kurulum sonrası: .env geri yükle veya .env.example'dan oluştur. }
  if CurStep = ssPostInstall then
  begin
    EnvDst := ExpandConstant('{app}\.env');
    if (EnvBackupPath <> '') and FileExists(EnvBackupPath) then
    begin
      FileCopy(EnvBackupPath, EnvDst, False);
      DeleteFile(EnvBackupPath);
    end
    else
    begin
      EnvSrc := ExpandConstant('{app}\.env.example');
      if FileExists(EnvSrc) and not FileExists(EnvDst) then
        FileCopy(EnvSrc, EnvDst, False);
    end;
  end;
end;

{
  Kaldırma: kullanıcı .env'sini koru (yedekle).
}
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  EnvSrc, EnvDst: String;
begin
  if CurUninstallStep = usUninstall then
  begin
    EnvSrc := ExpandConstant('{app}\.env');
    EnvDst := ExpandConstant('{userappdata}\SiparisAsistani\.env.backup');
    if FileExists(EnvSrc) then
      FileCopy(EnvSrc, EnvDst, False);
  end;
end;
