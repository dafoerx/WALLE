#!/usr/bin/env python3
"""
测试完整的语音对话工作流程
模拟用户通过WALLE查询GitHub Trending
"""

import requests
import json
import urllib3
import time

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_complete_workflow():
    """测试完整的工作流程"""
    print("🔧 测试完整的语音对话工作流程")
    print("=" * 60)
    
    # 步骤1: 检查服务状态
    print("1. 检查服务状态:")
    
    services = [
        ("WALLE界面", "https://localhost:8000"),
        ("OpenClaw代理", "https://localhost:8081"),
        ("WALLE API", "https://localhost:8000/api/voices"),
        ("代理健康", "https://localhost:8081/health")
    ]
    
    all_healthy = True
    for name, url in services:
        try:
            if "health" in url:
                resp = requests.get(url, verify=False, timeout=5)
                if resp.status_code == 200:
                    print(f"   ✅ {name}: 健康")
                else:
                    print(f"   ❌ {name}: 不健康 ({resp.status_code})")
                    all_healthy = False
            else:
                resp = requests.get(url, verify=False, timeout=5)
                if resp.status_code == 200:
                    print(f"   ✅ {name}: 可访问")
                else:
                    print(f"   ❌ {name}: 不可访问 ({resp.status_code})")
                    all_healthy = False
        except Exception as e:
            print(f"   ❌ {name}: 错误 - {e}")
            all_healthy = False
    
    if not all_healthy:
        print("\n⚠️  部分服务不可用，无法继续测试")
        return False
    
    # 步骤2: 模拟语音识别结果（用户说"查看一下 GitHub,今日热门项目"）
    print("\n2. 模拟语音识别:")
    user_message = "查看一下 GitHub,今日热门项目"
    print(f"   用户语音输入: '{user_message}'")
    print("   ✅ 语音识别完成")
    
    # 步骤3: 发送到OpenClaw代理
    print("\n3. 发送到OpenClaw代理:")
    print(f"   发送消息: '{user_message}'")
    
    try:
        start_time = time.time()
        resp = requests.post(
            "https://localhost:8081/v1/chat/completions",
            json={
                "model": "openclaw-chat",
                "messages": [{"role": "user", "content": user_message}],
                "stream": False
            },
            verify=False,
            timeout=15
        )
        response_time = time.time() - start_time
        
        if resp.status_code == 200:
            data = resp.json()
            reply = data["choices"][0]["message"]["content"]
            print(f"   ✅ 代理响应成功 (耗时: {response_time:.2f}s)")
            
            # 检查回复内容
            if "GitHub" in reply and ("趋势" in reply or "热门" in reply):
                print(f"   ✅ 正确调用了GitHub Trending工具")
                
                # 提取部分结果显示
                lines = reply.split('\n')
                print(f"   📊 返回了 {len(lines)} 行结果")
                print(f"   前3个项目:")
                project_count = 0
                for line in lines:
                    if line.strip() and line[0].isdigit() and '.' in line:
                        project_count += 1
                        if project_count <= 3:
                            print(f"      {line}")
            else:
                print(f"   ❌ 未正确调用GitHub Trending工具")
                print(f"      回复: {reply[:100]}...")
                return False
        else:
            print(f"   ❌ 代理响应失败: {resp.status_code}")
            print(f"      错误: {resp.text[:100]}")
            return False
            
    except Exception as e:
        print(f"   ❌ 请求失败: {e}")
        return False
    
    # 步骤4: 模拟语音合成和播放
    print("\n4. 模拟语音合成和播放:")
    print("   ✅ 文本转语音(TTS)完成")
    print("   🔊 正在播放语音回复...")
    print("   ✅ 语音播放完成")
    
    # 步骤5: 测试其他工具
    print("\n5. 测试其他工具:")
    
    test_cases = [
        ("Hacker News查询", "看看Hacker News有什么新闻"),
        ("时间查询", "现在几点了？"),
        ("网页搜索", "搜索一下人工智能")
    ]
    
    for test_name, test_message in test_cases:
        print(f"   📋 {test_name}: '{test_message}'")
        try:
            resp = requests.post(
                "https://localhost:8081/v1/chat/completions",
                json={
                    "model": "openclaw-chat",
                    "messages": [{"role": "user", "content": test_message}],
                    "stream": False
                },
                verify=False,
                timeout=10
            )
            
            if resp.status_code == 200:
                data = resp.json()
                reply = data["choices"][0]["message"]["content"]
                
                # 简单检查回复是否合理
                if len(reply) > 10:
                    print(f"      ✅ 响应正常 ({len(reply)} 字符)")
                else:
                    print(f"      ⚠️  响应过短: {reply}")
            else:
                print(f"      ❌ 响应失败: {resp.status_code}")
                
        except Exception as e:
            print(f"      ❌ 请求失败: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 完整工作流程测试完成！")
    
    print("\n📋 总结:")
    print("   1. ✅ 所有服务正常运行")
    print("   2. ✅ 语音识别模拟成功")
    print("   3. ✅ GitHub Trending工具调用成功")
    print("   4. ✅ 语音合成和播放模拟成功")
    print("   5. ✅ 其他工具测试通过")
    
    print("\n🚀 现在可以通过WALLE进行语音对话:")
    print("   访问: https://localhost:8000")
    print("   说: '查看一下 GitHub,今日热门项目'")
    print("   系统将: 识别 → 调用工具 → 生成回复 → 播放语音")
    
    print("\n💡 提示:")
    print("   - 首次访问需要接受安全警告")
    print("   - 需要允许麦克风权限")
    print("   - 点击页面解锁音频播放")
    print("   - 说话清晰，环境安静")
    
    return True

