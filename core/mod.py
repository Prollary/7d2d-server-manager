import os
import shutil
import zipfile
from typing import List


class ModManager:
    """模组管理器，处理 Mod 的识别、解包、启用及禁用"""
    def __init__(self, mods_dir: str):
        self.mods_dir = mods_dir

    def ensure_dir(self):
        """确保模组目录存在"""
        if self.mods_dir:
            os.makedirs(self.mods_dir, exist_ok=True)

    def list_mods(self) -> List[dict]:
        """列出所有模组及其状态"""
        if not self.mods_dir:
            return []
        self.ensure_dir()
        mods = []
        for name in sorted(os.listdir(self.mods_dir)):
            path = os.path.join(self.mods_dir, name)
            if os.path.isdir(path):
                disabled = name.endswith(".disabled")
                display = name[:-len(".disabled")] if disabled else name
                mods.append({"name": display, "raw": name, "path": path, "enabled": not disabled})
        return mods

    def install_zip(self, zip_path: str) -> str:
        """从 ZIP 文件安装模组"""
        self.ensure_dir()
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            top = names[0].split("/")[0] if names else os.path.splitext(os.path.basename(zip_path))[0]
            dest = os.path.join(self.mods_dir, top)
            zf.extractall(self.mods_dir)
        return top

    def install_folder(self, folder_path: str) -> str:
        """从文件夹安装模组"""
        self.ensure_dir()
        name = os.path.basename(folder_path.rstrip("/\\"))
        dest = os.path.join(self.mods_dir, name)
        if os.path.exists(dest):
            shutil.rmtree(dest)
        shutil.copytree(folder_path, dest)
        return name

    def toggle_mod(self, raw_name: str) -> bool:
        """切换模组启用/禁用状态"""
        path = os.path.join(self.mods_dir, raw_name)
        if raw_name.endswith(".disabled"):
            new_name = raw_name[:-len(".disabled")]
        else:
            new_name = raw_name + ".disabled"
        new_path = os.path.join(self.mods_dir, new_name)
        os.rename(path, new_path)
        return not raw_name.endswith(".disabled")

    def delete_mod(self, raw_name: str):
        """删除模组"""
        path = os.path.join(self.mods_dir, raw_name)
        if os.path.isdir(path):
            shutil.rmtree(path)


class WorldManager:
    """世界地图管理器，处理自定义地图的识别和导入"""
    def __init__(self, worlds_dir: str):
        self.worlds_dir = worlds_dir

    def ensure_dir(self):
        """确保地图目录存在"""
        if self.worlds_dir:
            os.makedirs(self.worlds_dir, exist_ok=True)

    def list_worlds(self) -> List[str]:
        """列出所有可用地图"""
        if not self.worlds_dir:
            return []
        self.ensure_dir()
        return [
            d for d in sorted(os.listdir(self.worlds_dir))
            if os.path.isdir(os.path.join(self.worlds_dir, d))
        ]

    def install_world(self, folder_path: str) -> str:
        """从文件夹安装地图"""
        self.ensure_dir()
        name = os.path.basename(folder_path.rstrip("/\\"))
        dest = os.path.join(self.worlds_dir, name)
        if os.path.exists(dest):
            shutil.rmtree(dest)
        shutil.copytree(folder_path, dest)
        return name

    def delete_world(self, name: str):
        """删除地图"""
        path = os.path.join(self.worlds_dir, name)
        if os.path.isdir(path):
            shutil.rmtree(path)
