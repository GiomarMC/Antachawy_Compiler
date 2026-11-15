; Instalador de Windows de Antachawi Yachay (lenguaje + entorno).
; Lo usa empaquetado/construir.py, que pasa Version, Origen, Salida y
; NombreSalida con /D.

#ifndef Version
  #define Version "0.0.0"
#endif

[Setup]
AppId={{6F1D6B2A-6C2E-4C8B-9A57-3E1A2B7C9D41}
AppName=Antachawi Yachay
AppVersion={#Version}
AppPublisher=Antachawi
AppPublisherURL=https://github.com/GiomarMC/Antachawy_Compiler
DefaultDirName={autopf}\Antachawi Yachay
DefaultGroupName=Antachawi Yachay
DisableProgramGroupPage=yes
; Se puede instalar solo para el usuario (sin permisos de administrador)
; o para todos.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
ChangesAssociations=yes
ChangesEnvironment=yes
LicenseFile={#Origen}\LICENSE.txt
SetupIconFile={#Origen}\antachawi-yachay.ico
UninstallDisplayIcon={app}\antachawi-yachay.exe
OutputDir={#Salida}
OutputBaseFilename={#NombreSalida}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "escritorio"; Description: "Crear un acceso directo en el escritorio"
Name: "ruta"; Description: "Usar el comando ""antachawi"" en la terminal (agregar al PATH)"
Name: "asociar"; Description: "Abrir los archivos .awi con Antachawi Yachay"

[Files]
Source: "{#Origen}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\Antachawi Yachay"; Filename: "{app}\antachawi-yachay.exe"
Name: "{group}\Desinstalar Antachawi Yachay"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Antachawi Yachay"; Filename: "{app}\antachawi-yachay.exe"; Tasks: escritorio

[Registry]
Root: HKA; Subkey: "Software\Classes\.awi"; ValueType: string; ValueData: "AntachawiYachay.awi"; Flags: uninsdeletevalue; Tasks: asociar
Root: HKA; Subkey: "Software\Classes\AntachawiYachay.awi"; ValueType: string; ValueData: "Programa Antachawi"; Flags: uninsdeletekey; Tasks: asociar
Root: HKA; Subkey: "Software\Classes\AntachawiYachay.awi\DefaultIcon"; ValueType: string; ValueData: "{app}\antachawi-yachay.exe,0"; Tasks: asociar
Root: HKA; Subkey: "Software\Classes\AntachawiYachay.awi\shell\open\command"; ValueType: string; ValueData: """{app}\antachawi-yachay.exe"" ""%1"""; Tasks: asociar

[Run]
Filename: "{app}\antachawi-yachay.exe"; Description: "Abrir Antachawi Yachay"; Flags: nowait postinstall skipifsilent

[Code]
function RaizDelPath(): Integer;
begin
  if IsAdminInstallMode then Result := HKEY_LOCAL_MACHINE else Result := HKEY_CURRENT_USER;
end;

function ClaveDelPath(): String;
begin
  if IsAdminInstallMode then
    Result := 'SYSTEM\CurrentControlSet\Control\Session Manager\Environment'
  else
    Result := 'Environment';
end;

procedure CambiarPath(Agregar: Boolean);
var
  Actual, Carpeta: String;
  Posicion: Integer;
begin
  Carpeta := ExpandConstant('{app}');
  if not RegQueryStringValue(RaizDelPath(), ClaveDelPath(), 'Path', Actual) then
    Actual := '';
  Posicion := Pos(';' + Uppercase(Carpeta) + ';', ';' + Uppercase(Actual) + ';');
  if Agregar and (Posicion = 0) then
  begin
    if (Actual <> '') and (Copy(Actual, Length(Actual), 1) <> ';') then
      Actual := Actual + ';';
    RegWriteExpandStringValue(RaizDelPath(), ClaveDelPath(), 'Path', Actual + Carpeta);
  end
  else if (not Agregar) and (Posicion > 0) then
  begin
    Actual := ';' + Actual + ';';
    Delete(Actual, Posicion, Length(Carpeta) + 1);
    Actual := Copy(Actual, 2, Length(Actual) - 2);
    RegWriteExpandStringValue(RaizDelPath(), ClaveDelPath(), 'Path', Actual);
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssPostInstall) and WizardIsTaskSelected('ruta') then
    CambiarPath(True);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
    CambiarPath(False);
end;
