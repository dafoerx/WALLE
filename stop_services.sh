#!/bin/bash
# ============================================
# 停止 WALLE 和 OpenClaw 代理服务
# ============================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================"
echo "🛑 停止 WALLE + OpenClaw 服务"
echo "============================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 函数：打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 停止 WALLE 服务器
stop_walle() {
    print_info "停止 WALLE 服务器..."
    
    # 通过 PID 文件停止
    if [ -f ".walle.pid" ]; then
        WALLE_PID=$(cat .walle.pid)
        if kill -0 $WALLE_PID 2>/dev/null; then
            kill $WALLE_PID
            print_info "已发送停止信号给 WALLE (PID: $WALLE_PID)"
            
            # 等待进程结束
            for i in {1..10}; do
                if ! kill -0 $WALLE_PID 2>/dev/null; then
                    print_success "WALLE 服务器已停止"
                    rm -f .walle.pid
                    return 0
                fi
                sleep 1
            done
            
            # 如果还在运行，强制杀死
            kill -9 $WALLE_PID 2>/dev/null && print_warning "强制停止 WALLE 服务器"
            rm -f .walle.pid
        else
            rm -f .walle.pid
        fi
    fi
    
    # 通过进程名停止
    if pgrep -f "python server.py" > /dev/null; then
        print_info "发现 WALLE 进程，正在停止..."
        pkill -f "python server.py"
        sleep 2
        
        if pgrep -f "python server.py" > /dev/null; then
            pkill -9 -f "python server.py"
            print_warning "强制停止 WALLE 进程"
        fi
        
        print_success "WALLE 服务器已停止"
    else
        print_info "WALLE 服务器未在运行"
    fi
}

# 停止 OpenClaw 代理服务器
stop_proxy() {
    print_info "停止 OpenClaw 代理服务器..."
    
    # 通过 PID 文件停止
    if [ -f ".proxy.pid" ]; then
        PROXY_PID=$(cat .proxy.pid)
        if kill -0 $PROXY_PID 2>/dev/null; then
            kill $PROXY_PID
            print_info "已发送停止信号给代理服务器 (PID: $PROXY_PID)"
            
            # 等待进程结束
            for i in {1..5}; do
                if ! kill -0 $PROXY_PID 2>/dev/null; then
                    print_success "OpenClaw 代理服务器已停止"
                    rm -f .proxy.pid
                    return 0
                fi
                sleep 1
            done
            
            # 如果还在运行，强制杀死
            kill -9 $PROXY_PID 2>/dev/null && print_warning "强制停止代理服务器"
            rm -f .proxy.pid
        else
            rm -f .proxy.pid
        fi
    fi
    
    # 通过进程名停止
    if pgrep -f "openclaw_proxy.py" > /dev/null; then
        print_info "发现代理服务器进程，正在停止..."
        pkill -f "openclaw_proxy.py"
        sleep 2
        
        if pgrep -f "openclaw_proxy.py" > /dev/null; then
            pkill -9 -f "openclaw_proxy.py"
            print_warning "强制停止代理服务器进程"
        fi
        
        print_success "OpenClaw 代理服务器已停止"
    else
        print_info "OpenClaw 代理服务器未在运行"
    fi
}

# 恢复原配置
restore_config() {
    print_info "恢复 WALLE 原配置..."
    
    if [ -f ".env.backup" ]; then
        cp .env.backup .env
        print_success "已恢复原 .env 配置"
    else
        print_info "未找到备份配置，保持当前配置"
    fi
}

# 清理日志文件
cleanup_logs() {
    print_info "清理日志文件..."
    
    # 保留最新的日志，压缩旧的
    for logfile in walle.log openclaw_proxy.log; do
        if [ -f "$logfile" ]; then
            if [ $(stat -c%s "$logfile") -gt 10485760 ]; then  # 大于10MB
                print_info "压缩 $logfile..."
                gzip -c "$logfile" > "${logfile}.$(date +%Y%m%d).gz"
                > "$logfile"  # 清空文件
            fi
        fi
    done
    
    print_success "日志清理完成"
}

# 显示停止后的状态
show_status() {
    echo ""
    echo "============================================"
    echo "📊 停止后状态"
    echo "============================================"
    
    # 检查进程
    WALLE_RUNNING=$(pgrep -f "python server.py" > /dev/null && echo "是" || echo "否")
    PROXY_RUNNING=$(pgrep -f "openclaw_proxy.py" > /dev/null && echo "是" || echo "否")
    
    echo "WALLE 服务器运行: $WALLE_RUNNING"
    echo "OpenClaw 代理运行: $PROXY_RUNNING"
    
    # 检查端口
    echo ""
    echo "端口占用情况:"
    if netstat -tuln 2>/dev/null | grep -q ":8000 "; then
        echo "  端口 8000 (WALLE): 占用"
    else
        echo "  端口 8000 (WALLE): 空闲"
    fi
    
    if netstat -tuln 2>/dev/null | grep -q ":8081 "; then
        echo "  端口 8081 (代理): 占用"
    else
        echo "  端口 8081 (代理): 空闲"
    fi
    
    echo ""
    echo "✅ 服务停止完成"
    echo "============================================"
}

# 主函数
main() {
    # 停止服务
    stop_walle
    stop_proxy
    
    # 询问是否恢复配置
    echo ""
    read -p "是否恢复 WALLE 原配置？(y/N): " restore_choice
    if [[ "$restore_choice" =~ ^[Yy]$ ]]; then
        restore_config
    fi
    
    # 询问是否清理日志
    echo ""
    read -p "是否清理日志文件？(y/N): " cleanup_choice
    if [[ "$cleanup_choice" =~ ^[Yy]$ ]]; then
        cleanup_logs
    fi
    
    # 显示状态
    show_status
}

# 执行主函数
main "$@"