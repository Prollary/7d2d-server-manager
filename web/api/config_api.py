import os
import yaml
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict

router = APIRouter()


def _config_file() -> str:
    """当前用户的配置文件路径"""
    from web.state import get_current_config_file
    return get_current_config_file()


def _global_config_file() -> str:
    """全局配置文件路径（仅用于 Web 监听端口/地址，影响服务启动）"""
    from web.state import BASE_DIR
    return os.path.join(BASE_DIR, "web_config.yaml")


def _cfg():
    from web.state import config_manager
    return config_manager


# ── serverconfig.xml 管理 ──

@router.get("/server")
def get_server_config():
    """获取 serverconfig.xml 的所有属性"""
    cfg = _cfg()
    if not cfg or cfg.root is None:
        raise HTTPException(400, "未加载 serverconfig.xml，请先在系统设置中配置路径")
    return {"properties": cfg.get_all_properties()}

@router.post("/server")
def save_server_config(body: Dict[str, str]):
    """保存 serverconfig.xml 属性"""
    cfg = _cfg()
    if not cfg or cfg.root is None:
        raise HTTPException(400, "未加载 serverconfig.xml")
    for key, value in body.items():
        cfg.set_value(key, value)
    if not cfg.save():
        raise HTTPException(500, "保存失败，请检查文件权限")
    return {"success": True, "message": "配置已保存"}

@router.post("/hanize")
def hanize_server_config():
    """配置文件汉化"""
    cfg = _cfg()
    if not cfg or cfg.root is None:
        raise HTTPException(400, "未加载 serverconfig.xml")
    
    i18n_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "core", "config_i18n.json")
    if not os.path.exists(i18n_path):
        raise HTTPException(500, "未找到汉化字典文件 config_i18n.json")
        
    try:
        with open(i18n_path, "r", encoding="utf-8") as f:
            mapping = json.load(f)
    except Exception as e:
        raise HTTPException(500, f"读取汉化字典失败：{e}")
        
    # 汉化前备份
    from web.state import app_config
    backup_dir = app_config.get("server", {}).get("backup_dir", "")
    if backup_dir:
        cfg.backup(backup_dir)
        
    if not cfg.hanize_config(mapping):
        raise HTTPException(500, "汉化过程失败，可能是由于文件权限或格式异常")
        
    return {"success": True, "message": "配置文件汉化成功！"}

# ── 路径 / Web 配置 ──

@router.get("/paths")
def get_paths():
    """获取系统路径配置"""
    from web.state import app_config
    sc = app_config.get("server", {})
    web = app_config.get("web", {})
    return {
        "server_dir":  sc.get("dir", ""),
        "config_path": sc.get("config_path", ""),
        "web_host":    web.get("host", "0.0.0.0"),
        "web_port":    web.get("port", 8888),
    }

class PathsBody(BaseModel):
    server_dir:  str = ""
    config_path: str = ""
    web_host:    str = "0.0.0.0"
    web_port:    int = 8888

@router.post("/paths")
def save_paths(body: PathsBody):
    """保存系统路径配置 — 写入当前用户的专属配置文件"""
    from web.state import app_config, apply_paths
    app_config.setdefault("web", {})
    app_config["web"]["host"] = body.web_host
    app_config["web"]["port"] = body.web_port
    apply_paths(body.server_dir, body.config_path)

    # 写入用户专属配置
    user_cfg = _config_file()
    os.makedirs(os.path.dirname(user_cfg), exist_ok=True)
    try:
        with open(user_cfg, "w", encoding="utf-8") as f:
            yaml.dump(app_config, f, allow_unicode=True, default_flow_style=False)
    except Exception as e:
        raise HTTPException(500, f"写入配置文件失败：{e}")

    # 同步 web host/port 到全局配置（影响下次服务启动端口）
    global_cfg = _global_config_file()
    try:
        g = {}
        if os.path.exists(global_cfg):
            with open(global_cfg, "r", encoding="utf-8") as f:
                g = yaml.safe_load(f) or {}
        g.setdefault("web", {})
        g["web"]["host"] = body.web_host
        g["web"]["port"] = body.web_port
        with open(global_cfg, "w", encoding="utf-8") as f:
            yaml.dump(g, f, allow_unicode=True, default_flow_style=False)
    except Exception:
        pass

    return {"success": True, "message": "路径配置已保存，端口变更需重启Web服务生效"}


