#!/bin/bash
echo "============================================"
echo "  7D2D Server Manager - Web 控制面板"
echo "============================================"

cd "$(dirname "$0")"

# 安装依赖
echo "[1/2] 安装依赖..."
pip3 install fastapi "uvicorn[standard]" pyyaml python-multipart websockets -q

# 读取端口
PORT=$(python3 -c "
import yaml, sys
try:
    c = yaml.safe_load(open('web_config.yaml'))
    print(c.get('web',{}).get('port', 8888))
except:
    print(8888)
")

echo "[2/2] 启动 Web 服务..."
echo ""
echo "  访问地址：http://0.0.0.0:$PORT"
echo "  API 文档：http://0.0.0.0:$PORT/api/docs"
echo ""

python3 -m web.app
