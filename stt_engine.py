"""
STT 模块 - 语音转文字
支持: faster-whisper (本地) / OpenAI Whisper API
"""

import os
import io
import tempfile
import logging
import numpy as np
import soundfile as sf
from typing import Optional

logger = logging.getLogger(__name__)


class STTEngine:
    """语音转文字引擎 - 基于 faster-whisper"""

    def __init__(
        self,
        model_size: str = "base",
        language: str = "zh",
        device: str = "auto",
    ):
        self.model_size = model_size
        self.language = language
        self.device = device
        self.model = None

    def _load_model(self):
        """延迟加载模型"""
        if self.model is not None:
            return

        try:
            from faster_whisper import WhisperModel

            # 自动选择设备: 有 CUDA 用 GPU，否则用 CPU
            if self.device == "auto":
                try:
                    import torch
                    has_cuda = torch.cuda.is_available()
                except ImportError:
                    has_cuda = False
                compute_type = "float16" if has_cuda else "int8"
                device = "cuda" if has_cuda else "cpu"
            else:
                device = self.device
                compute_type = "float16" if device == "cuda" else "int8"

            logger.info(f"加载 Whisper 模型: {self.model_size}, 设备: {device}, 精度: {compute_type}")
            self.model = WhisperModel(
                self.model_size,
                device=device,
                compute_type=compute_type,
            )
            logger.info("Whisper 模型加载完成")

        except Exception as e:
            logger.error(f"加载 Whisper 模型失败: {e}")
            raise

    def transcribe_bytes(self, audio_bytes: bytes, sample_rate: int = 16000) -> str:
        """
        从音频字节流转录文字
        :param audio_bytes: 原始音频数据 (WAV/WebM 格式)
        :param sample_rate: 采样率
        :return: 识别的文字
        """
        self._load_model()

        try:
            # 尝试用 soundfile 读取
            audio_data, sr = sf.read(io.BytesIO(audio_bytes))

            # 转为单声道
            if len(audio_data.shape) > 1:
                audio_data = audio_data.mean(axis=1)

            # 转为 float32
            audio_data = audio_data.astype(np.float32)

            # 执行识别
            segments, info = self.model.transcribe(
                audio_data,
                language=self.language,
                beam_size=5,
                vad_filter=True,  # 启用 VAD 过滤静音
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    speech_pad_ms=300,
                ),
            )

            # 拼接结果
            text = "".join([seg.text for seg in segments]).strip()
            logger.info(f"STT 识别结果: {text}")
            return text

        except Exception as e:
            logger.error(f"STT 识别失败: {e}")
            return ""

    def transcribe_file(self, file_path: str) -> str:
        """从文件路径转录"""
        self._load_model()

        try:
            segments, info = self.model.transcribe(
                file_path,
                language=self.language,
                beam_size=5,
                vad_filter=True,
            )
            text = "".join([seg.text for seg in segments]).strip()
            logger.info(f"STT 识别结果: {text}")
            return text

        except Exception as e:
            logger.error(f"STT 文件识别失败: {e}")
            return ""