@router.get("/auto-search")
def auto_search():
    """在 exe 所在盘符自动搜索七日杀服务端目录"""
    import sys, string
    TARGET = "7DaysToDieServer.exe"
    SKIP = {"Windows", "System32", "SysWOW64", "$Recycle.Bin", "ProgramData",
            "Recovery", "Config.Msi", "System Volume Information"}

    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    drive = os.path.splitdrive(base)[0] + os.sep if os.name == "nt" else "/"

    # 先检查常见路径
    quick_paths = [
        os.path.join(base, "7DaysToDieServer"),
        os.path.join(os.path.dirname(base), "7DaysToDieServer"),
    ]
    if os.name == "nt":
        for d in string.ascii_uppercase:
            for sub in [
                f"{d}:\\SteamLibrary\\steamapps\\common\\7 Days to Die Dedicated Server",
                f"{d}:\\Steam\\steamapps\\common\\7 Days to Die Dedicated Server",
                f"{d}:\\Program Files (x86)\\Steam\\steamapps\\common\\7 Days to Die Dedicated Server",
                f"{d}:\\7DaysToDieServer",
            ]:
                quick_paths.append(sub)

    for p in quick_paths:
        if os.path.isfile(os.path.join(p, TARGET)):
            cfg = os.path.join(p, "serverconfig.xml")
            return {"success": True, "server_dir": p,
                    "config_path": cfg if os.path.exists(cfg) else "",
                    "message": f"已找到：{p}"}

    # 递归搜索（限制深度 5）
    def _walk(root, depth):
        if depth > 5:
            return None
        try:
            with os.scandir(root) as it:
                for e in it:
                    if e.is_file() and e.name == TARGET:
                        return e.path
                    if e.is_dir() and e.name not in SKIP and not e.name.startswith("."):
                        r = _walk(e.path, depth + 1)
                        if r:
                            return r
        except PermissionError:
            pass
        return None

    found_exe = _walk(drive, 0)
    if found_exe:
        d = os.path.dirname(found_exe)
        cfg = os.path.join(d, "serverconfig.xml")
        return {"success": True, "server_dir": d,
                "config_path": cfg if os.path.exists(cfg) else "",
                "message": f"已找到：{d}"}

    return {"success": False, "message": f"在 {drive} 上未找到七日杀服务端，请手动填写路径"}

# ── 浏览服务端文件系统 ──
@router.get("/fs")
def browse_server_fs(path: str = "", type: str = "dir"):
    """浏览服务器文件/目录"""
    import os
    if not path and os.name == 'nt':
        import string
        drives = [{"name": f"{d}:\\", "path": f"{d}:\\"} for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]
        return {
            "current_path": "",
            "parent_path": None,
            "directories": drives,
            "files": []
        }
    
    if not path:
        path = "/" if os.name != 'nt' else "C:\\"

    if not os.path.exists(path) or not os.path.isdir(path):
        raise HTTPException(400, "路径不存在或不是目录")
    
    try:
        current_path = os.path.abspath(path)
        parent_path = os.path.dirname(current_path) if current_path != os.path.dirname(current_path) else None
        if os.name == 'nt' and current_path == parent_path:
            parent_path = "" 

        directories = []
        files = []
        for entry in os.scandir(current_path):
            try:
                if entry.is_dir():
                    directories.append({"name": entry.name, "path": entry.path})
                elif entry.is_file() and type == "file":
                    files.append({"name": entry.name, "path": entry.path})
            except Exception:
                pass 

        directories.sort(key=lambda x: x["name"].lower())
        files.sort(key=lambda x: x["name"].lower())

        return {
            "current_path": current_path,
            "parent_path": parent_path,
            "directories": directories,
            "files": files
        }
    except Exception as e:
        raise HTTPException(403, f"无权访问或出错: {e}")

