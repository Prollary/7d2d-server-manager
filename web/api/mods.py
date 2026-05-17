import os
import tempfile
import zipfile
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

router = APIRouter()


def _mgr():
    from web.state import mod_manager
    if not mod_manager:
        raise HTTPException(500, "服务未初始化")
    return mod_manager


@router.get("")
def list_mods():
    """获取模组列表"""
    return {"mods": _mgr().list_mods()}

@router.post("/upload")
async def upload_mod(file: UploadFile = File(...)):
    """上传并安装模组 (ZIP)"""
    mgr = _mgr()
    if not file.filename.endswith(".zip"):
        raise HTTPException(400, "仅支持 .zip 格式")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        name = mgr.install_zip(tmp_path)
    finally:
        os.unlink(tmp_path)
    return {"success": True, "name": name, "message": f"模组 '{name}' 安装成功"}

@router.put("/{raw_name}/toggle")
def toggle_mod(raw_name: str):
    """启用/禁用模组"""
    mgr = _mgr()
    enabled = mgr.toggle_mod(raw_name)
    return {"success": True, "enabled": enabled}

@router.delete("/{raw_name}")
def delete_mod(raw_name: str):
    """删除模组"""
    mgr = _mgr()
    mgr.delete_mod(raw_name)
    return {"success": True, "message": f"模组 '{raw_name}' 已删除"}
