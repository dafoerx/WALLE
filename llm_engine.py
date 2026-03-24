"""
LLM 模块 - DeepSeek 对话引擎
兼容 OpenAI SDK，支持 Function Calling 工具调用
"""

import os
import json
import logging
import threading
from typing import Generator, List, Dict, Optional, Any
from openai import OpenAI

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


class LLMEngine:
    """DeepSeek 对话引擎 - 支持 Function Calling"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-chat",
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        max_history: int = 20,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_executor=None,
    ):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        self.base_url = base_url
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

        # 初始化客户端
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )
        tool_info = f", tools={len(self.tools)}" if self.tools else ""
        logger.info(f"LLM 引擎初始化: model={self.model}, base_url={self.base_url}{tool_info}")

    def chat(self, user_text: str) -> str:
        """
        非流式对话 - 支持 Function Calling 多轮工具调用
        :param user_text: 用户输入文字
        :return: AI 最终回复文字
        """
        if not user_text.strip():
            return ""

        self._stop_event.clear()
        self.messages.append({"role": "user", "content": user_text})
        self._trim_history()

        try:
            # 工具调用循环（最多 5 轮，防止无限循环）
            max_rounds = 5
            for round_i in range(max_rounds):
                # 检查是否被中断
                if self._stop_event.is_set():
                    logger.info("⏹ LLM 生成被用户中断")
                    reply = "（已停止回复）"
                    self.messages.append({"role": "assistant", "content": reply})
                    return reply
                # 构建请求参数
                kwargs = {
                    "model": self.model,
                    "messages": self.messages,
                    "temperature": 0.7,
                    "max_tokens": 800,  # 工具调用场景需要更多 token
                    "stream": False,
                }
                if self.tools:
                    kwargs["tools"] = self.tools

                response = self.client.chat.completions.create(**kwargs)
                msg = response.choices[0].message

                # 情况 1: 模型要求调用工具
                if msg.tool_calls and self.tool_executor:
                    # 将 assistant 消息（含 tool_calls）加入历史
                    self.messages.append({
                        "role": "assistant",
                        "content": msg.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                },
                            }
                            for tc in msg.tool_calls
                        ],
                    })

                    # 执行每个工具调用
                    for tc in msg.tool_calls:
                        func_name = tc.function.name
                        try:
                            func_args = json.loads(tc.function.arguments)
                        except json.JSONDecodeError:
                            func_args = {}

                        logger.info(f"🔧 调用工具: {func_name}({func_args})")
                        tool_result = self.tool_executor(func_name, func_args)
                        logger.info(f"🔧 工具结果: {tool_result[:200]}...")

                        # 将工具结果加入历史
                        self.messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": tool_result,
                        })

                    # 继续下一轮，让模型根据工具结果生成回复
                    continue

                # 情况 2: 模型直接回复（无工具调用）
                reply = (msg.content or "").strip()
                self.messages.append({"role": "assistant", "content": reply})
                logger.info(f"LLM 回复: {reply[:100]}...")
                return reply

            # 超过最大轮数
            reply = "抱歉，处理这个问题花了太长时间，请你换个方式问一下。"
            self.messages.append({"role": "assistant", "content": reply})
            return reply

        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            return "抱歉，我暂时无法回答，请稍后再试。"

    def chat_stream(self, user_text: str) -> Generator[str, None, None]:
        """
        流式对话 - 逐句返回，适合实时 TTS
        注意: 流式模式下如果触发工具调用，会先同步执行工具，再流式输出最终回复
        :param user_text: 用户输入文字
        :return: 生成器，逐块返回文字
        """
        if not user_text.strip():
            return

        self.messages.append({"role": "user", "content": user_text})
        self._trim_history()

        try:
            # 第一步：非流式调用看是否需要工具
            max_rounds = 5
            for round_i in range(max_rounds):
                kwargs = {
                    "model": self.model,
                    "messages": self.messages,
                    "temperature": 0.7,
                    "max_tokens": 800,
                    "stream": False,
                }
                if self.tools:
                    kwargs["tools"] = self.tools

                response = self.client.chat.completions.create(**kwargs)
                msg = response.choices[0].message

                if msg.tool_calls and self.tool_executor:
                    self.messages.append({
                        "role": "assistant",
                        "content": msg.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                },
                            }
                            for tc in msg.tool_calls
                        ],
                    })

                    for tc in msg.tool_calls:
                        func_name = tc.function.name
                        try:
                            func_args = json.loads(tc.function.arguments)
                        except json.JSONDecodeError:
                            func_args = {}

                        logger.info(f"🔧 [stream] 调用工具: {func_name}({func_args})")
                        tool_result = self.tool_executor(func_name, func_args)

                        self.messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": tool_result,
                        })
                    continue

                # 没有工具调用，直接把内容作为最终回复
                reply = (msg.content or "").strip()
                self.messages.append({"role": "assistant", "content": reply})
                logger.info(f"LLM 流式回复完成: {reply[:100]}...")

                # 模拟流式：按句子切分 yield
                sentence_buffer = ""
                sentence_endings = {"。", "！", "？", "；", ".", "!", "?", "\n"}
                for ch in reply:
                    sentence_buffer += ch
                    if ch in sentence_endings and len(sentence_buffer.strip()) > 1:
                        yield sentence_buffer.strip()
                        sentence_buffer = ""
                if sentence_buffer.strip():
                    yield sentence_buffer.strip()
                return

            yield "抱歉，处理这个问题花了太长时间，请换个方式问一下。"

        except Exception as e:
            logger.error(f"LLM 流式调用失败: {e}")
            yield "抱歉，我暂时无法回答，请稍后再试。"

    def _trim_history(self):
        """保持对话历史在合理长度（跳过 tool 相关消息避免截断不完整）"""
        if len(self.messages) > self.max_history + 1:
            # 保留 system prompt + 最近的 N 条
            self.messages = [self.messages[0]] + self.messages[-(self.max_history):]

    def clear_history(self):
        """清空对话历史"""
        self.messages = [{"role": "system", "content": self.system_prompt}]
        logger.info("对话历史已清空")

    def stop(self):
        """中断当前正在进行的生成"""
        self._stop_event.set()
        logger.info("⏹ 收到停止请求")
