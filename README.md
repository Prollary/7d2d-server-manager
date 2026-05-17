# 七日杀服务器管理器 | 7D2D Server Manager

> 面向普通玩家的七日杀服务端一站式管理工具，同时提供 **桌面版（EXE）** 和 **Web 版（可部署到服务器、外网访问）** 两种形式。

---

## 功能概览

| 模块 | 描述 |
|---|---|
| 🖥 服务器控制台 | 一键启动/停止/重启，实时日志流，颜色高亮 |
| 👥 在线玩家管理 | 查看在线玩家列表，**右键菜单**执行踢出/封禁/管理员操作 |
| 🔧 模组管理 | 上传 ZIP 模组，一键启用/禁用/删除 |
| 🗺 地图管理 | 上传地图包、切换地图（自动写入 serverconfig.xml）|
| ⚙ 服务器设置 | 可视化编辑全部 serverconfig.xml 参数，支持 **一键汉化注释** |
| 🛠 辅助工具 | 端口检测、防火墙自动开放、存档一键 ZIP 备份 |
| 🔩 系统设置 | 配置服务端路径、Web 端口（多端口支持）、备份目录 |

---

## 快速开始

### 桌面版（免安装 EXE）

```
双击 dist/7DaysToDieServerManager.exe
```

无需安装 Python，双击即用。

---

### Web 版（可远程/外网访问）

#### Windows 一键部署

```bat
双击运行  deploy.bat
```

自动完成：检测 Python → 安装依赖 → 生成配置 → 可选开放防火墙 → 启动并打开浏览器。

#### Linux 服务器

```bash
pip3 install fastapi "uvicorn[standard]" pyyaml python-multipart websockets
python3 -m web.app
```

#### 访问地址

| 场景 | 地址 |
|---|---|
| 本机 | http://localhost:8888 |
| 局域网 | http://[内网IP]:8888 |
| 外网 | http://[公网IP]:8888 |
| API 文档（Swagger） | http://localhost:8888/api/docs |

> 默认端口 **8888**，可在 `web_config.yaml` 或【系统设置】页面修改。外网访问需在云服务器安全组/防火墙放行对应端口。

---

## 配置文件 `web_config.yaml`

```yaml
web:
  host: "0.0.0.0"    # 监听所有 IP
  port: 8888          # Web 面板端口，按需修改（避免使用 80）

server:
  dir: "C:/7DaysToDieServer"
  config_path: "C:/7DaysToDieServer/serverconfig.xml"
  backup_dir: "D:/Backups/7D2D"
  saves_dir: "C:/7DaysToDieServer/Saves"

rcon:
  password: "your_telnet_password"  # 与 serverconfig.xml 中 TelnetPassword 一致
  port: 8081
```

首次使用可直接在【系统设置】页面填写路径，保存后无需重启立即生效。

---

## 在线玩家管理

**前提**：需在 serverconfig.xml 中开启 Telnet（管理器通过 Telnet 与服务器通信）。

### 开启步骤

1. 【服务器设置】→ `TelnetEnabled` 设为 `true`
2. 设置 `TelnetPort`（默认 8081）和 `TelnetPassword`
3. 保存配置并重启服务器
4. 【系统设置】→ Rcon 密码填入相同密码，保存

### 右键菜单操作

| 操作 | 说明 |
|---|---|
| 踢出 | 将玩家踢出服务器，可填写原因 |
| 封禁 | 封禁玩家，支持指定时长（`60 minutes` / `7 days` / `perm`）|
| 设为管理员 | 赋予玩家管理员权限（等级 0）|
| 撤销管理员 | 移除玩家管理员权限 |
| 解除封禁 | 解除对玩家的封禁 |

---

## 配置文件汉化

【服务器设置】→ 点击「📝 一键汉化配置文件」：

- 为 `serverconfig.xml` 每个配置项自动添加中文注释说明
- **汉化前自动备份**原始文件到备份目录
- **本地处理，无需联网**，使用内置 `core/config_i18n.json` 字典（覆盖 60+ 参数）

汉化效果示例：
```xml
<!-- [汉化] 血月频率（天）: 每隔多少游戏天发生一次血月，0表示关闭血月 -->
<property name="BloodMoonFrequency" value="7" />
```

---

## API 接口

启动后访问 `/api/docs` 查看完整 Swagger UI。核心接口：

```
服务器控制
  GET  /api/server/status          状态查询
  POST /api/server/start           启动
  POST /api/server/stop            优雅停止（Rcon → 进程终止）
  POST /api/server/force-stop      强制终止
  POST /api/server/restart         重启
  GET  /api/server/players         在线玩家列表
  POST /api/server/players/action  玩家操作（kick/ban/admin/unadmin/unban）

模组与地图
  GET/POST/PUT/DELETE /api/mods/*
  GET/POST/PUT/DELETE /api/worlds/*

配置管理
  GET  /api/config/server          读取全部参数
  POST /api/config/server          保存参数
  POST /api/config/hanize          一键汉化
  GET  /api/config/paths           读取路径配置
  POST /api/config/paths           保存路径配置

辅助工具
  GET  /api/tools/network          端口检测
  POST /api/tools/firewall         防火墙开放
  POST /api/tools/backup           存档备份

实时通信
  WS   /ws/logs                    服务器日志 WebSocket 流
```

---

## Linux 服务部署（systemd）

```ini
# /etc/systemd/system/7d2d-manager.service
[Unit]
Description=7D2D Server Manager
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/7d2d-server-manager
ExecStart=/usr/bin/python3 -m web.app
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload && sudo systemctl enable --now 7d2d-manager
```

---

## 项目结构

```
7d2d-server-manager/
├── core/                    # 核心逻辑（桌面/Web 共用）
│   ├── server.py            # 进程控制 + Telnet 玩家管理
│   ├── config.py            # serverconfig.xml 读写 + 汉化
│   ├── mod.py               # 模组/地图管理
│   ├── network.py           # 端口检测/防火墙
│   ├── backup.py            # 存档备份
│   └── config_i18n.json     # 汉化字典
├── web/                     # Web 版 (FastAPI)
│   ├── app.py               # 主应用 + WebSocket 广播
│   ├── state.py             # 全局单例
│   └── api/                 # REST 路由
├── web/static/              # 前端（Vue 3 CDN + 原生 HTML/CSS/JS）
├── ui/                      # 桌面版 UI (PyQt5)
├── web_config.yaml          # Web 版配置
├── deploy.bat               # Windows 一键部署
├── start_web.bat / .sh      # 启动脚本
└── dist/7DaysToDieServerManager.exe
```

## 技术栈

| 层次 | 技术 |
|---|---|
| 后端 | Python 3.8+, FastAPI, Uvicorn |
| 实时通信 | WebSocket（日志）, Telnet（Rcon 玩家管理）|
| 前端 | Vue 3 (CDN), Axios, 纯 HTML/CSS |
| 桌面版 | PyQt5, PyInstaller |
| 配置 | YAML, XML（ElementTree）|

---

## 常见问题

**玩家列表为空？** → 确认 `TelnetEnabled=true`，`TelnetPassword` 已设置，系统设置中 Rcon 密码与之一致。

**外网无法访问？** → 检查：① 云服务器安全组/防火墙已放行端口；② `web_config.yaml` 中 host 为 `0.0.0.0`。

**汉化后 XML 报错？** → 汉化前已自动备份到备份目录，可手动恢复原文件。

**日志不显示？** → WebSocket 需要现代浏览器（Chrome/Edge/Firefox），确认页面 URL 端口正确。

---

*免费使用 · 非商业用途 · Python 3.8 / FastAPI / Vue 3*
