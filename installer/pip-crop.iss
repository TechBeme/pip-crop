; PiP Crop setup for Windows. Adds PiP Crop to LibreWolf (the extension plus
; four prefs in user.js, in every profile) and to Firefox (the AutoConfig files
; in its installation folder). The uninstaller undoes both.
;
; Build (after "python tools/build.py"):
;   ISCC /DAppVersion=1.3.0 installer\pip-crop.iss
; Test build that needs no elevation, with the browsers replaced by test targets:
;   ISCC /DAppVersion=1.3.0 /DTestBuild installer\pip-crop.iss
;   pip-crop-1.3.0-setup.exe /DIR=... /LIBREWOLFDATA=<folder with profiles.ini> /FIREFOXDIRS=<dir;dir>

#ifndef AppVersion
  #error Pass the version: ISCC /DAppVersion=X.Y.Z installer\pip-crop.iss
#endif
#define AppName "PiP Crop"
#define AddonId "pip-crop@techbeme.github.io"
#define Dist "..\dist"

[Setup]
AppId={{6F0B2D4E-9C3A-4B8E-A1D7-5E2C8F4B9A13}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=TechBe
AppPublisherURL=https://github.com/TechBeme/pip-crop
AppSupportURL=https://github.com/TechBeme/pip-crop/issues
AppUpdatesURL=https://github.com/TechBeme/pip-crop/releases
AppCopyright=Copyright (c) 2026 TechBe
VersionInfoVersion={#AppVersion}
VersionInfoDescription={#AppName} setup
DefaultDirName={autopf}\{#AppName}
DisableWelcomePage=no
DisableDirPage=yes
DisableProgramGroupPage=yes
DisableReadyPage=yes
#ifdef TestBuild
PrivilegesRequired=lowest
#else
PrivilegesRequired=admin
#endif
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
WizardStyle=modern dynamic
WizardImageFile=art\wizard-202.png,art\wizard-269.png,art\wizard-336.png,art\wizard-430.png,art\wizard-538.png
WizardSmallImageFile=art\small-58.png,art\small-77.png,art\small-97.png,art\small-124.png,art\small-159.png
WizardImageFileDynamicDark=art\wizard-202.png,art\wizard-269.png,art\wizard-336.png,art\wizard-430.png,art\wizard-538.png
WizardSmallImageFileDynamicDark=art\small-58.png,art\small-77.png,art\small-97.png,art\small-124.png,art\small-159.png
SetupIconFile=art\pip-crop.ico
UninstallDisplayIcon={app}\pip-crop.ico
UninstallDisplayName={#AppName}
OutputDir={#Dist}
OutputBaseFilename=pip-crop-{#AppVersion}-setup
Compression=lzma2/max
SolidCompression=yes
ShowLanguageDialog=no
LanguageDetectionMethod=uilanguage

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "ptbr"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Messages]
en.WelcomeLabel2=This adds PiP Crop to LibreWolf and Firefox.%n%nPiP Crop crops the Picture-in-Picture video window: hold Shift and drag an edge of the window to cut black bars or any side of the video. The window shrinks with it.%n%nYou can keep your browser open while it installs.
ptbr.WelcomeLabel2=Isto adiciona o PiP Crop ao LibreWolf e ao Firefox.%n%nO PiP Crop recorta a janela de Picture-in-Picture: segure Shift e arraste uma borda da janela para cortar barras pretas ou qualquer lado do vídeo. A janela encolhe junto.%n%nVocê pode deixar o navegador aberto durante a instalação.
es.WelcomeLabel2=Esto añade PiP Crop a LibreWolf y Firefox.%n%nPiP Crop recorta la ventana de Picture-in-Picture: mantén Shift y arrastra un borde de la ventana para cortar las barras negras o cualquier lado del video. La ventana se encoge con él.%n%nPuedes dejar el navegador abierto durante la instalación.

[CustomMessages]
en.BrowsersCaption=Choose your browsers
en.BrowsersDescription=Where should PiP Crop be added?
en.BrowsersSub=PiP Crop will be added to the browsers you check:
en.NotFound=not installed
en.OpenOnce=open it once, then run this setup again
en.OtherAutoConfig=already customized by another program, can't be changed automatically
en.NothingFound=No LibreWolf or Firefox was found on this computer.%n%nInstall one of them, open it once, then run this setup again.
en.NothingSelected=Check at least one browser.
en.CloseLibreWolf=LibreWolf is using the PiP Crop files.%n%nClose every LibreWolf window, then click Retry.
en.And=and
en.Done=PiP Crop has been added to %1.%n%nTo start using it, close the browser completely and open it again. Then play any video in Picture-in-Picture, hold Shift and drag an edge of the video window.%n%nShift + double-click removes the crop.
ptbr.BrowsersCaption=Escolha os navegadores
ptbr.BrowsersDescription=Onde o PiP Crop deve ser adicionado?
ptbr.BrowsersSub=O PiP Crop será adicionado aos navegadores marcados:
ptbr.NotFound=não instalado
ptbr.OpenOnce=abra-o uma vez e rode este instalador de novo
ptbr.OtherAutoConfig=já personalizado por outro programa, não dá para alterar automaticamente
ptbr.NothingFound=Nenhum LibreWolf ou Firefox foi encontrado neste computador.%n%nInstale um deles, abra-o uma vez e rode este instalador de novo.
ptbr.NothingSelected=Marque pelo menos um navegador.
ptbr.CloseLibreWolf=O LibreWolf está usando os arquivos do PiP Crop.%n%nFeche todas as janelas do LibreWolf e clique em Repetir.
ptbr.And=e
ptbr.Done=O PiP Crop foi adicionado: %1.%n%nPara começar a usar, feche o navegador por completo e abra de novo. Depois abra qualquer vídeo em Picture-in-Picture, segure Shift e arraste uma borda da janela do vídeo.%n%nShift + duplo clique remove o corte.
es.BrowsersCaption=Elige tus navegadores
es.BrowsersDescription=¿Dónde se debe añadir PiP Crop?
es.BrowsersSub=PiP Crop se añadirá a los navegadores marcados:
es.NotFound=no instalado
es.OpenOnce=ábrelo una vez y vuelve a ejecutar este instalador
es.OtherAutoConfig=ya personalizado por otro programa, no se puede cambiar automáticamente
es.NothingFound=No se encontró LibreWolf ni Firefox en este equipo.%n%nInstala uno de ellos, ábrelo una vez y vuelve a ejecutar este instalador.
es.NothingSelected=Marca al menos un navegador.
es.CloseLibreWolf=LibreWolf está usando los archivos de PiP Crop.%n%nCierra todas las ventanas de LibreWolf y haz clic en Reintentar.
es.And=y
es.Done=PiP Crop se añadió a %1.%n%nPara empezar a usarlo, cierra el navegador por completo y vuelve a abrirlo. Luego reproduce cualquier video en Picture-in-Picture, mantén Shift y arrastra un borde de la ventana del video.%n%nShift + doble clic quita el recorte.

[Files]
Source: "{#Dist}\pip-crop-{#AppVersion}.xpi"; DestDir: "{app}"; DestName: "pip-crop.xpi"; Flags: ignoreversion
Source: "{#Dist}\firefox-autoconfig\pipcrop.js"; DestDir: "{app}\firefox"; Flags: ignoreversion
Source: "{#Dist}\firefox-autoconfig\pipcrop.cfg"; DestDir: "{app}\firefox"; Flags: ignoreversion
Source: "{#Dist}\firefox-autoconfig\defaults\pref\autoconfig.js"; DestDir: "{app}\firefox"; Flags: ignoreversion
Source: "art\pip-crop.ico"; DestDir: "{app}"; Flags: ignoreversion

[UninstallDelete]
Type: files; Name: "{app}\targets.ini"

[Code]
const
  AddonId = '{#AddonId}';
  MarkBegin = '// >>> PiP Crop';
  MarkEnd = '// <<< PiP Crop';
  PrefCount = 4;

var
  BrowserPage: TInputOptionWizardPage;
  LwProfiles, FxDirs: TStringList;
  FxItems: array of Integer;
  LwItem: Integer;
  InstalledNames: String;

function PrefName(I: Integer): String;
begin
  case I of
    0: Result := 'xpinstall.signatures.required';
    1: Result := 'extensions.experiments.enabled';
    2: Result := 'extensions.startupScanScopes';
  else
    Result := 'extensions.autoDisableScopes';
  end;
end;

function PrefValue(I: Integer): String;
begin
  case I of
    0: Result := 'false';
    1: Result := 'true';
    2: Result := '1';
  else
    Result := '14';
  end;
end;

{ ---- detection ------------------------------------------------------------ }

function LibreWolfData: String;
begin
  Result := ExpandConstant('{param:LIBREWOLFDATA|}');
  if Result = '' then
    Result := ExpandConstant('{userappdata}\librewolf');
end;

function LibreWolfInstalled: Boolean;
begin
  Result := FileExists(ExpandConstant('{commonpf32}\LibreWolf\librewolf.exe'));
  if IsWin64 and not Result then
    Result := FileExists(ExpandConstant('{commonpf64}\LibreWolf\librewolf.exe'));
end;

procedure FindLibreWolfProfiles;
var
  Ini, Section, Path: String;
  I, Gaps: Integer;
begin
  Ini := AddBackslash(LibreWolfData) + 'profiles.ini';
  if not FileExists(Ini) then
    exit;
  I := 0;
  Gaps := 0;
  while Gaps < 10 do begin
    Section := 'Profile' + IntToStr(I);
    Path := GetIniString(Section, 'Path', '', Ini);
    if Path = '' then
      Gaps := Gaps + 1
    else begin
      StringChangeEx(Path, '/', '\', True);
      if GetIniInt(Section, 'IsRelative', 1, 0, 1, Ini) = 1 then
        Path := AddBackslash(LibreWolfData) + Path;
      if DirExists(Path) and (LwProfiles.IndexOf(Path) < 0) then
        LwProfiles.Add(Path);
    end;
    I := I + 1;
  end;
end;

procedure AddFirefoxDir(Dir: String);
begin
  Dir := RemoveBackslashUnlessRoot(Trim(Dir));
  if (Dir <> '') and FileExists(AddBackslash(Dir) + 'firefox.exe') and (FxDirs.IndexOf(Dir) < 0) then
    FxDirs.Add(Dir);
end;

procedure AddFirefoxFromRegistry(RootKey: Integer);
var
  Versions: TArrayOfString;
  I: Integer;
  Dir: String;
begin
  if RegGetSubkeyNames(RootKey, 'SOFTWARE\Mozilla\Mozilla Firefox', Versions) then
    for I := 0 to GetArrayLength(Versions) - 1 do
      if RegQueryStringValue(RootKey, 'SOFTWARE\Mozilla\Mozilla Firefox\' + Versions[I] + '\Main', 'Install Directory', Dir) then
        AddFirefoxDir(Dir);
end;

procedure FindFirefoxDirs;
var
  List: String;
  P: Integer;
begin
  List := ExpandConstant('{param:FIREFOXDIRS|}');
  if List <> '' then begin
    List := List + ';';
    P := Pos(';', List);
    while P > 0 do begin
      AddFirefoxDir(Copy(List, 1, P - 1));
      Delete(List, 1, P);
      P := Pos(';', List);
    end;
    exit;
  end;
  if IsWin64 then begin
    AddFirefoxDir(ExpandConstant('{commonpf64}\Mozilla Firefox'));
    AddFirefoxDir(ExpandConstant('{commonpf64}\Firefox Developer Edition'));
    AddFirefoxDir(ExpandConstant('{commonpf64}\Firefox Nightly'));
  end;
  AddFirefoxDir(ExpandConstant('{commonpf32}\Mozilla Firefox'));
  AddFirefoxDir(ExpandConstant('{localappdata}\Mozilla Firefox'));
  AddFirefoxFromRegistry(HKLM);
  if IsWin64 then
    AddFirefoxFromRegistry(HKLM32);
  AddFirefoxFromRegistry(HKCU);
end;

{ Another program (a userChrome.js loader, for example) already uses AutoConfig. }
function ForeignAutoConfig(Dir: String): Boolean;
var
  Rec: TFindRec;
  PrefDir: String;
  S: AnsiString;
begin
  Result := False;
  PrefDir := AddBackslash(Dir) + 'defaults\pref\';
  if FindFirst(PrefDir + '*.js', Rec) then
    try
      repeat
        if LoadStringFromFile(PrefDir + Rec.Name, S) then
          if (Pos('general.config.filename', S) > 0) and (Pos('pipcrop.cfg', S) = 0) then
            Result := True;
      until Result or not FindNext(Rec);
    finally
      FindClose(Rec);
    end;
end;

{ ---- user.js / prefs.js --------------------------------------------------- }

function StripBlock(S: AnsiString): AnsiString;
var
  B, E: Integer;
begin
  B := Pos(MarkBegin, S);
  while B > 0 do begin
    E := Pos(MarkEnd, S);
    if E < B then
      break;
    E := E + Length(MarkEnd);
    while (E <= Length(S)) and ((S[E] = #13) or (S[E] = #10)) do
      E := E + 1;
    Delete(S, B, E - B);
    B := Pos(MarkBegin, S);
  end;
  Result := S;
end;

function WritePrefsBlock(UserJs: String): Boolean;
var
  S: AnsiString;
  I: Integer;
begin
  S := '';
  if FileExists(UserJs) then
    LoadStringFromFile(UserJs, S);
  S := StripBlock(S);
  if (Length(S) > 0) and (S[Length(S)] <> #10) then
    S := S + #13#10;
  S := S + MarkBegin + ': added by the PiP Crop installer, removed when you uninstall it' + #13#10;
  for I := 0 to PrefCount - 1 do
    S := S + 'user_pref("' + PrefName(I) + '", ' + PrefValue(I) + ');' + #13#10;
  S := S + MarkEnd + #13#10;
  Result := SaveStringToFile(UserJs, S, False);
end;

{ The value of a pref in prefs.js, or '' when it is not set there. The last
  line wins, as in Firefox. }
function PrefsJsValue(S: AnsiString; Name: String): String;
var
  P, E: Integer;
  Key: String;
  Rest: AnsiString;
begin
  Result := '';
  Key := 'user_pref("' + Name + '", ';
  Rest := S;
  P := Pos(Key, Rest);
  while P > 0 do begin
    Rest := Copy(Rest, P + Length(Key), Length(Rest));
    E := 1;
    while (E <= Length(Rest)) and (Rest[E] <> #10) do
      E := E + 1;
    Result := Copy(Rest, 1, E - 1);
    P := Pos(');', Result);
    if P > 0 then
      Result := Copy(Result, 1, P - 1);
    P := Pos(Key, Rest);
  end;
end;

{ Remove every user_pref line of a pref from prefs.js text. }
function RemovePrefLines(S: AnsiString; Name: String): AnsiString;
var
  P, E: Integer;
begin
  P := Pos('user_pref("' + Name + '", ', S);
  while P > 0 do begin
    E := P;
    while (E <= Length(S)) and (S[E] <> #10) do
      E := E + 1;
    Delete(S, P, E - P + 1);
    P := Pos('user_pref("' + Name + '", ', S);
  end;
  Result := S;
end;

{ A running LibreWolf keeps parent.lock open in its profile. }
function ProfileInUse(P: String): Boolean;
var
  Lock: String;
begin
  Lock := AddBackslash(P) + 'parent.lock';
  Result := FileExists(Lock) and not DeleteFile(Lock);
end;

{ ---- targets.ini: what was changed, so the uninstaller can undo it --------- }

function TargetsIni: String;
begin
  Result := ExpandConstant('{app}\targets.ini');
end;

function FindTarget(Kind, Value: String): Integer;
var
  I, N: Integer;
begin
  Result := -1;
  N := GetIniInt(Kind, 'Count', 0, 0, 100000, TargetsIni);
  for I := 0 to N - 1 do
    if CompareText(GetIniString(Kind, 'Item' + IntToStr(I), '', TargetsIni), Value) = 0 then
      Result := I;
end;

function AddTarget(Kind, Value: String): Integer;
begin
  Result := FindTarget(Kind, Value);
  if Result < 0 then begin
    Result := GetIniInt(Kind, 'Count', 0, 0, 100000, TargetsIni);
    SetIniString(Kind, 'Item' + IntToStr(Result), Value, TargetsIni);
    SetIniInt(Kind, 'Count', Result + 1, TargetsIni);
  end;
end;

{ ---- install -------------------------------------------------------------- }

function CopyFileRetry(Src, Dst, Retry: String): Boolean;
begin
  Result := FileCopy(Src, Dst, False);
  while not Result do begin
    if SuppressibleMsgBox(Retry, mbError, MB_RETRYCANCEL, IDCANCEL) <> IDRETRY then
      exit;
    Result := FileCopy(Src, Dst, False);
  end;
end;

function InstallLibreWolfProfile(P: String): Boolean;
var
  Idx, I: Integer;
  S: AnsiString;
  Section, Old: String;
begin
  Result := False;
  ForceDirectories(AddBackslash(P) + 'extensions');
  if not CopyFileRetry(ExpandConstant('{app}\pip-crop.xpi'), AddBackslash(P) + 'extensions\' + AddonId + '.xpi', CustomMessage('CloseLibreWolf')) then
    exit;
  Idx := FindTarget('LibreWolf', P);
  if Idx < 0 then begin
    { first install in this profile: remember the prefs' previous values }
    Idx := AddTarget('LibreWolf', P);
    Section := 'LibreWolf' + IntToStr(Idx);
    S := '';
    LoadStringFromFile(AddBackslash(P) + 'prefs.js', S);
    for I := 0 to PrefCount - 1 do begin
      Old := PrefsJsValue(S, PrefName(I));
      if Old = '' then
        Old := '-';
      SetIniString(Section, PrefName(I), Old, TargetsIni);
    end;
  end;
  Result := WritePrefsBlock(AddBackslash(P) + 'user.js');
end;

function InstallFirefox(Dir: String): Boolean;
var
  Src: String;
begin
  Src := ExpandConstant('{app}\firefox\');
  ForceDirectories(AddBackslash(Dir) + 'defaults\pref');
  Result := FileCopy(Src + 'autoconfig.js', AddBackslash(Dir) + 'defaults\pref\autoconfig.js', False)
    and FileCopy(Src + 'pipcrop.cfg', AddBackslash(Dir) + 'pipcrop.cfg', False)
    and FileCopy(Src + 'pipcrop.js', AddBackslash(Dir) + 'pipcrop.js', False);
  if Result then
    AddTarget('Firefox', Dir);
end;

function AddName(Names, Name: String): String;
begin
  if Names = '' then
    Result := Name
  else
    Result := Names + ' ' + CustomMessage('And') + ' ' + Name;
end;

{ ---- wizard ---------------------------------------------------------------- }

function InitializeSetup: Boolean;
begin
  LwProfiles := TStringList.Create;
  FxDirs := TStringList.Create;
  FindLibreWolfProfiles;
  FindFirefoxDirs;
  Result := (LwProfiles.Count > 0) or (FxDirs.Count > 0);
  if not Result then
    SuppressibleMsgBox(CustomMessage('NothingFound'), mbError, MB_OK, IDOK);
end;

procedure InitializeWizard;
var
  I, Idx: Integer;
begin
  BrowserPage := CreateInputOptionPage(wpWelcome, CustomMessage('BrowsersCaption'),
    CustomMessage('BrowsersDescription'), CustomMessage('BrowsersSub'), False, False);
  LwItem := -1;
  if LwProfiles.Count > 0 then begin
    LwItem := BrowserPage.Add('LibreWolf');
    BrowserPage.Values[LwItem] := True;
  end else begin
    if LibreWolfInstalled then
      Idx := BrowserPage.Add('LibreWolf (' + CustomMessage('OpenOnce') + ')')
    else
      Idx := BrowserPage.Add('LibreWolf (' + CustomMessage('NotFound') + ')');
    BrowserPage.CheckListBox.ItemEnabled[Idx] := False;
  end;
  SetArrayLength(FxItems, FxDirs.Count);
  for I := 0 to FxDirs.Count - 1 do begin
    if ForeignAutoConfig(FxDirs[I]) then begin
      Idx := BrowserPage.Add('Firefox - ' + FxDirs[I] + ' (' + CustomMessage('OtherAutoConfig') + ')');
      BrowserPage.CheckListBox.ItemEnabled[Idx] := False;
      FxItems[I] := -1;
    end else begin
      FxItems[I] := BrowserPage.Add('Firefox - ' + FxDirs[I]);
      BrowserPage.Values[FxItems[I]] := True;
    end;
  end;
  if FxDirs.Count = 0 then begin
    Idx := BrowserPage.Add('Firefox (' + CustomMessage('NotFound') + ')');
    BrowserPage.CheckListBox.ItemEnabled[Idx] := False;
  end;
end;

function AnySelected: Boolean;
var
  I: Integer;
begin
  Result := (LwItem >= 0) and BrowserPage.Values[LwItem];
  for I := 0 to GetArrayLength(FxItems) - 1 do
    if (FxItems[I] >= 0) and BrowserPage.Values[FxItems[I]] then
      Result := True;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if (CurPageID = BrowserPage.ID) and not AnySelected then begin
    SuppressibleMsgBox(CustomMessage('NothingSelected'), mbError, MB_OK, IDOK);
    Result := False;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  I: Integer;
  Names: String;
begin
  if CurStep <> ssPostInstall then
    exit;
  Names := '';
  if (LwItem >= 0) and BrowserPage.Values[LwItem] then begin
    for I := 0 to LwProfiles.Count - 1 do
      InstallLibreWolfProfile(LwProfiles[I]);
    Names := AddName(Names, 'LibreWolf');
  end;
  for I := 0 to FxDirs.Count - 1 do
    if (FxItems[I] >= 0) and BrowserPage.Values[FxItems[I]] then
      if InstallFirefox(FxDirs[I]) and (Pos('Firefox', Names) = 0) then
        Names := AddName(Names, 'Firefox');
  InstalledNames := Names;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  { no Ready page: the browser choice is the last step before installing }
  if CurPageID = BrowserPage.ID then
    WizardForm.NextButton.Caption := SetupMessage(msgButtonInstall);
  if (CurPageID = wpFinished) and (InstalledNames <> '') then begin
    WizardForm.FinishedLabel.Caption := FmtMessage(CustomMessage('Done'), [InstalledNames]);
    WizardForm.AdjustLabelHeight(WizardForm.FinishedLabel);
  end;
end;

{ ---- uninstall ------------------------------------------------------------- }

function InitializeUninstall: Boolean;
var
  I, N: Integer;
  P, Ini: String;
begin
  Result := True;
  Ini := ExpandConstant('{app}\targets.ini');
  N := GetIniInt('LibreWolf', 'Count', 0, 0, 100000, Ini);
  for I := 0 to N - 1 do begin
    P := GetIniString('LibreWolf', 'Item' + IntToStr(I), '', Ini);
    while (P <> '') and ProfileInUse(P) do
      if SuppressibleMsgBox(CustomMessage('CloseLibreWolf'), mbError, MB_RETRYCANCEL, IDCANCEL) <> IDRETRY then begin
        Result := False;
        exit;
      end;
  end;
end;

procedure RemoveFromLibreWolfProfile(P: String; Idx: Integer);
var
  S: AnsiString;
  I: Integer;
  Old, Section: String;
begin
  DeleteFile(AddBackslash(P) + 'extensions\' + AddonId + '.xpi');
  if LoadStringFromFile(AddBackslash(P) + 'user.js', S) then begin
    S := StripBlock(S);
    if Trim(S) = '' then
      DeleteFile(AddBackslash(P) + 'user.js')
    else
      SaveStringToFile(AddBackslash(P) + 'user.js', S, False);
  end;
  { user.js values end up in prefs.js too: put back what was there before }
  Section := 'LibreWolf' + IntToStr(Idx);
  if LoadStringFromFile(AddBackslash(P) + 'prefs.js', S) then begin
    for I := 0 to PrefCount - 1 do begin
      Old := GetIniString(Section, PrefName(I), '-', TargetsIni);
      S := RemovePrefLines(S, PrefName(I));
      if Old <> '-' then
        S := S + 'user_pref("' + PrefName(I) + '", ' + Old + ');' + #10;
    end;
    SaveStringToFile(AddBackslash(P) + 'prefs.js', S, False);
  end;
  { make LibreWolf rescan its add-ons at the next start, so it forgets PiP Crop }
  DeleteFile(AddBackslash(P) + 'addonStartup.json.lz4');
end;

procedure RemoveFromFirefox(Dir: String);
var
  S: AnsiString;
  F: String;
begin
  F := AddBackslash(Dir) + 'defaults\pref\autoconfig.js';
  if LoadStringFromFile(F, S) and (Pos('pipcrop.cfg', S) > 0) then
    DeleteFile(F);
  DeleteFile(AddBackslash(Dir) + 'pipcrop.cfg');
  DeleteFile(AddBackslash(Dir) + 'pipcrop.js');
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  I, N: Integer;
  P: String;
begin
  if CurUninstallStep <> usUninstall then
    exit;
  N := GetIniInt('LibreWolf', 'Count', 0, 0, 100000, TargetsIni);
  for I := 0 to N - 1 do begin
    P := GetIniString('LibreWolf', 'Item' + IntToStr(I), '', TargetsIni);
    if P <> '' then
      RemoveFromLibreWolfProfile(P, I);
  end;
  N := GetIniInt('Firefox', 'Count', 0, 0, 100000, TargetsIni);
  for I := 0 to N - 1 do begin
    P := GetIniString('Firefox', 'Item' + IntToStr(I), '', TargetsIni);
    if P <> '' then
      RemoveFromFirefox(P);
  end;
end;
