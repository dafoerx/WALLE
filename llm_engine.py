"""
LLM 模块 - DeepSeek 对话引擎
兼容 OpenAI SDK，支持流式输出
"""

import os
import logging
from typing import Generator, List, Dict, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

# 默认系统提示词
DEFAULT_SYSTEM_PROMPT = """你是一个友好的 AI 语音助手。请用简洁自然的口语风格回答用户的问题。
注意事项：
1. 回答要简短精炼，适合语音播放，一般不超过3句话
2. 不要使用 markdown 格式、代码块、列表符号等
3. 不要输出表情符号 emoji
4. 用自然的中文口语表达，像朋友聊天一样
5. 如果用户说的内容不清楚，可以礼貌地请他再说一遍"""


class LLMEngine:
    """DeepSeek 对话引擎"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-chat",
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        max_history: int = 20,
    ):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        self.base_url = base_url
        self.model = model
        self.system_prompt = system_prompt
        self.max_history = max_history

        # 对话历史
        self.messages: List[Dict[str, str]] = [
            {"role": "system", "content": self.system_prompt}
        ]

        # 初始化客户端
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )
        logger.info(f"LLM 引擎初始化: model={self.model}, base_url={self.base_url}")

    def chat(self, user_text: str) -> str:
        """
        非流式对话
        :param user_text: 用户输入文字
        :return: AI 回复文字
        """
        if not user_text.strip():
            return ""

        self.messages.append({"role": "user", "content": user_text})
        self._trim_history()

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                temperature=0.7,
                max_tokens=300,  # 语音场景不需要太长
                stream=False,
            )

            reply = response.choices[0].message.content.strip()
            self.messages.append({"role": "assistant", "content": reply})

            logger.info(f"LLM 回复: {reply[:100]}...")
            return reply

        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            return "抱歉，我暂时无法回答，请稍后再试。"

    def chat_stream(self, user_text: str) -> Generator[str, None, None]:
        """
        流式对话 - 逐句返回，适合实时 TTS
        :param user_text: 用户输入文字
        :return: 生成器，逐块返回文字
        """
        if not user_text.strip():
            return

        self.messages.append({"role": "user", "content": user_text})
        self._trim_history()

        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                temperature=0.7,
                max_tokens=300,
                stream=True,
            )

            full_reply = ""
            sentence_buffer = ""
            # 中文句末标点
            sentence_endings = {"。", "！", "？", "；", "，", ".", "!", "?", "\n"}

            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    text = delta.content
                    full_reply += text
                    sentence_buffer += text

                    # 遇到句末标点就 yield 一个完整句子
                    for char in text:
                        if char in sentence_endings and len(sentence_buffer.strip()) > 1:
                            yield sentence_buffer.strip()
                            sentence_buffer = ""
                            break

            # 输出剩余内容
            if sentence_buffer.strip():
                yield sentence_buffer.strip()

            self.messages.append({"role": "assistant", "content": full_reply})
            logger.info(f"LLM 流式回复完成: {full_reply[:100]}...")

        except Exception as e:
            logger.error(f"LLM 流式调用失败: {e}")
            yield "抱歉，我暂时无法回答，请稍后再试。"

    def _trim_history(self):
        """保持对话历史在合理长度"""
        if len(self.messages) > self.max_history + 1:  # +1 for system prompt
            # 保留 system prompt + 最近的 N 条
            self.messages = [self.messages[0]] + self.messages[-(self.max_history):]

    def clear_history(self):
        """清空对话历史"""
        self.messages = [{"role": "system", "content": self.system_prompt}]
        logger.info("对话历史已清空")
