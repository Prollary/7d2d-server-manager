import socket
import subprocess
import os


PORTS = [26900, 26901, 26902]


def check_port_in_use(port: int) -> bool:
    """检查本地端口是否已被占用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", port)) == 0

def check_ports() -> dict:
    """检查常用端口状态"""
    results = {}
    for p in PORTS:
        results[p] = check_port_in_use(p)
    return results

def open_firewall_port(port: int) -> bool:
    """在 Windows 防火墙中开放指定端口"""
    if os.name != "nt":
        return False
    try:
        for proto in ("TCP", "UDP"):
            subprocess.run(
                ["netsh", "advfirewall", "firewall", "add", "rule",
                 f"name=7D2D_{port}_{proto}", "dir=in", "action=allow",
                 f"protocol={proto}", f"localport={port}"],
                check=True, capture_output=True
            )
        return True
    except subprocess.CalledProcessError:
        return False
