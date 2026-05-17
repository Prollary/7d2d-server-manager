import xml.etree.ElementTree as ET
import os
import shutil
from datetime import datetime


class ConfigManager:
    """XML 配置文件管理器，用于读取、修改并保存服务端的 serverconfig.xml 设置"""
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.tree = None
        self.root = None

    def load(self) -> bool:
        """从磁盘加载 XML 树"""
        if not os.path.exists(self.config_path):
            return False
        try:
            self.tree = ET.parse(self.config_path)
            self.root = self.tree.getroot()
            return True
        except ET.ParseError:
            return False

    def get_value(self, name: str) -> str:
        """查找指定的 property 并返回其 value 值"""
        if self.root is None:
            return ""
        for prop in self.root.findall("property"):
            if prop.get("name") == name:
                return prop.get("value", "")
        return ""

    def set_value(self, name: str, value: str):
        """设置指定的 property 的 value 值"""
        if self.root is None:
            return
        for prop in self.root.findall("property"):
            if prop.get("name") == name:
                prop.set("value", value)
                return
        # 如果未找到该属性，则创建新属性
        new_prop = ET.SubElement(self.root, "property")
        new_prop.set("name", name)
        new_prop.set("value", value)

    def save(self) -> bool:
        """保存 XML 树到磁盘"""
        if self.tree is None:
            return False
        try:
            ET.indent(self.tree, space="    ")
        except AttributeError:
            pass  # 兼容低版本 Python
        try:
            self.tree.write(self.config_path, encoding="utf-8", xml_declaration=True)
            return True
        except Exception:
            return False

    def get_all_properties(self) -> dict:
        """获取配置文件中的所有属性"""
        if self.root is None:
            return {}
        return {
            p.get("name"): p.get("value", "")
            for p in self.root.findall("property")
            if p.get("name")
        }

    def backup(self, backup_dir: str) -> str:
        """备份当前配置文件"""
        os.makedirs(backup_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = os.path.join(backup_dir, f"serverconfig_{ts}.xml")
        shutil.copy2(self.config_path, dest)
        return dest

    def hanize_config(self, i18n_mapping: dict) -> bool:
        """对配置文件进行中文注释汉化"""
        if not os.path.exists(self.config_path):
            return False
            
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                
            new_lines = []
            import re
            
            for i, line in enumerate(lines):
                match = re.search(r'<property\s+name="([^"]+)"', line)
                if match:
                    prop_name = match.group(1)
                    if prop_name in i18n_mapping:
                        i18n_info = i18n_mapping[prop_name]
                        desc = i18n_info.get("desc", "")
                        label = i18n_info.get("label", "")
                        if desc or label:
                            # 避免重复插入
                            already_has = False
                            for j in range(max(0, len(new_lines)-3), len(new_lines)):
                                if "<!-- [汉化]" in new_lines[j] and (label in new_lines[j] or desc in new_lines[j]):
                                    already_has = True
                                    break
                            
                            if not already_has:
                                indent_match = re.match(r'^(\s*)', line)
                                indent = indent_match.group(1) if indent_match else ""
                                new_lines.append(f"{indent}<!-- [汉化] {label}: {desc} -->\n")
                new_lines.append(line)
                
            with open(self.config_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
                
            # 重新加载以确保 XML 仍然有效
            self.load()
            return True
        except Exception as e:
            print(f"Error hanizing config: {e}")
            return False
