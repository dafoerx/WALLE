#!/usr/bin/env python3
"""
测试 WALLE 的 GitHub Trending 功能
通过语音对话系统查询GitHub热门项目
"""

import requests
import json
import urllib3

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_github_trending_via_proxy():
    """通过代理服务器测试GitHub Trending"""
    print("🔧 测试 GitHub Trending 功能")
    print("=" * 60)
    
    # 测试直接调用代理服务器
    print("1. 直接调用代理服务器:")
    
    test_messages = [
        "查看一下 GitHub,今日热门项目",
        "GitHub有什么趋势项目？",
        "看看今天的GitHub热门",
        "查询GitHub趋势项目"
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n   📋 测试 {i}: {message}")
        
        try:
            resp = requests.post(
                "https://localhost:8081/v1/chat/completions",
                json={
                    "model": "openclaw-chat",
                    "messages": [{"role": "user", "content": message}],
                    "stream": False
                },
                verify=False,
                timeout=10
            )
            
            if resp.status_code == 200:
                data = resp.json()
                reply = data["choices"][0]["message"]["content"]
                
                # 检查是否包含GitHub Trending信息
                if "GitHub" in reply and ("趋势" in reply or "热门" in reply):
                    print(f"      ✅ 成功: 返回GitHub趋势信息")
                    # 显示部分结果
                    lines = reply.split('\n')
                    for line in lines[:8]:
                        if line.strip():
                            print(f"         {line}")
                    if len(lines) > 8:
                        print(f"         ... (共{len(lines)}行)")
                else:
                    print(f"      ⚠️  警告: 未返回GitHub趋势信息")
                    print(f"         回复: {reply[:80]}...")
            else:
                print(f"      ❌ HTTP错误: {resp.status_code}")
                print(f"         响应: {resp.text[:100]}")
                
        except Exception as e:
            print(f"      ❌ 请求失败: {e}")
    
    # 测试WALLE API
    print("\n2. 测试 WALLE API:")
    try:
        resp = requests.get("https://localhost:8000/api/voices", verify=False, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            print(f"   ✅ WALLE API正常 ({len(data['voices'])} 种语音)")
        else:
            print(f"   ❌ WALLE API错误: {resp.status_code}")
    except Exception as e:
        print(f"   ❌ WALLE API失败: {e}")
    
    # 测试代理服务器工具列表
    print("\n3. 测试代理服务器工具支持:")
    try:
        resp = requests.get("https://localhost:8081/tools", verify=False, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            print(f"   ✅ 工具列表正常 ({data['count']} 个工具)")
            for tool in data["tools"]:
                name = tool["function"]["name"]
                desc = tool["function"]["description"]
                print(f"      • {name}: {desc[:60]}...")
        else:
            print(f"   ❌ 工具列表错误: {resp.status_code}")
    except Exception as e:
        print(f"   ❌ 工具列表失败: {e}")
    
    # 测试健康检查
    print("\n4. 测试服务健康状态:")
    try:
        resp = requests.get("https://localhost:8081/health", verify=False, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            print(f"   ✅ 代理服务器健康: {data['status']}")
            print(f"      对话数: {data['conversations']}")
            print(f"      工具数: {data['tools']}")
        else:
            print(f"   ❌ 健康检查错误: {resp.status_code}")
    except Exception as e:
        print(f"   ❌ 健康检查失败: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 GitHub Trending 功能测试完成！")
    
    print("\n📋 语音对话测试指南:")
    print("   1. 访问 https://localhost:8000")
    print("   2. 接受安全警告")
    print("   3. 允许麦克风权限")
    print("   4. 点击麦克风按钮")
    print("   5. 说: '查看GitHub今日热门项目'")
    print("   6. 松开按钮发送")
    print("   7. 等待系统回复")
    
    print("\n💡 预期结果:")
    print("   - 系统识别你的语音")
    print("   - 调用GitHub Trending工具")
    print("   - 返回GitHub热门项目列表")
    print("   - 通过语音播放结果")
    
    print("\n🔧 其他可用的工具查询:")
    print("   - '看看Hacker News新闻'")
    print("   - '现在几点了？'")
    print("   - '搜索一下AI技术'")
    print("   - '获取网页内容 https://...'")

def test_specific_tools():
    """测试特定工具"""
    print("\n" + "=" * 60)
    print("🛠️  详细工具测试")
    print("=" * 60)
    
    from openclaw_proxy_enhanced import ToolExecutor
    
    executor = ToolExecutor()
    
    print("1. GitHub Trending 工具测试:")
    result = executor.github_trending(language="python", since="daily", count=3)
    print(result[:200] + "...")
    
    print("\n2. Hacker News 工具测试:")
    result = executor.hacker_news_top(count=3)
    print(result[:200] + "...")
    
    print("\n3. 时间工具测试:")
    result = executor.get_current_time()
    print(result)
    
    print("\n4. 网页搜索工具测试:")
    result = executor.web_search(query="人工智能", count=3)
    print(result[:200] + "...")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="测试 GitHub Trending 功能")
    parser.add_argument("--tools", action="store_true", help="测试具体工具")
    
    args = parser.parse_args()
    
    if args.tools:
        test_specific_tools()
    else:
        test_github_trending_via_proxy()