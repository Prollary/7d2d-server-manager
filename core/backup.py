import os
import shutil
import zipfile
from datetime import datetime


def backup_saves(saves_dir: str, backup_dir: str) -> str:
    """立即备份游戏存档为 ZIP 文件"""
    os.makedirs(backup_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"saves_backup_{ts}.zip"
    zip_path = os.path.join(backup_dir, zip_name)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(saves_dir):
            for file in files:
                full = os.path.join(root, file)
                arcname = os.path.relpath(full, os.path.dirname(saves_dir))
                zf.write(full, arcname)
    return zip_path
