import io
import os
import tempfile
import zipfile
import shutil
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter()


def _mgr():
    from web.state import world_manager
    if not world_manager:
        raise HTTPException(500, "服务未初始化")
    return world_manager


def _cfg():
    from web.state import config_manager
    return config_manager


@router.get("")
def list_worlds():
    """获取地图列表及当前使用的地图"""
    mgr = _mgr()
    worlds = mgr.list_worlds()
    current = _cfg().get_value("GameWorld") if _cfg() and _cfg().root else ""
    return {"worlds": worlds, "current": current}

@router.post("/upload")
async def upload_world(file: UploadFile = File(...)):
    """上传并安装地图 (ZIP)"""
    mgr = _mgr()
    if not file.filename.endswith(".zip"):
        raise HTTPException(400, "请上传 .zip 格式的地图压缩包")
    with tempfile.TemporaryDirectory() as tmp_dir:
        zip_path = os.path.join(tmp_dir, "world.zip")
        with open(zip_path, "wb") as f:
            f.write(await file.read())
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp_dir)
        os.remove(zip_path)
        # 找到解压后的顶级文件夹
        entries = [e for e in os.listdir(tmp_dir) if os.path.isdir(os.path.join(tmp_dir, e))]
        if not entries:
            raise HTTPException(400, "zip 中未找到地图文件夹")
        world_folder = os.path.join(tmp_dir, entries[0])
        name = mgr.install_world(world_folder)
    return {"success": True, "name": name, "message": f"地图 '{name}' 上传成功"}

class SwitchBody(BaseModel):
    world_name: str

@router.put("/switch")
def switch_world(body: SwitchBody):
    """切换当前使用的地图"""
    cfg = _cfg()
    if not cfg or cfg.root is None:
        raise HTTPException(400, "未加载 serverconfig.xml")
    cfg.set_value("GameWorld", body.world_name)
    if not cfg.save():
        raise HTTPException(500, "保存配置文件失败")
    return {"success": True, "message": f"地图已切换为 '{body.world_name}'，重启生效"}

@router.delete("/{name}")
def delete_world(name: str):
    """删除地图"""
    _mgr().delete_world(name)
    return {"success": True, "message": f"地图 '{name}' 已删除"}


@router.get("/backup")
def backup_world():
    """备份当前存档（Saves 目录）并提供下载"""
    from web.state import app_config
    sc = app_config.get("server", {})
    server_dir = sc.get("dir", "")
    if not server_dir:
        raise HTTPException(400, "未配置服务端目录")

    saves_dir = os.path.join(server_dir, "Saves")
    if not os.path.isdir(saves_dir):
        raise HTTPException(400, f"存档目录不存在：{saves_dir}")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(saves_dir):
            dirs[:] = [d for d in dirs if d != "_snapshots"]
            for f in files:
                fp = os.path.join(root, f)
                zf.write(fp, os.path.relpath(fp, saves_dir))
    buf.seek(0)

    filename = f"7d2d_saves_{ts}.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
