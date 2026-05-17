import os
import queue as sync_queue
from collections import deque
from typing import Optional

# ── 日志广播 ──
log_queue: sync_queue.Queue = sync_queue.Queue(maxsize=2000)
log_history: deque = deque(maxlen=500)
log_sequence: int = 0
ws_clients: set = set()

# ── 路径定义 ──
import sys
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── 当前登录用户 ──
_current_user: str = ""


def get_current_config_file() -> str:
    """返回当前用户的配置文件路径（userdata/<user>/web_config.yaml）"""
    if _current_user:
        from web.api.auth import BASE_DIR as AUTH_BASE, USERDATA_DIR
        return os.path.join(USERDATA_DIR, _current_user, "web_config.yaml")
    return os.path.join(BASE_DIR, "web_config.yaml")


def activate_user(username: str):
    """切换到指定用户：加载其专属配置并重新初始化状态"""
    global _current_user
    _current_user = username
    import yaml
    cfg_file = get_current_config_file()
    config: dict = {}
    if os.path.exists(cfg_file):
        with open(cfg_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
    init_state(config)

# ── 全局单例 ──
from core.server import ServerController
from core.config import ConfigManager
from core.mod import ModManager, WorldManager
from core.snapshot import SnapshotManager

server_controller:   Optional[ServerController]   = None
config_manager:      Optional[ConfigManager]       = None
mod_manager:         Optional[ModManager]          = None
world_manager:       Optional[WorldManager]        = None
snapshot_manager:    Optional[SnapshotManager]     = None
app_config: dict = {}

def _log_callback(text: str):
    """日志回调函数，将日志放入队列和历史记录"""
    global log_sequence
    log_history.append(text)
    log_sequence += 1
    try:
        log_queue.put_nowait(text)
    except sync_queue.Full:
        try:
            log_queue.get_nowait()
            log_queue.put_nowait(text)
        except Exception:
            pass

def init_state(config: dict):
    """初始化全局状态"""
    global server_controller, config_manager, mod_manager, world_manager, snapshot_manager, app_config
    app_config = config

    sc = config.get("server", {})
    server_dir = sc.get("dir", "")
    config_path = sc.get("config_path", "")

    config_manager = ConfigManager(config_path)
    if config_path and os.path.exists(config_path):
        config_manager.load()

    server_controller = ServerController(
        server_dir=server_dir,
        config_path=config_path,
        output_callback=_log_callback,
    )

    rcon = config.get("rcon", {})
    server_controller.set_rcon(rcon.get("password", ""), int(rcon.get("port", 8081)))

    mods_dir = os.path.join(server_dir, "Mods") if server_dir else ""
    worlds_dir = os.path.join(server_dir, "Data", "Worlds") if server_dir else ""
    mod_manager = ModManager(mods_dir)
    world_manager = WorldManager(worlds_dir)

    # 启动独立日志监控
    if server_dir:
        server_controller.start_log_watcher()

    # 启动滚动快照管理
    if snapshot_manager:
        snapshot_manager.stop()
    if server_dir:
        saves_dir = os.path.join(server_dir, "Saves")
        os.makedirs(saves_dir, exist_ok=True)
        snapshot_manager = SnapshotManager(saves_dir)
        snapshot_manager.start()

def apply_paths(server_dir: str, config_path: str):
    """热更新路径配置，无需重启服务"""
    global app_config
    app_config.setdefault("server", {})
    app_config["server"].update(dir=server_dir, config_path=config_path)
    if server_controller:
        server_controller.server_dir = server_dir
        server_controller.config_path = config_path
        # 同步 Rcon 密码
        if config_manager and config_manager.root is not None:
            pw  = config_manager.get_value("TelnetPassword")
            pt  = config_manager.get_value("TelnetPort")
            if pw:
                server_controller.set_rcon(pw, int(pt) if pt.isdigit() else 8081)
    if config_manager:
        config_manager.config_path = config_path
        if config_path and os.path.exists(config_path):
            config_manager.load()
    if mod_manager:
        mod_manager.mods_dir = os.path.join(server_dir, "Mods") if server_dir else ""
    if world_manager:
        world_manager.worlds_dir = os.path.join(server_dir, "Data", "Worlds") if server_dir else ""
