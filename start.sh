#!/bin/bash
# Chess Game Launcher
# 启动象棋游戏服务器

echo "========================================="
echo "      国际象棋对战平台"
echo "========================================="
echo ""

# 进入脚本所在目录
cd "$(dirname "$0")"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 Python3"
    echo "请安装 Python3: https://www.python.org/downloads/"
    exit 1
fi

echo "✓ Python 版本: $(python3 --version)"

# 准备虚拟环境，避免系统 Python 的受管环境限制（PEP 668）
if [ ! -d ".venv" ]; then
    echo ""
    echo "正在创建虚拟环境..."
    python3 -m venv .venv
    if [ $? -ne 0 ]; then
        echo "❌ 虚拟环境创建失败"
        exit 1
    fi
fi

VENV_PYTHON="./.venv/bin/python"
VENV_PIP="./.venv/bin/pip"

# 检查并安装依赖
if ! "$VENV_PYTHON" -c "import flask; import chess; import requests" 2>/dev/null; then
    echo ""
    echo "正在安装依赖..."
    "$VENV_PIP" install -r requirements.txt --quiet

    if [ $? -ne 0 ]; then
        echo "❌ 依赖安装失败"
        echo "请手动运行: ./.venv/bin/pip install -r requirements.txt"
        exit 1
    fi
fi

echo "✓ 依赖已安装"

# 检查 Stockfish (可选)
if command -v stockfish &> /dev/null; then
    echo "✓ Stockfish 已安装"
else
    echo "⚠ 未安装 Stockfish (将使用内置AI)"
    echo "  安装方法: brew install stockfish (macOS)"
    echo "           或访问: https://stockfishchess.org/download/"
fi

echo ""
echo "========================================="
echo "启动服务器..."
echo "访问地址: http://localhost:5001"
echo "按 Ctrl+C 停止服务器"
echo "========================================="
echo ""

# 启动服务器
"$VENV_PYTHON" app.py