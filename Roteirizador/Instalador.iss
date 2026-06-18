; Script de Instalação Profissional - Roteirizador BrPaving
; ---------------------------------------------------------

#define MyAppName "Roteirizador BrPaving"
#define MyAppVersion "3.0"
#define MyAppPublisher "BrPaving Engenharia"
#define MyAppExeName "RoteirizadorBrPaving.exe"

[Setup]
; ID único do App. Mantenha este mesmo ID para futuras atualizações.
AppId={{A4B5C6D7-E8F9-0011-2233-445566778899}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
; Instala na pasta "Arquivos de Programas"
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
; Nome do arquivo final do instalador que será gerado
OutputBaseFilename=Instalador_Roteirizador_v2
; Compressão máxima para o arquivo ficar leve
Compression=lzma
SolidCompression=yes
WizardStyle=modern
; Se você tiver um ícone .ico, descomente a linha abaixo:
; SetupIconFile=icone.ico

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; 1. O EXECUTÁVEL PRINCIPAL
; O Inno Setup vai buscar na pasta 'dist' onde o PyInstaller cria o arquivo.
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; 2. O BANCO DE DADOS (CRÍTICO)
; Incluímos o JSON separadamente para garantir que ele exista e possa ser substituído/editado.
Source: "banco_bairros_oficial.json"; DestDir: "{app}"; Flags: ignoreversion

; 3. OUTROS ARQUIVOS (Opcional)
; Se tiver um ícone para o atalho, inclua aqui:
; Source: "icone.ico"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
; Atalho no Menu Iniciar
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
; Atalho na Área de Trabalho (se o usuário marcar a opção)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Executar o programa automaticamente após instalar
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
// Código opcional para limpeza futura (pode deixar vazio por enquanto)
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    // Lógica para apagar arquivos de cache se necessário
  end;
end;