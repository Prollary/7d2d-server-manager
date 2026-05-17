import asyncio
import threading
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


# ── 崩溃检测 ──

@router.get("/crash")
def detect_crash():
    """扫描近期日志，匹配已知崩溃模式并返回诊断结果"""
    from web.state import log_history
    from core.crash_db import CRASH_PATTERNS

    recent = list(log_history)
    combined = "\n".join(recent[-200:]).lower()

    hits = []
    for p in CRASH_PATTERNS:
        matched_kw = next((kw for kw in p["keywords"] if kw.lower() in combined), None)
        if matched_kw:
            hits.append({
                "id":       p["id"],
                "level":    p["level"],
                "cause":    p["cause"],
                "solution": p["solution"],
                "keyword":  matched_kw,
            })

    if not hits:
        return {"found": False, "message": "未检测到已知崩溃模式，服务器运行正常"}
    return {"found": True, "issues": hits}


# ── 回档 ──

class RollbackBody(BaseModel):
    tag: str  # 5min | 30min | 3h | daily

@router.post("/rollback")
def rollback(body: RollbackBody):
    """回档到指定时间点的快照"""
    from web.state import server_controller, app_config
    from core.snapshot import SnapshotManager

    if server_controller and server_controller.is_running():
        return {"success": False, "message": "请先停止服务器再执行回档"}

    sc = app_config.get("server", {})
    saves_dir = _get_saves_dir(sc.get("dir", ""))
    if not saves_dir:
        return {"success": False, "message": "未找到存档目录（Saves），请先配置服务端路径"}

    mgr = SnapshotManager(saves_dir)
    ok, msg = mgr.rollback(body.tag)
    return {"success": ok, "message": msg}


@router.get("/snapshots")
def list_snapshots():
    """列出可用快照"""
    from web.state import app_config
    from core.snapshot import SnapshotManager

    sc = app_config.get("server", {})
    saves_dir = _get_saves_dir(sc.get("dir", ""))
    if not saves_dir:
        return {"snapshots": {}}

    mgr = SnapshotManager(saves_dir)
    return {"snapshots": mgr.list_snapshots()}


def _get_saves_dir(server_dir: str) -> str:
    """推断存档目录（server_dir/Saves）"""
    import os
    if not server_dir:
        return ""
    candidate = os.path.join(server_dir, "Saves")
    os.makedirs(candidate, exist_ok=True)
    return candidate


# ── 控制台指令 ──

class CommandBody(BaseModel):
    command: str

@router.post("/command")
def send_command(body: CommandBody):
    """通过 Telnet/RCON 向服务器发送指令"""
    from web.state import server_controller
    if not server_controller:
        raise HTTPException(503, "服务未初始化")
    if not server_controller.is_running():
        raise HTTPException(400, "服务器未在运行")
    cmd = body.command.strip()
    if not cmd:
        raise HTTPException(400, "指令不能为空")
    result = server_controller.execute_rcon(cmd, wait=1.5)
    if result is None:
        raise HTTPException(500, "Telnet 未连接，请检查 TelnetEnabled 和 TelnetPassword 配置")
    return {"success": True, "output": result}


@router.get("/stream")
async def stream_logs():
    """SSE 实时日志推送"""
    import web.state as _state  # 模块引用，读属性总能拿到最新值

    async def generate():
        last_seq = _state.log_sequence
        for line in list(_state.log_history):
            yield f"data: {line}\n\n"

        while True:
            await asyncio.sleep(0.5)
            cur_seq = _state.log_sequence   # 每次都从模块属性读，不是旧的 int 副本
            if cur_seq > last_seq:
                new_count = cur_seq - last_seq
                all_logs = list(_state.log_history)
                for line in all_logs[-min(new_count, len(all_logs)):]:
                    yield f"data: {line}\n\n"
                last_seq = cur_seq
            else:
                yield ": keepalive\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/status")
def get_status():
    """获取服务器运行状态"""
    from web.state import server_controller
    running = server_controller.is_running() if server_controller else False
    pid = server_controller.process.pid if running and server_controller.process else None
    return {"running": running, "pid": pid}

@router.post("/start")
def start_server():
    """启动服务器"""
    from web.state import server_controller, app_config
    if not server_controller:
        return {"success": False, "message": "服务未初始化"}
    if server_controller.is_running():
        return {"success": False, "message": "服务器已在运行中"}
    sc = app_config.get("server", {})
    if not sc.get("dir"):
        return {"success": False, "message": "未配置服务端目录，请先在【系统设置】中配置"}
    ok = server_controller.start_server()
    return {"success": ok, "message": "启动指令已发送" if ok else "启动失败，请检查服务端目录"}

@router.post("/stop")
def stop_server():
    """优雅停止服务器"""
    from web.state import server_controller
    if not server_controller or not server_controller.is_running():
        return {"success": False, "message": "服务器未在运行"}

    def _do():
        server_controller.stop_server()

    threading.Thread(target=_do, daemon=True).start()
    return {"success": True, "message": "关闭指令已发送，等待服务器退出（最多30秒）"}

@router.post("/force-stop")
def force_stop():
    """强制停止服务器"""
    from web.state import server_controller
    if not server_controller:
        return {"success": False, "message": "服务未初始化"}
    server_controller.force_stop()
    return {"success": True, "message": "已强制终止服务器进程"}

@router.post("/restart")
def restart_server():
    """重启服务器"""
    from web.state import server_controller
    if not server_controller:
        return {"success": False, "message": "服务未初始化"}

    def _do():
        server_controller.restart_server()

    threading.Thread(target=_do, daemon=True).start()
    return {"success": True, "message": "重启指令已发送"}

