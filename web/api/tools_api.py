from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


@router.get("/network")
def check_network():
    """检查服务器常用端口是否被占用"""
    from core.network import check_ports
    results = check_ports()
    return {"ports": {str(k): v for k, v in results.items()}}

@router.post("/firewall")
def open_firewall():
    """尝试自动在 Windows 防火墙中开放端口"""
    from core.network import open_firewall_port, PORTS
    results = {}
    for port in PORTS:
        results[str(port)] = open_firewall_port(port)
    return {"results": results}

class BackupBody(BaseModel):
    saves_dir: str = ""
    backup_dir: str = ""

@router.post("/backup")
def backup_saves(body: BackupBody):
    """立即备份游戏存档"""
    import os
    from core.backup import backup_saves as do_backup
    from web.state import app_config

    sc = app_config.get("server", {})
    saves_dir = body.saves_dir or sc.get("saves_dir", "")
    backup_dir = body.backup_dir or sc.get("backup_dir", "")

    if not saves_dir:
        raise HTTPException(400, "未指定存档目录（saves_dir）")
    if not backup_dir:
        raise HTTPException(400, "未指定备份目录（backup_dir）")
    if not os.path.isdir(saves_dir):
        raise HTTPException(400, f"存档目录不存在：{saves_dir}")

    path = do_backup(saves_dir, backup_dir)
    return {"success": True, "path": path, "message": f"备份成功：{path}"}
