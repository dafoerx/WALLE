#!/usr/bin/env python3
"""
简单的LLM引擎 - 使用requests代替OpenAI客户端
解决OpenAI库v2.x的SSL连接问题
"""

import os
import json
import logging
import threading
import requests
import urllib3
from typing import Generator, List, Dict, Optional, Any

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

# 默认系统提示词
DEFAULT_SYSTEM_PROMPT = """你是一个友好的 AI 语音助手，具备联网查询能力。请用简洁自然的口语风格回答用户的问题。
注意事项：
1. 回答要简短精炼，适合语音播放
2. 不要使用 markdown 格式、代码块、列表符号等
3. 不要输出表情符号 emoji
4. 用自然的中文口语表达，像朋友聊天一样
5. 如果用户说的内容不清楚，可以礼貌地请他再说一遍
6. 当用户询问实时信息（新闻、热门项目、当前时间等），你必须调用工具获取真实数据，不要编造
7. 整理工具返回的数据后，用口语化的方式念给用户，每条信息简明扼要"""


class LLMEngineSimple:
    """简单的DeepSeek对话引擎 - 使用requests，解决SSL问题"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-chat",
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        max_history: int = 20,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_executor: Optional[Any] = None,
    ):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.system_prompt = system_prompt
        self.max_history = max_history
        self.tools = tools  # Function Calling 工具定义
        self.tool_executor = tool_executor  # 工具执行函数: (name, args) -> str
        self._stop_event = threading.Event()  # 中断标志

        # 对话历史
        self.messages: List[Dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt}
        ]

        # 配置requests会话
        self.session = requests.Session()
        self.session.verify = False  # 禁用SSL验证
        self.session.timeout = 30
        
        tool_info = f", tools={len(self.tools)}" if self.tools else ""
        logger.info(f"LLM 引擎初始化(简单版): model={self.model}, base_url={self.base_url}{tool_info}")

    def chat(self, user_text: str) -> str:
        """
        非流式对话 - 支持 Function Calling 多轮工具调用
        :param user_text: 用户输入文字
        :return: AI 最终回复文字
        """
        if not user_text.strip():
            return ""

        # 重置中断标志
        self._stop_event.clear()

        # 添加用户消息
        self.messages.append({"role": "user", "content": user_text})

        # 限制历史长度
        if len(self.messages) > self.max_history + 1:  # +1 是 system prompt
            self.messages = [self.messages[0]] + self.messages[-(self.max_history):]

        try:
            # 准备请求数据
            request_data = {
                "model": self.model,
                "messages": self.messages,
                "stream": False
            }
            
            # 添加工具
            if self.tools:
                request_data["tools"] = self.tools
                request_data["tool_choice"] = "auto"
            
            # 添加API密钥到头部
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}" if self.api_key else ""
            }
            
            # 发送请求
            response = self.session.post(
                f"{self.base_url}/v1/chat/completions",
                json=request_data,
                headers=headers
            )
            
            # 检查响应
            if response.status_code != 200:
                logger.error(f"LLM API 响应错误: {response.status_code} - {response.text[:100]}")
                return "抱歉，我暂时无法回答，请稍后再试。"
            
            # 解析响应
            data = response.json()
            
            # 处理响应
            if "choices" not in data or not data["choices"]:
                logger.error(f"LLM API 响应格式错误: {data}")
                return "抱歉，我暂时无法回答，请稍后再试。"
            
            message = data["choices"][0]["message"]
            tool_calls = message.get("tool_calls")
            
            # 如果有工具调用
            if tool_calls and self.tool_executor:
                return self._handle_tool_calls(tool_calls, data.get("id", "unknown"))

            # 普通回复
            reply = message.get("content", "")
            if not reply:
                logger.error(f"LLM 返回空回复: {data}")
                return "抱歉，我暂时无法回答，请稍后再试。"
                
            self.messages.append({"role": "assistant", "content": reply})
            return reply

        except requests.exceptions.Timeout:
            logger.error("LLM 调用超时")
            return "抱歉，请求超时，请稍后再试。"
        except requests.exceptions.ConnectionError:
            logger.error("LLM 连接错误")
            return "抱歉，无法连接到AI服务，请检查网络连接。"
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            # 返回友好的错误消息
            return "抱歉，我暂时无法回答，请稍后再试。"

    def _handle_tool_calls(self, tool_calls, request_id: str) -> str:
        """处理工具调用"""
        for tool_call in tool_calls:
            tool_name = tool_call["function"]["name"]
            tool_args = json.loads(tool_call["function"]["arguments"])

            # 执行工具
            try:
                tool_result = self.tool_executor(tool_name, tool_args)
            except Exception as e:
                tool_result = f"执行工具 {tool_name} 时出错: {str(e)}"

            # 添加工具调用和结果到消息历史
            self.messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": tool_call["id"],
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "arguments": tool_call["function"]["arguments"]
                    }
                }]
            })

            self.messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": tool_result
            })

        # 第二次调用，让模型总结工具结果
        try:
            request_data = {
                "model": self.model,
                "messages": self.messages,
                "stream": False
            }
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}" if self.api_key else ""
            }
            
            response = self.session.post(
                f"{self.base_url}/v1/chat/completions",
                json=request_data,
                headers=headers
            )
            
            if response.status_code != 200:
                logger.error(f"工具调用后总结失败: {response.status_code}")
                return "工具调用成功，但总结结果时出错。"
            
            data = response.json()
            reply = data["choices"][0]["message"].get("content", "")
            self.messages.append({"role": "assistant", "content": reply})
            return reply
        except Exception as e:
            logger.error(f"工具调用后总结失败: {e}")
            return "工具调用成功，但总结结果时出错。"

    def stop(self):
        """停止当前生成"""
        self._stop_event.set()
        logger.info("⏹ LLM 引擎收到停止信号")

    def clear_history(self):
        """清空对话历史"""
        self.messages = [{"role": "system", "content": self.system_prompt}]
        logger.info("🗑️ 对话历史已清空")


def test_simple_engine():
    """测试简单的引擎"""
    print("🧪 测试简单的LLM引擎...")
    
    # 测试连接到本地代理
    engine = LLMEngineSimple(
        api_key="openclaw-proxy",
        base_url="https://localhost:8081",
        model="openclaw-chat"
    )
    
    test_messages = [
        "你好",
        "查看一下Hacker News的最新資訊",
        "现在几点了？",
        "查看GitHub热门项目"
    ]
    
    for msg in test_messages:
        print(f"\n📋 测试: {msg}")
        try:
            reply = engine.chat(msg)
            print(f"   回复: {reply[:100]}...")
            if "抱歉" in reply and "无法回答" in reply:
                print("   ❌ 仍然返回错误消息")
            else:
                print("   ✅ 成功获取回复")
        except Exception as e:
            print(f"   ❌ 错误: {e}")


if __name__ == "__main__":
    test_simple_engine()