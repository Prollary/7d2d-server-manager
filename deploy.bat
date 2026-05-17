@echo off
chcp 65001 >nul
title 7D2D Server Manager - 一键部署

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║      七日杀服务器管理器  -  一键部署向导             ║
echo  ║      7D2D Server Manager  -  Deploy Wizard           ║
echo  ╚══════════════════════════════════════════════════════╝
echo.

:: ── 检测 Python ─────────────────────────────────────────────────────────────
echo  [1/5] 检测 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ╔══ 未找到 Python! ══════════════════════════════════════╗
    echo  ║                                                        ║
    echo  ║  请先安装 Python 3.8 或更高版本:                       ║
    echo  ║  https://www.python.org/downloads/                     ║
    echo  ║                                                        ║
    echo  ║  安装时请勾选 "Add Python to PATH"                     ║
    echo  ╚════════════════════════════════════════════════════════╝
    echo.
    echo  是否自动通过 winget 安装 Python?（需要 Windows 10/11）
    set /p INSTALL_PY= 输入 Y 自动安装，其他键跳过:
    if /i "%INSTALL_PY%"=="Y" (
        echo  正在通过 winget 安装 Python 3.11...
        winget install Python.Python.3.11 --silent --accept-package-agreements
        if errorlevel 1 (
            echo  自动安装失败，请手动下载 Python 后重新运行此脚本。
            pause & exit /b 1
        )
    ) else (
        pause & exit /b 1
    )
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo  ✓ %%v

:: ── 安装依赖 ────────────────────────────────────────────────────────────────
echo.
echo  [2/5] 安装 Python 依赖包...
pip install fastapi "uvicorn[standard]" pyyaml python-multipart websockets -q
if errorlevel 1 (
    echo  依赖安装失败，请检查网络连接。
    pause & exit /b 1
)
echo  ✓ 依赖安装完成

:: ── 检查配置文件 ─────────────────────────────────────────────────────────────
echo.
echo  [3/5] 检查配置文件...
if not exist web_config.yaml (
    echo  创建默认配置文件 web_config.yaml...
    (
        echo web:
        echo   host: 0.0.0.0
        echo   port: 8888
        echo server:
        echo   dir: ''
        echo   config_path: ''
        echo   backup_dir: ''
        echo   saves_dir: ''
        echo rcon:
        echo   password: ''
        echo   port: 8081
    ) > web_config.yaml
)
echo  ✓ 配置文件就绪

:: ── 读取端口配置 ─────────────────────────────────────────────────────────────
set PORT=8888
for /f "tokens=2 delims=: " %%p in ('findstr "port:" web_config.yaml 2^>nul') do set PORT=%%p

:: ── 防火墙设置（可选）───────────────────────────────────────────────────────
echo.
echo  [4/5] 防火墙配置（可选）
echo  是否自动开放 Web 管理面板端口 %PORT%？（需要管理员权限）
set /p OPEN_FW= 输入 Y 开放端口，其他键跳过:
if /i "%OPEN_FW%"=="Y" (
    netsh advfirewall firewall add rule name="7D2D Manager Web" dir=in action=allow protocol=TCP localport=%PORT% >nul 2>&1
    if errorlevel 1 (
        echo  ⚠ 需要以管理员身份运行才能开放防火墙端口
    ) else (
        echo  ✓ 防火墙端口 %PORT% 已开放
    )
)

:: ── 启动服务 ─────────────────────────────────────────────────────────────────
echo.
echo  [5/5] 启动 Web 服务...
echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║  访问地址（本机）： http://localhost:%PORT%          ║
echo  ║  访问地址（局域网）：http://[本机IP]:%PORT%          ║
echo  ║  访问地址（外网）：  http://[公网IP]:%PORT%          ║
echo  ║  API 文档：         http://localhost:%PORT%/api/docs ║
echo  ╚══════════════════════════════════════════════════════╝
echo.
echo  首次启动请在管理面板【系统设置】中配置服务端路径
echo  按 Ctrl+C 停止服务
echo.

:: 延迟 2 秒后自动打开浏览器
start "" timeout /t 2 /nobreak >nul ^& start http://localhost:%PORT%

python -m web.app
pause
