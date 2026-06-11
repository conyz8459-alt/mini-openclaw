#!/usr/bin/env bash
# ============================================================
#  Mini-OpenClaw 一键启动（macOS / Linux）
#  自动：建虚拟环境 -> 装后端依赖 -> 检查 .env -> 装前端依赖
#       -> 同时拉起后端(8002) 与 前端(3000)
# ============================================================
set -e

cd "$(dirname "$0")"
echo "[Mini-OpenClaw] 启动中..."
echo

# 选择 python 命令
if command -v python3 >/dev/null 2>&1; then
    PY=python3
else
    PY=python
fi

# ---------- 1. 后端：虚拟环境 ----------
if [ ! -d "backend/.venv" ]; then
    echo "[1/5] 创建 Python 虚拟环境..."
    "$PY" -m venv backend/.venv
else
    echo "[1/5] 已存在虚拟环境，跳过创建。"
fi

# ---------- 2. 后端：安装依赖 ----------
echo "[2/5] 安装后端依赖（使用国内镜像源加速，首次较慢，请耐心等待）..."
# shellcheck disable=SC1091
source backend/.venv/bin/activate
python -m pip install -q --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
python -m pip install -q -r backend/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# ---------- 3. 检查 .env ----------
if [ ! -f "backend/.env" ]; then
    echo "[3/5] 未找到 backend/.env，正在从模板复制..."
    cp backend/.env.example backend/.env
    echo
    echo "============================================================"
    echo " 请先编辑 backend/.env，填入你的模型 API Key（LLM_API_KEY），"
    echo " 然后重新运行本脚本。"
    echo "============================================================"
    exit 0
else
    echo "[3/5] 已存在 backend/.env。"
fi

# ---------- 4. 前端：安装依赖 ----------
if [ ! -d "frontend/node_modules" ]; then
    echo "[4/5] 安装前端依赖（使用国内镜像源加速）..."
    (cd frontend && npm install --registry=https://registry.npmmirror.com)
else
    echo "[4/5] 前端依赖已存在，跳过安装。"
fi

# ---------- 5. 同时启动前后端 ----------
echo "[5/5] 启动服务..."
echo "  后端: http://localhost:8002"
echo "  前端: http://localhost:3000"
echo

# 后端后台启动，前端前台启动；Ctrl+C 时一并清理
(cd backend && python app.py) &
BACKEND_PID=$!

cleanup() {
    echo
    echo "正在停止服务..."
    kill "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

(cd frontend && npm run dev)
