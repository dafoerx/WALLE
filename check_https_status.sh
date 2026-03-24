#!/bin/bash
# ============================================
# 检查 WALLE + OpenClaw HTTPS 状态
# ============================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================"
echo "🔍 WALLE + OpenClaw HTTPS 状态检查"
echo "============================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 函数：检查服务
check_service() {
    local name=$1
    local url=$2
    local use_https=$3
    
    echo -n "检查 $name: "
    
    if [ "$use_https" = "true" ]; then
        # 使用HTTPS检查
        if curl -k -s "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ HTTPS 正常${NC}"
            echo "  地址: $url"
            return 0
        else
            # 尝试HTTP
            http_url=$(echo "$url" | sed 's|https://|http://|')
            if curl -s "$http_url" > /dev/null 2>&1; then
                echo -e "${YELLOW}⚠️  HTTP 正常 (未使用HTTPS)${NC}"
                echo "  地址: $http_url"
                return 1
            else
                echo -e "${RED}❌ 无法访问${NC}"
                return 2
            fi
        fi
    else
        # 使用HTTP检查
        if curl -s "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ HTTP 正常${NC}"
            echo "  地址: $url"
            return 0
        else
            echo -e "${RED}❌ 无法访问${NC}"
            return 2
        fi
    fi
}

# 检查进程
check_process() {
    local name=$1
    local pattern=$2
    
    echo -n "检查 $name 进程: "
    if pgrep -f "$pattern" > /dev/null; then
        echo -e "${GREEN}✅ 运行中${NC}"
        return 0
    else
        echo -e "${RED}❌ 未运行${NC}"
        return 1
    fi
}

# 检查文件
check_file() {
    local name=$1
    local file=$2
    
    echo -n "检查 $name: "
    if [ -f "$file" ]; then
        size=$(stat -c%s "$file" 2>/dev/null || stat -f%z "$file" 2>/dev/null)
        echo -e "${GREEN}✅ 存在 (${size} bytes)${NC}"
        return 0
    else
        echo -e "${RED}❌ 缺失${NC}"
        return 1
    fi
}

# 检查配置
check_config() {
    echo "检查 WALLE 配置:"
    
    if [ ! -f ".env" ]; then
        echo -e "  ${RED}❌ .env 文件不存在${NC}"
        return 1
    fi
    
    # 检查Base URL
    base_url=$(grep "DEEPSEEK_BASE_URL=" .env | cut -d= -f2)
    if [ -n "$base_url" ]; then
        echo -n "  DEEPSEEK_BASE_URL: "
        if [[ "$base_url" == https://* ]]; then
            echo -e "${GREEN}$base_url 🔒${NC}"
            echo -e "    ${GREEN}✅ 使用HTTPS协议${NC}"
        elif [[ "$base_url" == http://* ]]; then
            echo -e "${YELLOW}$base_url${NC}"
            echo -e "    ${YELLOW}⚠️  使用HTTP协议 (建议使用HTTPS)${NC}"
        else
            echo -e "${RED}$base_url${NC}"
            echo -e "    ${RED}❌ 无效的URL格式${NC}"
        fi
    else
        echo -e "  ${RED}❌ 未找到DEEPSEEK_BASE_URL配置${NC}"
    fi
    
    # 检查API Key
    api_key=$(grep "DEEPSEEK_API_KEY=" .env | cut -d= -f2)
    if [ -n "$api_key" ]; then
        echo -n "  DEEPSEEK_API_KEY: "
        if [ "$api_key" = "openclaw-proxy" ]; then
            echo -e "${GREEN}$api_key${NC}"
            echo -e "    ${GREEN}✅ 配置为使用OpenClaw代理${NC}"
        else
            echo -e "${YELLOW}$api_key${NC}"
            echo -e "    ${YELLOW}⚠️  可能不是OpenClaw代理配置${NC}"
        fi
    fi
    
    # 检查Model
    model=$(grep "DEEPSEEK_MODEL=" .env | cut -d= -f2)
    if [ -n "$model" ]; then
        echo "  DEEPSEEK_MODEL: $model"
    fi
}

# 主检查
echo "1. 检查进程状态:"
check_process "WALLE服务器" "python server.py"
check_process "OpenClaw代理" "openclaw_proxy.py"

echo ""
echo "2. 检查服务访问:"
check_service "WALLE界面" "https://localhost:8000" "true"
check_service "OpenClaw代理" "https://localhost:8081" "true"

echo ""
echo "3. 检查SSL证书:"
check_file "WALLE证书" "cert.pem"
check_file "WALLE密钥" "key.pem"
check_file "代理证书" "proxy_cert.pem"
check_file "代理密钥" "proxy_key.pem"

echo ""
check_config

echo ""
echo "4. 快速功能测试:"
echo -n "  WALLE API测试: "
if curl -k -s https://localhost:8000/api/voices > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 正常${NC}"
else
    echo -e "${RED}❌ 失败${NC}"
fi

echo -n "  OpenClaw API测试: "
if curl -k -s https://localhost:8081/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 正常${NC}"
else
    echo -e "${RED}❌ 失败${NC}"
fi

echo ""
echo "============================================"
echo "📋 总结与建议:"
echo ""

# 给出建议
if pgrep -f "python server.py" > /dev/null && \
   pgrep -f "openclaw_proxy.py" > /dev/null && \
   curl -k -s https://localhost:8000 > /dev/null 2>&1 && \
   curl -k -s https://localhost:8081 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 所有服务正常运行，HTTPS配置正确！${NC}"
    echo ""
    echo "🚀 可以开始使用:"
    echo "  1. 打开浏览器访问: https://localhost:8000"
    echo "  2. 接受安全警告（自签名证书）"
    echo "  3. 允许麦克风权限"
    echo "  4. 开始语音对话"
elif curl -s http://localhost:8000 > /dev/null 2>&1 && \
     curl -s http://localhost:8081 > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  服务运行但未使用HTTPS${NC}"
    echo ""
    echo "💡 建议:"
    echo "  - 确保SSL证书文件存在"
    echo "  - 重启服务以启用HTTPS"
    echo "  - 检查WALLE配置是否使用https://"
else
    echo -e "${RED}❌ 服务未完全运行或配置有问题${NC}"
    echo ""
    echo "🔧 需要检查:"
    echo "  - 服务是否启动"
    echo "  - 端口是否被占用"
    echo "  - 配置文件是否正确"
fi

echo ""
echo "🔗 访问地址:"
echo "  WALLE界面: https://localhost:8000"
echo "  OpenClaw代理: https://localhost:8081"
echo "  OpenClaw健康检查: https://localhost:8081/health"
echo ""
echo "⚠️  注意: 自签名证书需要手动接受安全警告"
echo "============================================"