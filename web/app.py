import sys
import os

if getattr(sys, 'frozen', False):
    ROOT = sys._MEIPASS
else:
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.chdir(ROOT)

# ── 配置文件路径 ──
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = ROOT

CONFIG_FILE = os.path.join(BASE_DIR, "web_config.yaml")
LOG_FILE    = os.path.join(BASE_DIR, "platform.log")

# ═══════════════════════════════════════════════════════════
#  日志系统  — 写入 platform.log，同时输出到终端
# ═══════════════════════════════════════════════════════════
import logging
import traceback
from logging.handlers import RotatingFileHandler

def _setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 文件 handler：最大 5 MB，保留 3 个滚动文件
    os.makedirs(os.path.dirname(LOG_FILE) if os.path.dirname(LOG_FILE) else ".", exist_ok=True)
    fh = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    # 终端 handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)

    # 让 uvicorn / fastapi 的日志也写进文件
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        logging.getLogger(name).setLevel(logging.INFO)

    return logger

_log = logging.getLogger("platform")

# ═══════════════════════════════════════════════════════════
import json
import yaml
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import uvicorn
from web.api import server as server_api
from web.api import mods as mods_api
from web.api import worlds as worlds_api
from web.api import config_api
from web.api import tools_api
from web.api import auth as auth_api

# ── 生命周期 ──
@asynccontextmanager
async def lifespan(_app: FastAPI):
    _load_config()
    yield

# ── 认证中间件 ──
_PUBLIC = ("/api/auth/", "/static/", "/favicon")

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path == "/" or path == "/admin" or any(path.startswith(p) for p in _PUBLIC):
            return await call_next(request)
        token = (request.headers.get("X-Auth-Token") or
                 request.query_params.get("token") or "")
        from web.api.auth import check_token
        session_data = check_token(token)
        if not session_data:
            return JSONResponse({"detail": "请先登录"}, status_code=401)
        
        username = session_data["username"]
        role = session_data["role"]
        
        request.state.role = role
        import web.state as _state
        if _state._current_user != username:
            try:
                _state.activate_user(username)
            except Exception as exc:
                _log.error("activate_user(%s) failed: %s", username, exc)
        return await call_next(request)

# ── FastAPI 应用 ──
app = FastAPI(
    title="七日杀联机平台",
    description="七日杀服务器管理面板",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

app.add_middleware(AuthMiddleware)

app.include_router(auth_api.router,   prefix="/api/auth",   tags=["认证"])
app.include_router(server_api.router, prefix="/api/server", tags=["服务器控制"])
app.include_router(mods_api.router,   prefix="/api/mods",   tags=["模组管理"])
app.include_router(worlds_api.router, prefix="/api/worlds", tags=["地图管理"])
app.include_router(config_api.router, prefix="/api/config", tags=["配置管理"])
app.include_router(tools_api.router,  prefix="/api/tools",  tags=["辅助工具"])

STATIC_DIR = os.path.join(ROOT, "web", "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.get("/admin")
def admin_index():
    return FileResponse(os.path.join(STATIC_DIR, "admin.html"))

# ── 配置加载 ──
def _load_config():
    from web.state import init_state
    
    nat_config_path = os.path.join(BASE_DIR, "nat_config.json")
    if not os.path.exists(nat_config_path):
        default_nat = {
            "GamePublicIP": "",
            "ServerPort": 26900,
            "HardwareSpec": "标准型服务器"
        }
        with open(nat_config_path, "w", encoding="utf-8") as f:
            json.dump(default_nat, f, indent=4)
            
    init_state({})

# ═══════════════════════════════════════════════════════════
#  程序入口
# ═══════════════════════════════════════════════════════════
def main():
    import multiprocessing
    multiprocessing.freeze_support()

    # 日志系统是第一件事，确保任何崩溃都能被记录
    _setup_logging()
    _log.info("=" * 60)
    _log.info("七日杀联机平台 v2.0 启动")
    _log.info("日志文件: %s", LOG_FILE)
    _log.info("程序目录: %s", BASE_DIR)
    _log.info("Python: %s  |  平台: %s", sys.version.split()[0], sys.platform)
    _log.info("PyInstaller 打包: %s", bool(getattr(sys, 'frozen', False)))

    try:
        # 读取 web 配置
        config = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
            _log.info("配置文件已加载: %s", CONFIG_FILE)
        else:
            _log.warning("未找到配置文件 %s，使用默认值", CONFIG_FILE)

        web  = config.get("web", {})
        host = web.get("host", "0.0.0.0")
        port = int(web.get("port", 8888))

        _log.info("监听地址: %s:%d", host, port)
        _log.info("访问地址: http://127.0.0.1:%d", port)
        _log.info("=" * 60)

        # 延迟 1.5 秒后自动打开浏览器（等服务器就绪）
        import threading, webbrowser
        def _open_browser():
            import time; time.sleep(1.5)
            webbrowser.open(f"http://127.0.0.1:{port}")
        threading.Thread(target=_open_browser, daemon=True).start()

        # 配置 uvicorn 日志级别（写入同一个 platform.log）
        uv_log_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "fmt": "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                }
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                }
            },
            "loggers": {
                "uvicorn": {"handlers": ["default"], "level": "INFO"},
                "uvicorn.error": {"level": "INFO"},
                "uvicorn.access": {"handlers": ["default"], "level": "INFO", "propagate": False},
            },
        }

        if getattr(sys, 'frozen', False):
            uvicorn.run(app, host=host, port=port, log_config=uv_log_config)
        else:
            uvicorn.run("web.app:app", host=host, port=port, reload=False, log_config=uv_log_config)

    except SystemExit:
        _log.info("程序正常退出")
    except Exception:
        _log.critical("启动失败，详细错误如下：\n%s", traceback.format_exc())
        # 闪退保护：保持终端窗口打开，让用户读到错误
        if getattr(sys, 'frozen', False):
            print("\n" + "=" * 60)
            print("[错误] 程序启动失败！")
            print(f"请查看日志文件了解详情：{LOG_FILE}")
            print("=" * 60)
            input("\n按 Enter 键关闭窗口...")
        raise

if __name__ == "__main__":
    main()
