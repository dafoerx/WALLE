#!/bin/bash
# ============================================
# 语音对话系统 - 一键启动脚本
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================"
echo "🎙️  AI 语音对话系统 (DeepSeek + Whisper + Edge-TTS)"
echo "============================================"
echo ""

# 激活 conda 环境
CONDA_BASE="/data/dafoer/miniconda3"
if [ -f "$CONDA_BASE/bin/activate" ]; then
    export PATH="$CONDA_BASE/bin:$PATH"
    source activate voicechat
    echo "✅ Conda 环境 (voicechat) 已激活"
else
    echo "❌ 未找到 conda 环境，请先安装:"
    echo "   1. 安装 miniconda: bash Miniconda3-latest-Linux-x86_64.sh -b -p /data/dafoer/miniconda3"
    echo "   2. 创建环境: conda create -n voicechat python=3.10 -y"
    echo "   3. 安装依赖: conda activate voicechat && pip install -r requirements.txt"
    echo "   4. 安装 ffmpeg: conda install -y ffmpeg"
    echo "   5. 安装 PyTorch: pip install torch --index-url https://download.pytorch.org/whl/cpu"
    exit 1
fi

PYTHON_VERSION=$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✅ Python 版本: $PYTHON_VERSION"

# 检查 .env 配置
if [ ! -f ".env" ]; then
    echo "❌ 未找到 .env 配置文件"
    exit 1
fi

# 检查 API Key
source .env 2>/dev/null || true
if [ -z "$DEEPSEEK_API_KEY" ]; then
    echo "⚠️  未配置 DEEPSEEK_API_KEY，请在 .env 文件中设置"
fi

echo ""
echo "============================================"
echo "🚀 启动语音对话服务器..."
echo "   地址: http://localhost:${SERVER_PORT:-8000}"
echo "   LLM:  DeepSeek (${DEEPSEEK_MODEL:-deepseek-chat})"
echo "   STT:  Whisper (${WHISPER_MODEL:-base})"
echo "   TTS:  Edge-TTS (${TTS_VOICE:-zh-CN-XiaoxiaoNeural})"
echo "============================================"
echo ""

python server.py
