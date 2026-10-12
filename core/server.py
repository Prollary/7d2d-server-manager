import subprocess
import threading
import telnetlib
import time
import os
import signal
from typing import Callable, Optional


class ServerController:
    def __init__(self, server_dir: str, config_path: str,
                 output_callback: Optional[Callable[[str], None]] = None):
        self.server_dir = server_dir
        self.config_path = config_path
        self.output_callback = output_callback
        self.process: Optional[subprocess.Popen] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._log_watcher_thread: Optional[threading.Thread] = None
        self._log_watcher_running = False
        self._rcon_host = "127.0.0.1"
        self._rcon_port = 8081
        self._rcon_password = ""

    # ── 进程运行状态 ──

    def is_running(self) -> bool:
        """检查服务器进程是否正在运行"""
        if self.process is not None and self.process.poll() is None:
            return True
        return self._is_external_running()

    def _is_external_running(self) -> bool:
        """检查是否有外部启动的 7DaysToDieServer 进程"""
        if os.name == "nt":
            try:
                result = subprocess.run(
                    ["tasklist", "/FI", "IMAGENAME eq 7DaysToDieServer.exe", "/NH"],
                    capture_output=True, text=True, timeout=5
                )
                return "7DaysToDieServer.exe" in result.stdout
            except Exception:
                return False
        return False

    def get_exe_path(self) -> str:
        """获取服务端可执行文件路径"""
        for name in ("7DaysToDieServer.exe", "startdedicated.bat"):
            path = os.path.join(self.server_dir, name)
            if os.path.exists(path):
                return path
        return ""

    # ── 启动 / 停止 ──

    def start_server(self) -> bool:
        """启动服务器"""
        if self.is_running():
            return False
        exe = self.get_exe_path()
        if not exe:
            self._emit("错误：未找到服务端可执行文件。")
            return False

        # --- 注入 NAT 外网配置 ---
        try:
            import json, sys
            import xml.etree.ElementTree as ET
            
            # 定位 nat_config.json
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            nat_file = os.path.join(base_dir, "nat_config.json")
            if os.path.exists(nat_file) and os.path.exists(self.config_path):
                with open(nat_file, "r", encoding="utf-8") as f:
                    nat_cfg = json.load(f)
                
                pub_ip = nat_cfg.get("GamePublicIP", "").strip()
                server_port = nat_cfg.get("ServerPort")
                
                # 更新 XML
                tree = ET.parse(self.config_path)
                root = tree.getroot()
                changed = False
                
                for prop in root.findall("property"):
                    name = prop.get("name")
                    if name == "ServerIP" and pub_ip:
                        prop.set("value", pub_ip)
                        changed = True
                    elif name == "ServerPort" and server_port:
                        prop.set("value", str(server_port))
                        changed = True
                        
                if changed:
                    tree.write(self.config_path, encoding="utf-8", xml_declaration=True)
                    self._emit(f"[*] 已应用 NAT 外部配置：IP={pub_ip or '默认'}, 端口={server_port or '默认'}")
        except Exception as e:
            self._emit(f"[!] 应用 NAT 外部配置失败：{e}")
        # -----------------------------

        self._log_file = os.path.join(self.server_dir, "output_log.txt")
        cmd = [exe, f"-configfile={self.config_path}",
               "-logfile", "output_log.txt",
               "-quit", "-batchmode", "-nographics", "-dedicated"]
        try:
            self.process = subprocess.Popen(
                cmd,
                cwd=self.server_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        except Exception as e:
            self._emit(f"启动失败：{e}")
            return False

        self._monitor_thread = threading.Thread(target=self._tail_log_file, daemon=True)
        self._monitor_thread.start()
        return True

    def stop_server(self) -> bool:
        """尝试优雅关闭服务器。成功返回 True；Rcon 超时返回 False。"""
        if not self.is_running():
            return False
        rcon_ok = self._send_rcon("shutdown")
        if rcon_ok:
            self._emit("已发送 shutdown 指令，等待服务器退出（最多30秒）...")
            for _ in range(30):
                if not self.is_running():
                    return True
                time.sleep(1)
            self._emit("服务器未在30秒内正常退出。")
            return False

        # 无 Rcon 时直接强制终止
        self._emit("Rcon 不可用，正在通过系统指令终止进程...")
        self.force_stop()
        return True

    def force_stop(self):
        """立即强制结束服务器进程"""
        # 先尝试停面板启动的进程
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
        # 再尝试强制杀死外部启动的进程
        if os.name == "nt":
            try:
                subprocess.run(
                    ["taskkill", "/F", "/IM", "7DaysToDieServer.exe"],
                    capture_output=True, timeout=10
                )
            except Exception:
                pass

    def restart_server(self):
        """重启服务器"""
        result = self.stop_server()
        if not result and self.is_running():
            self.force_stop()
        time.sleep(2)
        self.start_server()

    # ── RCON 连接设置 ──

    def set_rcon(self, password: str, port: int = 8081):
        self._rcon_password = password
        self._rcon_port = port

    def _auto_load_rcon(self):
        """从已加载的 serverconfig.xml 中自动读取 Telnet 端口和密码"""
        try:
            from web.state import config_manager
            if config_manager and config_manager.root is not None:
                passwd = config_manager.get_value("TelnetPassword")
                port_str = config_manager.get_value("TelnetPort")
                enabled = config_manager.get_value("TelnetEnabled")
                if enabled.lower() == "true" and passwd:
                    self._rcon_password = passwd
                    self._rcon_port = int(port_str) if port_str.isdigit() else 8081
        except Exception:
            pass

    def _send_rcon(self, command: str) -> bool:
        """发送单条 RCON 命令"""
        self._auto_load_rcon()
        if not self._rcon_password:
            return False
        try:
            tn = telnetlib.Telnet(self._rcon_host, self._rcon_port, timeout=5)
            tn.read_until(b"password:", timeout=5)
            tn.write(self._rcon_password.encode("utf-8") + b"\n")
            time.sleep(0.5)
            tn.write(command.encode("utf-8") + b"\n")
            time.sleep(0.5)
            tn.close()
            return True
        except Exception:
            return False

    def execute_rcon(self, command: str, wait: float = 1.5) -> str:
        """发送 RCON 命令并返回响应文本内容"""
        self._auto_load_rcon()
        if not self._rcon_password:
            return ""
        try:
            tn = telnetlib.Telnet(self._rcon_host, self._rcon_port, timeout=5)
            tn.read_until(b"password:", timeout=5)
            tn.write(self._rcon_password.encode("utf-8") + b"\n")
            time.sleep(0.5)
            tn.write(command.encode("utf-8") + b"\n")
            time.sleep(wait)
            response = tn.read_very_eager()
            tn.close()
            return response.decode("utf-8", errors="replace")
        except Exception as e:
            return ""

    def get_players(self) -> list:
        """通过 Telnet 获取在线玩家列表"""
        import re
        raw = self.execute_rcon("lp")
        if not raw:
            return []
        players = []
        for line in raw.splitlines():
            line = line.strip()
            m = re.search(r'\d+\.\s+id=(\d+),\s*Name=([^,]+),.*?(?:steamid|pltfmid)=(?:Steam_)?(\d+|EOS_\w+).*?ip=([\d.]+),\s*ping=(\d+)', line)
            if m:
                players.append({
                    "id": m.group(1),
                    "name": m.group(2).strip(),
                    "steam_id": m.group(3),
                    "ip": m.group(4),
                    "ping": int(m.group(5)),
                })
            else:
                m2 = re.search(r'id=(\d+),\s*Name=([^,]+)', line)
                if m2:
                    players.append({
                        "id": m2.group(1),
                        "name": m2.group(2).strip(),
                        "steam_id": "",
                        "ip": "",
                        "ping": 0,
                    })
        return players

    def send_player_action(self, action: str, player_id: str, reason: str = "", duration: str = "perm") -> bool:
        """对玩家执行操作（踢出、封禁、管理等）"""
        if action == "kick":
            reason_part = f" {reason}" if reason else ""
            cmd = f"kick {player_id}{reason_part}"
        elif action == "ban":
            reason_part = reason if reason else "Banned by admin"
            cmd = f"ban add {player_id} {duration} \"{reason_part}\""
        elif action == "admin":
            cmd = f"admin add {player_id} 0"
        elif action == "unadmin":
            cmd = f"admin remove {player_id}"
        elif action == "unban":
            cmd = f"ban remove {player_id}"
        else:
            return False
        return self._send_rcon(cmd)

    # ── 日志文件跟踪 ──

    def _tail_log_file(self):
        """面板启动服务器后，追踪读取日志文件"""
        log_file = self._log_file

        old_mtime = os.path.getmtime(log_file) if os.path.exists(log_file) else 0
        old_size = os.path.getsize(log_file) if os.path.exists(log_file) else 0

        self._emit("── 等待服务器创建日志文件 ──")

        file_ready = False
        for _ in range(40):
            if not self.is_running():
                self._emit("── 服务器进程已结束 ──")
                return
            if os.path.exists(log_file):
                cur_mtime = os.path.getmtime(log_file)
                cur_size = os.path.getsize(log_file)
                if cur_mtime != old_mtime or cur_size != old_size:
                    file_ready = True
                    break
            time.sleep(0.5)

        if not file_ready:
            if os.path.exists(log_file):
                self._emit("── 日志文件已存在，从尾部开始追踪 ──")
            else:
                self._emit("⚠ 日志文件未出现，请检查服务端路径配置")
                return

        self._emit(f"── 日志开始输出（{log_file}）──")
        try:
            with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                if not file_ready:
                    f.seek(0, 2)

                while self.is_running():
                    line = f.readline()
                    if line:
                        self._emit(line.rstrip())
                    else:
                        time.sleep(0.1)
                for line in f:
                    if line.strip():
                        self._emit(line.rstrip())
        except Exception as e:
            self._emit(f"日志读取异常：{e}")
        self._emit("── 服务器进程已结束 ──")

    # ── 独立日志监控（支持外部启动的服务器）──

    def start_log_watcher(self):
        """启动独立的日志文件监控线程，即使服务器是外部启动的也能读取日志"""
        if self._log_watcher_running:
            return
        log_file = os.path.join(self.server_dir, "output_log.txt") if self.server_dir else ""
        if not log_file:
            return
        self._log_watcher_running = True
        self._log_watcher_thread = threading.Thread(
            target=self._independent_log_watcher, args=(log_file,), daemon=True
        )
        self._log_watcher_thread.start()

    def _independent_log_watcher(self, log_file: str):
        """独立日志监控：持续追踪 output_log.txt，不依赖 self.process"""
        self._emit("── 日志监控已启动 ──")
        last_size = 0
        last_inode = None

        while self._log_watcher_running:
            try:
                if not os.path.exists(log_file):
                    time.sleep(1)
                    continue

                # 检查文件是否被重新创建（inode 变了或文件变小了）
                cur_size = os.path.getsize(log_file)
                try:
                    cur_stat = os.stat(log_file)
                    cur_inode = (cur_stat.st_dev, cur_stat.st_ino, cur_stat.st_ctime_ns)
                except Exception:
                    cur_inode = None

                if cur_size < last_size or (cur_inode and last_inode and cur_inode != last_inode):
                    # 文件被重新创建了，从头开始读
                    last_size = 0

                if cur_size > last_size:
                    try:
                        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                            f.seek(last_size)
                            while True:
                                line = f.readline()
                                if not line:
                                    break
                                stripped = line.rstrip()
                                if stripped:
                                    self._emit(stripped)
                            last_size = f.tell()
                    except Exception as e:
                        self._emit(f"日志读取异常：{e}")

                last_inode = cur_inode
                time.sleep(0.3)

            except Exception:
                time.sleep(1)

    def stop_log_watcher(self):
        """停止独立日志监控"""
        self._log_watcher_running = False

    def _emit(self, text: str):
        if self.output_callback:
            self.output_callback(text)