# ── 玩家管理 ──

@router.get("/players")
def get_players():
    """获取在线玩家列表"""
    from web.state import server_controller
    if not server_controller:
        raise HTTPException(503, "服务未初始化")
    if not server_controller.is_running():
        return {"players": [], "message": "服务器未运行"}
    try:
        players = server_controller.get_players()
        return {"players": players, "count": len(players)}
    except Exception as e:
        raise HTTPException(500, f"获取玩家列表失败：{e}")

class PlayerActionBody(BaseModel):
    player_id: str
    action: str  # kick | ban | admin | unadmin | unban
    reason: Optional[str] = ""
    duration: Optional[str] = "perm"

@router.post("/players/action")
def player_action(body: PlayerActionBody):
    """执行玩家管理操作"""
    from web.state import server_controller
    if not server_controller:
        raise HTTPException(503, "服务未初始化")
    if not server_controller.is_running() and body.action not in ("unban",):
        raise HTTPException(400, "服务器未在运行，无法执行玩家操作")

    ACTION_LABELS = {
        "kick": "踢出",
        "ban": "封禁",
        "admin": "设置管理员",
        "unadmin": "撤销管理员",
        "unban": "解除封禁",
    }
    if body.action not in ACTION_LABELS:
        raise HTTPException(400, f"未知操作类型: {body.action}")

    ok = server_controller.send_player_action(
        action=body.action,
        player_id=body.player_id,
        reason=body.reason or "",
        duration=body.duration or "perm",
    )
    label = ACTION_LABELS[body.action]
    if ok:
        return {"success": True, "message": f"玩家 {body.player_id} 已{label}"}
    else:
        raise HTTPException(500, f"操作失败，请确认 Telnet 已开启且密码正确（检查 serverconfig.xml 内 TelnetEnabled/TelnetPassword）")

@router.post("/install")
def install_server():
    """使用 SteamCMD 下载安装七日杀服务端"""
    from web.state import server_controller, BASE_DIR, app_config, _log_callback
    
    if server_controller and server_controller.is_running():
        return {"success": False, "message": "请先停止运行中的服务器！"}
        
    def _install_worker():
        import os, urllib.request, zipfile, subprocess, threading
        
        steamcmd_dir = os.path.join(BASE_DIR, "steamcmd")
        steamcmd_exe = os.path.join(steamcmd_dir, "steamcmd.exe")
        server_dest = os.path.join(BASE_DIR, "7DaysToDieServer")
        
        os.makedirs(steamcmd_dir, exist_ok=True)
        os.makedirs(server_dest, exist_ok=True)
        
        _log_callback(f"[*] 准备安装服务端到: {server_dest}")
        
        # 1. 下载 SteamCMD
        if not os.path.exists(steamcmd_exe):
            zip_path = os.path.join(steamcmd_dir, "steamcmd.zip")
            _log_callback("[*] 未找到 SteamCMD，正在从官方下载...")
            try:
                urllib.request.urlretrieve("https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip", zip_path)
                _log_callback("[*] 下载 SteamCMD 完成，正在解压...")
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(steamcmd_dir)
                os.remove(zip_path)
            except Exception as e:
                _log_callback(f"[!] 下载 SteamCMD 失败: {e}")
                return
                
        # 2. 执行 SteamCMD 安装七日杀服务端 (AppID 294420)
        _log_callback("[*] 开始下载/验证七日杀服务端 (AppID: 294420)... 这可能需要很长时间，请耐心等待。")
        cmd = [
            steamcmd_exe,
            "+force_install_dir", server_dest,
            "+login", "anonymous",
            "+app_update", "294420", "validate",
            "+quit"
        ]
        
        max_retries = 2
        for attempt in range(max_retries):
            try:
                # 实时捕获输出并推送到前端日志
                process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                    text=True, encoding='utf-8', errors='replace',
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                )
                
                for line in process.stdout:
                    if line:
                        _log_callback(f"[SteamCMD] {line.strip()}")
                        
                process.wait()
                
                if process.returncode == 0:
                    _log_callback("[*] 服务端下载/更新完成！")
                    
                    # 更新配置文件路径
                    config_path = os.path.join(server_dest, "serverconfig.xml")
                    
                    import yaml
                    config_file = os.path.join(BASE_DIR, "web_config.yaml")
                    config_data = {}
                    if os.path.exists(config_file):
                        with open(config_file, "r", encoding="utf-8") as f:
                            config_data = yaml.safe_load(f) or {}
                    
                    config_data.setdefault("server", {})
                    config_data["server"]["dir"] = server_dest
                    config_data["server"]["config_path"] = config_path
                    
                    with open(config_file, "w", encoding="utf-8") as f:
                        yaml.safe_dump(config_data, f, allow_unicode=True)
                    
                    # 热更新运行时路径
                    from web.state import init_state
                    init_state(config_data)
                    
                    _log_callback("[*] 配置路径已自动更新为新下载的服务端。")
                    break
                elif process.returncode == 7 and attempt < max_retries - 1:
                    _log_callback("[*] SteamCMD 需要重启以应用自身更新，正在自动重试...")
                else:
                    _log_callback(f"[!] SteamCMD 异常退出，返回码: {process.returncode}")
                    break
                    
            except Exception as e:
                _log_callback(f"[!] 执行安装过程时出错: {e}")
                break

    import threading
    threading.Thread(target=_install_worker, daemon=True).start()
    return {"success": True, "message": "安装任务已在后台启动，请查看日志！"}
