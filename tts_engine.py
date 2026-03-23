"""
TTS 模块 - 文字转语音
支持: Edge-TTS (微软免费语音，无需GPU，中文效果优秀)
"""

import os
import io
import asyncio
import tempfile
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 推荐的中文语音列表
VOICE_OPTIONS = {
    "xiaoxiao": "zh-CN-XiaoxiaoNeural",     # 女声 - 温柔甜美 (推荐)
    "xiaoyi": "zh-CN-XiaoyiNeural",         # 女声 - 活泼
    "yunjian": "zh-CN-YunjianNeural",        # 男声 - 沉稳
    "yunxi": "zh-CN-YunxiNeural",            # 男声 - 阳光
    "yunxia": "zh-CN-YunxiaNeural",          # 男声 - 少年
    "yunyang": "zh-CN-YunyangNeural",        # 男声 - 新闻播音
    "xiaobei": "zh-CN-XiaobeiNeural",        # 女声 - 活力
    "xiaoni": "zh-CN-XiaoniNeural",          # 女声 - 温暖
}


class TTSEngine:
    """文字转语音引擎 - 基于 Edge-TTS"""

    def __init__(
        self,
        voice: str = "zh-CN-XiaoxiaoNeural",
        rate: str = "+0%",
        volume: str = "+0%",
        pitch: str = "+0Hz",
    ):
        """
        :param voice: 语音名称
        :param rate: 语速调节 (如 "+10%", "-20%")
        :param volume: 音量调节
        :param pitch: 音调调节
        """
        self.voice = voice
        self.rate = rate
        self.volume = volume
        self.pitch = pitch

        # 确保事件循环可用
        self._loop = None
        logger.info(f"TTS 引擎初始化: voice={self.voice}, rate={self.rate}")

    def _get_loop(self):
        """获取或创建事件循环"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            return loop
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    async def _synthesize_async(self, text: str) -> bytes:
        """异步合成语音"""
        import edge_tts

        communicate = edge_tts.Communicate(
            text=text,
            voice=self.voice,
            rate=self.rate,
            volume=self.volume,
            pitch=self.pitch,
        )

        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]

        return audio_data

    def synthesize(self, text: str) -> bytes:
        """
        同步接口 - 将文字合成为 MP3 音频
        :param text: 要合成的文字
        :return: MP3 音频字节流
        """
        if not text.strip():
            return b""

        try:
            # 在新的事件循环中运行
            audio_data = asyncio.run(self._synthesize_async(text))
            logger.info(f"TTS 合成完成: {len(audio_data)} bytes, text={text[:50]}...")
            return audio_data
        except Exception as e:
            logger.error(f"TTS 合成失败: {e}")
            return b""

    async def synthesize_async(self, text: str) -> bytes:
        """
        异步接口 - 将文字合成为 MP3 音频
        :param text: 要合成的文字
        :return: MP3 音频字节流
        """
        if not text.strip():
            return b""

        try:
            audio_data = await self._synthesize_async(text)
            logger.info(f"TTS 异步合成完成: {len(audio_data)} bytes")
            return audio_data
        except Exception as e:
            logger.error(f"TTS 异步合成失败: {e}")
            return b""

    def synthesize_to_file(self, text: str, output_path: str) -> bool:
        """合成并保存到文件"""
        audio_data = self.synthesize(text)
        if audio_data:
            with open(output_path, "wb") as f:
                f.write(audio_data)
            return True
        return False

    def set_voice(self, voice_key: str):
        """切换语音"""
        if voice_key in VOICE_OPTIONS:
            self.voice = VOICE_OPTIONS[voice_key]
            logger.info(f"语音切换为: {voice_key} -> {self.voice}")
        else:
            logger.warning(f"未知的语音名称: {voice_key}")

    @staticmethod
    def list_voices() -> dict:
        """列出所有可用语音"""
        return VOICE_OPTIONS.copy()
