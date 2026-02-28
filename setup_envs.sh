#!/bin/bash
#
# 一键配置 deepresearch_collection 的两个虚拟环境
#
# 用法：
#   bash setup_envs.sh
#
# 前置要求：
#   - Python 3.12（通过 uv、pyenv 或系统安装均可）
#   - pip
#
# 此脚本会在当前目录下创建：
#   .venv_tier1/  —— InfoAgent, MiroFlow, OAgents, pydantic-deepagents 共用
#   .venv_yunque/ —— YunqueAgent 专用（依赖版本与 tier1 不兼容）
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ---------- 检测 Python 3.12 ----------
PYTHON_CMD=""
for cmd in python3.12 python3; do
    if command -v "$cmd" &>/dev/null; then
        ver=$("$cmd" --version 2>&1 | awk '{print $2}')
        major=$(echo "$ver" | cut -d. -f1)
        minor=$(echo "$ver" | cut -d. -f2)
        if [ "$major" = "3" ] && [ "$minor" -ge "12" ]; then
            PYTHON_CMD="$cmd"
            break
        fi
    fi
done

# 也检查 uv 安装的 Python
if [ -z "$PYTHON_CMD" ] && [ -f "$HOME/.local/share/uv/python/cpython-3.12.9-macos-x86_64-none/bin/python3.12" ]; then
    PYTHON_CMD="$HOME/.local/share/uv/python/cpython-3.12.9-macos-x86_64-none/bin/python3.12"
fi

if [ -z "$PYTHON_CMD" ]; then
    echo "Error: Python >= 3.12 not found."
    echo "Install it via one of:"
    echo "  uv python install 3.12"
    echo "  brew install python@3.12"
    echo "  pyenv install 3.12"
    exit 1
fi

echo "Using Python: $PYTHON_CMD ($($PYTHON_CMD --version))"
echo ""

# ---------- 创建 .venv_tier1 ----------
if [ -d ".venv_tier1" ]; then
    echo "[.venv_tier1] Already exists, skipping creation."
else
    echo "[.venv_tier1] Creating virtual environment..."
    "$PYTHON_CMD" -m venv .venv_tier1
fi

echo "[.venv_tier1] Installing dependencies..."
source .venv_tier1/bin/activate
pip install --upgrade pip -q

# 先装 requirements_tier1.txt（声明式依赖）
pip install -r requirements_tier1.txt -q

# 安装 OAgents（本地包）
if [ -d "OAgents/OAgents" ]; then
    pip install -e OAgents/OAgents -q 2>/dev/null || echo "  [warn] OAgents install skipped (optional)"
fi

# 再用冻结文件补齐精确版本
pip install -r requirements_tier1_freeze.txt -q 2>/dev/null || echo "  [warn] Some tier1 freeze packages may have platform-specific issues, continuing..."

deactivate
echo "[.venv_tier1] Done. ($(source .venv_tier1/bin/activate && pip list 2>/dev/null | wc -l | tr -d ' ') packages)"
echo ""

# ---------- 创建 .venv_yunque ----------
if [ -d ".venv_yunque" ]; then
    echo "[.venv_yunque] Already exists, skipping creation."
else
    echo "[.venv_yunque] Creating virtual environment..."
    "$PYTHON_CMD" -m venv .venv_yunque
fi

echo "[.venv_yunque] Installing dependencies..."
source .venv_yunque/bin/activate
pip install --upgrade pip -q
pip install -r requirements_yunque.txt -q 2>/dev/null || echo "  [warn] Some yunque packages may have platform-specific issues, continuing..."
deactivate
echo "[.venv_yunque] Done. ($(source .venv_yunque/bin/activate && pip list 2>/dev/null | wc -l | tr -d ' ') packages)"
echo ""

# ---------- 检查 .env 文件 ----------
echo "=========================================="
echo "Environment setup complete!"
echo "=========================================="
echo ""
echo "Next steps — configure API keys:"
echo ""

env_files=(
    "InfoAgent/retrac/retrac/.env:InfoAgent/retrac/retrac/.env.example"
    "MiroFlow/.env:MiroFlow/.env.template"
    "YunqueAgent/.env:YunqueAgent/.env.example"
    "OAgents/OAgents/.env:OAgents/OAgents/.env.example"
    "OAgents/Efficient_Agents/.env:OAgents/Efficient_Agents/.env.example"
    "pydantic-deepagents/deepresearch/.env:pydantic-deepagents/deepresearch/.env.example"
)

for entry in "${env_files[@]}"; do
    target="${entry%%:*}"
    example="${entry##*:}"
    if [ ! -f "$target" ]; then
        if [ -f "$example" ]; then
            echo "  cp $example $target"
        else
            echo "  # Create $target manually (no example file found)"
        fi
    else
        echo "  $target  [already exists]"
    fi
done

echo ""
echo "Run scripts:"
echo "  bash run_infoagent.sh \"Your research topic\""
echo "  bash run_miroflow.sh \"Your research topic\""
echo "  bash run_oagents.sh \"Your research topic\""
echo "  bash run_pydantic_deepagents.sh \"Your research topic\""
echo "  bash run_yunqueagent.sh \"Your research topic\""
