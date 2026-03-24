#!/bin/bash
# ============================================
# WALLE 快速启动脚本
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================"
echo "🚀 WALLE 快速启动"
echo "============================================"
echo ""

# 检查Python环境
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "✅ Python虚拟环境已激活"
else
    echo "❌ 未找到虚拟环境，请先安装依赖"
    exit 1
fi

# 检查SSL证书
if [ ! -f "cert.pem" ] || [ ! -f "key.pem" ]; then
    echo "🔐 生成WALLE SSL证书..."
    openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes -subj '/CN=WALLE' > /dev/null 2>&1
    echo "✅ WALLE SSL证书生成完成"
fi

if [ ! -f "proxy_cert.pem" ] || [ ! -f "proxy_key.pem" ]; then
    echo "🔐 生成代理SSL证书..."
    openssl req -x509 -newkey rsa:2048 -keyout proxy_key.pem -out proxy_cert.pem -days 365 -nodes -subj '/CN=OpenClaw-Proxy' > /dev/null 2>&1
    echo "✅ 代理SSL证书生成完成"
fi

# 检查端口占用
check_port() {
    local port=$1
    local service=$2
    if lsof -i :$port > /dev/null 2>&1; then
        echo "⚠️  端口 $port 被占用 ($service)"
        lsof -i :$port | head -5
        echo "是否杀死占用进程？(y/N): "
        read choice
        if [[ "$choice" =~ ^[Yy]$ ]]; then
            lsof -ti :$port | xargs kill -9 2>/dev/null
            echo "✅ 已清理端口 $port"
            sleep 1
        else
            echo "❌ 端口被占用，无法启动服务"
            exit 1
        fi
    fi
}

check_port 8000 "WALLE"
check_port 8081 "OpenClaw代理"

# 启动OpenClaw代理服务器（增强版）
echo ""
echo "🚀 启动 OpenClaw 代理服务器（增强版）..."
nohup python openclaw_proxy_enhanced.py --port 8081 --ssl > proxy.log 2>&1 &
PROXY_PID=$!
sleep 3

if curl -k -s https://localhost:8081/health > /dev/null 2>&1; then
    echo "✅ OpenClaw代理启动成功 (PID: $PROXY_PID)"
    echo $PROXY_PID > .proxy.pid
else
    echo "❌ OpenClaw代理启动失败"
    echo "查看日志: tail -f proxy.log"
    exit 1
fi

# 启动WALLE服务器
echo ""
echo "🚀 启动 WALLE 服务器..."
nohup python server.py > walle.log 2>&1 &
WALLE_PID=$!
sleep 5

if curl -k -s https://localhost:8000 > /dev/null 2>&1; then
    echo "✅ WALLE服务器启动成功 (PID: $WALLE_PID)"
    echo $WALLE_PID > .walle.pid
else
    echo "❌ WALLE服务器启动失败"
    echo "查看日志: tail -f walle.log"
    # 尝试查看日志最后几行
    tail -20 walle.log 2>/dev/null || echo "无日志文件"
    exit 1
fi

# 测试集成
echo ""
echo "🧪 测试集成功能..."

echo "1. 测试OpenClaw代理..."
if curl -k -s https://localhost:8081/health | grep -q "healthy"; then
    echo "   ✅ OpenClaw代理健康检查通过"
else
    echo "   ❌ OpenClaw代理健康检查失败"
fi

echo "2. 测试WALLE API..."
if curl -k -s https://localhost:8000/api/voices > /dev/null 2>&1; then
    echo "   ✅ WALLE API测试通过"
else
    echo "   ❌ WALLE API测试失败"
fi

echo "3. 测试GitHub Trending功能..."
RESPONSE=$(curl -k -s https://localhost:8081/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"openclaw-chat","messages":[{"role":"user","content":"查看GitHub热门项目"}]}' 2>/dev/null)

if echo "$RESPONSE" | grep -q "GitHub"; then
    echo "   ✅ GitHub Trending功能正常"
else
    echo "   ❌ GitHub Trending功能异常"
    echo "   响应: ${RESPONSE:0:100}..."
fi

echo ""
echo "============================================"
echo "🎉 WALLE 启动完成！"
echo "============================================"
echo ""
echo "📋 服务状态:"
echo "   🔒 WALLE界面: https://localhost:8000"
echo "   🔒 OpenClaw代理: https://localhost:8081"
echo ""
echo "📋 使用步骤:"
echo "   1. 浏览器访问: https://localhost:8000"
echo "   2. 接受安全警告（点击'高级'->'继续前往'）"
echo "   3. 允许麦克风权限"
echo "   4. 点击页面任意位置解锁音频"
echo "   5. 点击麦克风按钮开始语音对话"
echo ""
echo "💡 语音命令示例:"
echo "   • '查看GitHub今日热门项目'"
echo "   • '看看Hacker News新闻'"
echo "   • '现在几点了？'"
echo "   • '搜索一下人工智能'"
echo ""
echo "🔧 管理命令:"
echo "   查看日志: tail -f walle.log 或 tail -f proxy.log"
echo "   停止服务: ./stop_services.sh"
echo "   检查状态: ./check_https_status.sh"
echo ""
echo "⚠️  注意: 首次访问需要接受自签名证书警告"
echo "============================================"