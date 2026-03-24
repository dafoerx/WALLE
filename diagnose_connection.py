#!/usr/bin/env python3
"""
诊断WALLE连接问题
"""

import requests
import json
import urllib3
from openai import OpenAI
import httpx

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_direct_requests():
    """测试直接使用requests"""
    print("1. 测试直接使用requests:")
    
    url = "https://localhost:8081/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    data = {
        "model": "openclaw-chat",
        "messages": [{"role": "user", "content": "测试连接"}],
        "stream": False
    }
    
    try:
        resp = requests.post(url, json=data, verify=False, timeout=10)
        print(f"   Status: {resp.status_code}")
        if resp.status_code == 200:
            result = resp.json()
            print(f"   ✅ 成功: {result['choices'][0]['message']['content'][:50]}...")
        else:
            print(f"   ❌ 失败: {resp.text[:100]}")
    except Exception as e:
        print(f"   ❌ 异常: {e}")

def test_openai_client():
    """测试OpenAI客户端"""
    print("\n2. 测试OpenAI客户端:")
    
    # 方法1: 使用默认配置
    print("   方法1: 默认配置")
    try:
        client = OpenAI(
            api_key="openclaw-proxy",
            base_url="https://localhost:8081"
        )
        
        response = client.chat.completions.create(
            model="openclaw-chat",
            messages=[{"role": "user", "content": "测试OpenAI客户端"}],
            stream=False
        )
        print(f"   ✅ 成功: {response.choices[0].message.content[:50]}...")
    except Exception as e:
        print(f"   ❌ 失败: {e}")
    
    # 方法2: 使用自定义HTTP客户端
    print("   方法2: 自定义HTTP客户端")
    try:
        http_client = httpx.Client(
            verify=False,  # 禁用SSL验证
            timeout=30.0
        )
        
        client = OpenAI(
            api_key="openclaw-proxy",
            base_url="https://localhost:8081",
            http_client=http_client
        )
        
        response = client.chat.completions.create(
            model="openclaw-chat",
            messages=[{"role": "user", "content": "测试自定义HTTP客户端"}],
            stream=False
        )
        print(f"   ✅ 成功: {response.choices[0].message.content[:50]}...")
    except Exception as e:
        print(f"   ❌ 失败: {e}")
    
    # 方法3: 使用httpx.AsyncClient
    print("   方法3: 异步客户端")
    try:
        import asyncio
        
        async def test_async():
            async with httpx.AsyncClient(verify=False) as client:
                openai_client = OpenAI(
                    api_key="openclaw-proxy",
                    base_url="https://localhost:8081",
                    http_client=client
                )
                
                response = await openai_client.chat.completions.create(
                    model="openclaw-chat",
                    messages=[{"role": "user", "content": "测试异步客户端"}],
                    stream=False
                )
                return response
        
        response = asyncio.run(test_async())
        print(f"   ✅ 成功: {response.choices[0].message.content[:50]}...")
    except Exception as e:
        print(f"   ❌ 失败: {e}")

def test_walle_config():
    """测试WALLE当前配置"""
    print("\n3. 测试WALLE当前配置:")
    
    # 读取.env文件
    try:
        with open(".env", "r") as f:
            env_content = f.read()
            print("   .env内容:")
            for line in env_content.strip().split('\n'):
                if line.strip() and not line.startswith('#'):
                    print(f"     {line}")
    except:
        print("   无法读取.env文件")
    
    # 测试当前配置的连接
    print("\n   测试当前配置的连接:")
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    
    print(f"   Base URL: {base_url}")
    print(f"   API Key: {api_key[:10]}...")
    print(f"   Model: {model}")
    
    try:
        # 使用与WALLE相同的方式
        client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "测试WALLE配置"}],
            stream=False,
            timeout=10
        )
        print(f"   ✅ 连接成功: {response.choices[0].message.content[:50]}...")
    except Exception as e:
        print(f"   ❌ 连接失败: {e}")

def check_network_issues():
    """检查网络问题"""
    print("\n4. 检查网络问题:")
    
    import socket
    
    # 检查端口
    ports = [(8000, "WALLE"), (8081, "OpenClaw代理")]
    
    for port, service in ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('localhost', port))
            if result == 0:
                print(f"   ✅ 端口 {port} ({service}): 开放")
            else:
                print(f"   ❌ 端口 {port} ({service}): 关闭")
            sock.close()
        except Exception as e:
            print(f"   ⚠️  端口 {port} ({service}): 检查失败 - {e}")
    
    # 检查DNS
    print("\n   检查DNS解析:")
    try:
        ip = socket.gethostbyname('localhost')
        print(f"   ✅ localhost解析为: {ip}")
    except Exception as e:
        print(f"   ❌ DNS解析失败: {e}")

if __name__ == "__main__":
    print("🔧 诊断WALLE连接问题")
    print("=" * 60)
    
    test_direct_requests()
    test_openai_client()
    test_walle_config()
    check_network_issues()
    
    print("\n" + "=" * 60)
    print("📋 诊断完成")
    print("\n💡 建议:")
    print("   1. 如果直接requests成功但OpenAI客户端失败，可能是OpenAI库版本问题")
    print("   2. 尝试更新或降级openai库: pip install openai==1.12.0")
    print("   3. 检查WALLE的.env配置文件是否正确")
    print("   4. 确保代理服务器返回正确的OpenAI兼容格式")