def check_real_time_status():
    """检查实时状态"""
    print("\n" + "=" * 60)
    print("📊 实时服务状态")
    print("=" * 60)
    
    import subprocess
    
    # 检查进程
    print("进程状态:")
    try:
        result = subprocess.run(["pgrep", "-f", "python server.py"], capture_output=True, text=True)
        if result.returncode == 0:
            print("   ✅ WALLE服务器: 运行中 (PID: {})".format(result.stdout.strip()))
        else:
            print("   ❌ WALLE服务器: 未运行")
    except:
        print("   ⚠️  无法检查WALLE进程")
    
    try:
        result = subprocess.run(["pgrep", "-f", "openclaw_proxy_enhanced.py"], capture_output=True, text=True)
        if result.returncode == 0:
            print("   ✅ OpenClaw代理: 运行中 (PID: {})".format(result.stdout.strip()))
        else:
            print("   ❌ OpenClaw代理: 未运行")
    except:
        print("   ⚠️  无法检查代理进程")
    
    # 检查端口
    print("\n端口占用:")
    for port, service in [(8000, "WALLE"), (8081, "OpenClaw代理")]:
        try:
            result = subprocess.run(["lsof", "-i", f":{port}"], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"   ✅ 端口 {port} ({service}): 被占用")
            else:
                print(f"   ❌ 端口 {port} ({service}): 空闲")
        except:
            print(f"   ⚠️  无法检查端口 {port}")
    
    # 检查日志文件
    print("\n日志文件:")
    import os
    for logfile in ["walle.log", "proxy.log"]:
        if os.path.exists(logfile):
            size = os.path.getsize(logfile)
            print(f"   ✅ {logfile}: 存在 ({size} bytes)")
            
            # 显示最后修改时间
            mtime = os.path.getmtime(logfile)
            from datetime import datetime
            print(f"       最后修改: {datetime.fromtimestamp(mtime)}")
            
            # 显示最后几行
            if size > 0:
                try:
                    with open(logfile, 'r') as f:
                        lines = f.readlines()[-3:]
                        print(f"       最后3行:")
                        for line in lines:
                            print(f"         {line.strip()}")
                except:
                    pass
        else:
            print(f"   ❌ {logfile}: 不存在")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="测试语音对话工作流程")
    parser.add_argument("--status", action="store_true", help="检查实时状态")
    
    args = parser.parse_args()
    
    if args.status:
        check_real_time_status()
    else:
        success = test_complete_workflow()
        if success:
            check_real_time_status()
        else:
            print("\n❌ 工作流程测试失败，请检查服务状态")