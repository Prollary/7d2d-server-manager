"""用户认证：注册 / 登录 / Token 校验

设计原则：
- users.json / userdata/ 与 exe 放在同一目录（BASE_DIR）
- Session 仅保留在内存中，exe 重启即清空，必须重新登录
- 前端不持久化 token，刷新页面即需要重新登录
"""
import os
import sys
import json
import shutil
import hashlib
import secrets
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# ── 基础路径：exe 所在目录（与 exe 同级） ──
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

USERS_FILE   = os.path.join(BASE_DIR, "users.json")
USERDATA_DIR = os.path.join(BASE_DIR, "userdata")   # userdata/<username>/

# ── Session 仅保留在内存中 ──
# exe 每次重启 _sessions 重置为空字典，所有已登录状态失效
_sessions: dict = {}   # {token: {"username": str, "expires": float}}

TOKEN_EXPIRY = 8 * 3600   # 单次登录有效期 8 小时（页面保持打开时）


# ── 用户数据路径工具 ──

def get_user_data_dir(username: str) -> str:
    return os.path.join(USERDATA_DIR, username)


def get_user_config_file(username: str) -> str:
    return os.path.join(get_user_data_dir(username), "web_config.yaml")


# ── 用户账号文件读写 ──

def _load_users() -> list:
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_users(users: list):
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def _hash_pw(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000
    ).hex()


def _create_session(username: str, role: str = "user") -> str:
    """创建内存 session，不写入任何文件"""
    token = secrets.token_urlsafe(32)
    _sessions[token] = {"username": username, "role": role, "expires": time.time() + TOKEN_EXPIRY}
    return token


def check_token(token: str) -> dict | None:
    """验证 token，有效返回字典包含 username 和 role，否则返回 None"""
    if not token:
        return None
    s = _sessions.get(token)
    if s and s.get("expires", 0) > time.time():
        return {"username": s["username"], "role": s.get("role", "user")}
    # token 不存在或已过期，从内存中清除
    _sessions.pop(token, None)
    return None


# ── 接口 ──

class RegisterBody(BaseModel):
    username: str
    password: str


class LoginBody(BaseModel):
    username: str
    password: str


@router.post("/register")
def register(body: RegisterBody):
    name = body.username.strip()
    if not name or len(name) < 2:
        raise HTTPException(400, "用户名至少 2 个字符")
    if len(body.password) < 6:
        raise HTTPException(400, "密码至少 6 位")
    if name.lower() == "admin":
        raise HTTPException(400, "不能注册管理员保留账号")

    users = _load_users()
    if any(u["username"] == name for u in users):
        raise HTTPException(400, "该用户名已被注册")

    # 注册时清除同名旧用户数据目录（含配置文件）
    old_dir = get_user_data_dir(name)
    if os.path.exists(old_dir):
        shutil.rmtree(old_dir, ignore_errors=True)
    os.makedirs(old_dir, exist_ok=True)

    salt    = secrets.token_hex(16)
    pw_hash = _hash_pw(body.password, salt)
    users.append({"username": name, "salt": salt, "password_hash": pw_hash})
    _save_users(users)

    token = _create_session(name)
    return {"success": True, "token": token, "username": name, "role": "user"}


@router.post("/login")
def login(body: LoginBody):
    # 管理员写死逻辑
    if body.username == "admin" and body.password == "admin123":
        os.makedirs(get_user_data_dir(body.username), exist_ok=True)
        token = _create_session("admin", role="admin")
        return {"success": True, "token": token, "username": "admin", "role": "admin"}
        
    users = _load_users()
    user  = next((u for u in users if u["username"] == body.username), None)
    if not user or _hash_pw(body.password, user["salt"]) != user["password_hash"]:
        raise HTTPException(401, "用户名或密码错误")
    # 确保用户数据目录存在（可能是老用户首次用新版）
    os.makedirs(get_user_data_dir(body.username), exist_ok=True)
    token = _create_session(body.username, role="user")
    return {"success": True, "token": token, "username": body.username, "role": "user"}


@router.get("/check")
def check(token: str = ""):
    session_data = check_token(token)
    if session_data:
        return {"valid": True, "username": session_data["username"], "role": session_data["role"]}
    return {"valid": False}


@router.post("/logout")
def logout(token: str = ""):
    _sessions.pop(token, None)
    return {"success": True}


@router.get("/info")
def info():
    """返回数据文件位置，方便忘记密码时找到 users.json 删除重置"""
    users = _load_users()
    return {
        "users_file": USERS_FILE,
        "data_dir":   BASE_DIR,
        "user_count": len(users),
        "tip": (
            "忘记密码？删除同目录下的 users.json 后重启程序，"
            "再重新注册即可（原有配置将同时清除）。"
        ),
    }
