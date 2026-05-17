; ============================================================
;  七日杀联机平台  -  Inno Setup 安装脚本  v2.0
; ============================================================

[Setup]
AppName=七日杀联机平台
AppVersion=2.0
AppPublisher=7D2D Platform
DefaultDirName={sd}\7DaysToDie_Manager
DefaultGroupName=七日杀联机平台
OutputBaseFilename=7D2D_Platform_Setup
Compression=lzma2/ultra64
SolidCompression=yes
PrivilegesRequired=admin
WizardStyle=modern
DisableWelcomePage=no
DisableDirPage=no
DisableReadyPage=no
UninstallDisplayIcon={app}\7D2D_WebManager.exe
MinVersion=6.1sp1

[Files]
Source: "dist\7D2D_WebManager\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\七日杀联机平台";      Filename: "{app}\7D2D_WebManager.exe"
Name: "{group}\卸载七日杀联机平台";  Filename: "{uninstallexe}"
Name: "{autodesktop}\七日杀联机平台"; Filename: "{app}\7D2D_WebManager.exe"; Comment: "七日杀联机平台管理面板"

[Run]
Filename: "{app}\7D2D_WebManager.exe"; Description: "立即启动七日杀联机平台"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: files;     Name: "{app}\web_config.yaml"
Type: files;     Name: "{app}\users.json"
Type: files;     Name: "{app}\sessions.json"
Type: dirifempty; Name: "{app}"

[Code]

var
  NetPage: TInputQueryWizardPage;

{ ── 向导页：外网 IP 与面板端口 ── }
procedure InitializeWizard;
begin
  NetPage := CreateInputQueryPage(wpSelectDir,
    'Web 面板网络配置',
    '设置外网访问地址与端口',
    '请填写服务器的外网 IP 和面板端口。' + #13#10 +
    '安装完成后可通过外网 IP + 端口访问管理面板。');

  NetPage.Add('服务器外网 IP:', False);
  NetPage.Add('面板端口（默认 8888）:', False);

  NetPage.Values[0] := '';
  NetPage.Values[1] := '8888';
end;

{ ── 验证端口为数字 ── }
function NextButtonClick(CurPageID: Integer): Boolean;
var
  PortStr: String;
  PortNum: Integer;
begin
  Result := True;
  if CurPageID = NetPage.ID then
  begin
    PortStr := Trim(NetPage.Values[1]);
    if PortStr = '' then
      NetPage.Values[1] := '8888'
    else
    begin
      PortNum := StrToIntDef(PortStr, -1);
      if (PortNum < 1024) or (PortNum > 65535) then
      begin
        MsgBox('端口号必须在 1024 ~ 65535 之间，请重新填写。', mbError, MB_OK);
        Result := False;
      end;
    end;
  end;
end;

{ ── 获取配置值（IP 仅用于显示，不写入监听配置） ── }
function GetDisplayIP: String;
begin
  Result := Trim(NetPage.Values[0]);
  if Result = '' then Result := '服务器公网IP';
end;

function GetWebPort: String;
begin
  Result := Trim(NetPage.Values[1]);
  if Result = '' then Result := '8888';
end;

{ ── 写入 web_config.yaml（监听地址固定 0.0.0.0） ── }
procedure WriteWebConfig;
var
  Path: String;
  Lines: TStringList;
begin
  Path := ExpandConstant('{app}\web_config.yaml');
  Lines := TStringList.Create;
  try
    Lines.Add('web:');
    Lines.Add('  host: 0.0.0.0');
    Lines.Add('  port: ' + GetWebPort);
    Lines.Add('server:');
    Lines.Add('  dir: ''''');
    Lines.Add('  config_path: ''''');
    Lines.Add('rcon:');
    Lines.Add('  password: ''''');
    Lines.Add('  port: 8081');
    Lines.SaveToFile(Path);
  finally
    Lines.Free;
  end;
end;

{ ── 防火墙规则 ── }
procedure AddFirewallRule(Port: String; RuleName: String);
var RC: Integer;
begin
  Exec('netsh', 'advfirewall firewall delete rule name="' + RuleName + '"',
       '', SW_HIDE, ewWaitUntilTerminated, RC);
  Exec('netsh',
       'advfirewall firewall add rule name="' + RuleName +
       '" dir=in action=allow protocol=TCP localport=' + Port,
       '', SW_HIDE, ewWaitUntilTerminated, RC);
end;

{ ── 安装后处理 ── }
procedure CurStepChanged(CurStep: TSetupStep);
var
  Port: String;
  DisplayIP: String;
begin
  if CurStep = ssPostInstall then
  begin
    Port := GetWebPort;
    WriteWebConfig;
    AddFirewallRule(Port, '7D2D_WebPanel');
  end;

  if CurStep = ssDone then
  begin
    Port     := GetWebPort;
    DisplayIP := GetDisplayIP;
    MsgBox(
      '七日杀联机平台安装完成！' + #13#10 + #13#10 +
      '面板访问地址：' + #13#10 +
      '  本机：http://127.0.0.1:' + Port + #13#10 +
      '  外网：http://' + DisplayIP + ':' + Port + #13#10 + #13#10 +
      '首次使用步骤：' + #13#10 +
      '  1. 打开上方地址，注册账号并登录' + #13#10 +
      '  2. 进入【系统设置】配置七日杀服务端路径' + #13#10 + #13#10 +
      '提示：Windows 防火墙已自动放行端口 ' + Port + #13#10 +
      '云服务器（阿里云/腾讯云）还需在安全组中手动放行 TCP ' + Port + ' 端口。',
      mbInformation, MB_OK
    );
  end;
end;
