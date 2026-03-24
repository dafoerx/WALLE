"""
Voice Chat Server - 语音对话主服务
管线: 麦克风录音 → STT(Whisper) → LLM(DeepSeek) → TTS(Edge-TTS) → 播放
"""

import os
import sys
import io
import json
import asyncio
import logging
import tempfile
import time
from pathlib import Path

# 确保当前 Python 环境的 bin 目录在 PATH 中（ffmpeg/ffprobe 依赖此路径）
_env_bin = str(Path(sys.executable).resolve().parent)
if _env_bin not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _env_bin + os.pathsep + os.environ.get("PATH", "")

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("VoiceChat")

# 导入引擎
from stt_engine import STTEngine
from llm_engine import LLMEngine
from tts_engine import TTSEngine

# ======== 全局配置 ========
CONFIG = {
    "deepseek_api_key": os.getenv("DEEPSEEK_API_KEY", ""),
    "deepseek_base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    "deepseek_model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
    "whisper_model": os.getenv("WHISPER_MODEL", "base"),
    "whisper_language": os.getenv("WHISPER_LANGUAGE", "zh"),
    "tts_voice": os.getenv("TTS_VOICE", "zh-CN-XiaoxiaoNeural"),
    "server_host": os.getenv("SERVER_HOST", "0.0.0.0"),
    "server_port": int(os.getenv("SERVER_PORT", "8000")),
}

# ======== 初始化引擎 ========
logger.info("=" * 50)
logger.info("🎙️  语音对话系统启动中...")
logger.info("=" * 50)

stt = STTEngine(
    model_size=CONFIG["whisper_model"],
    language=CONFIG["whisper_language"],
)

llm = LLMEngine(
    api_key=CONFIG["deepseek_api_key"],
    base_url=CONFIG["deepseek_base_url"],
    model=CONFIG["deepseek_model"],
)

tts = TTSEngine(
    voice=CONFIG["tts_voice"],
)

# ======== FastAPI 应用 ========
app = FastAPI(title="Voice Chat - DeepSeek 语音对话")

# 静态文件
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    """主页面"""
    html_path = Path(__file__).parent / "static" / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.post("/api/chat")
async def chat_api(audio: UploadFile = File(...), voice_output: str = Form("1")):
    """
    HTTP 接口 - 完整管线
    接收音频 → STT → LLM → (可选)TTS → 返回结果
    :param voice_output: "1" 返回语音+文字, "0" 仅返回文字
    """
    total_start = time.time()
    enable_tts = voice_output == "1"

    # 1. 读取上传的音频
    audio_bytes = await audio.read()
    logger.info(f"📥 收到音频: {len(audio_bytes)} bytes, 语音输出: {'开' if enable_tts else '关'}")

    # 2. STT: 语音 → 文字
    stt_start = time.time()
    user_text = stt.transcribe_bytes(audio_bytes)
    stt_time = time.time() - stt_start

    if not user_text:
        return JSONResponse(content={
            "success": False,
            "error": "未识别到语音内容，请重试",
            "user_text": "",
        })

    logger.info(f"🗣️  用户说: {user_text} (STT耗时: {stt_time:.2f}s)")

    # 3. LLM: 文字 → 回复
    llm_start = time.time()
    reply_text = llm.chat(user_text)
    llm_time = time.time() - llm_start
    logger.info(f"🤖 AI回复: {reply_text} (LLM耗时: {llm_time:.2f}s)")

    # 4. TTS: 回复 → 语音（仅在语音输出开启时执行）
    tts_time = 0
    audio_b64 = None
    if enable_tts:
        tts_start = time.time()
        audio_data = await tts.synthesize_async(reply_text)
        tts_time = time.time() - tts_start

        if audio_data:
            import base64
            audio_b64 = base64.b64encode(audio_data).decode("utf-8")
    else:
        logger.info("⏭️  语音输出已关闭，跳过TTS合成")

    total_time = time.time() - total_start
    logger.info(f"⏱️  总耗时: {total_time:.2f}s (STT:{stt_time:.2f} + LLM:{llm_time:.2f} + TTS:{tts_time:.2f})")

    # 返回结果
    return JSONResponse(content={
        "success": True,
        "user_text": user_text,
        "reply_text": reply_text,
        "audio": audio_b64,
        "voice_output": enable_tts,
        "timing": {
            "stt": round(stt_time, 2),
            "llm": round(llm_time, 2),
            "tts": round(tts_time, 2),
            "total": round(total_time, 2),
        },
    })


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket 接口 - 流式管线
    实时语音对话，更低延迟
    """
    await websocket.accept()
    logger.info("🔌 WebSocket 连接已建立")

    # 为每个连接创建独立的 LLM 引擎（独立对话历史）
    ws_llm = LLMEngine(
        api_key=CONFIG["deepseek_api_key"],
        base_url=CONFIG["deepseek_base_url"],
        model=CONFIG["deepseek_model"],
    )

    try:
        while True:
            # 接收音频数据
            data = await websocket.receive_bytes()
            logger.info(f"📥 WS收到音频: {len(data)} bytes")

            # 1. STT
            user_text = stt.transcribe_bytes(data)
            if not user_text:
                await websocket.send_json({
                    "type": "error",
                    "message": "未识别到语音，请重新说话",
                })
                continue

            # 发送识别结果
            await websocket.send_json({
                "type": "stt_result",
                "text": user_text,
            })

            # 2. LLM 流式生成 + 3. TTS 逐句合成
            full_reply = ""
            for sentence in ws_llm.chat_stream(user_text):
                full_reply += sentence

                # 发送文字
                await websocket.send_json({
                    "type": "llm_chunk",
                    "text": sentence,
                })

                # TTS 合成这一句
                audio_data = await tts.synthesize_async(sentence)
                if audio_data:
                    import base64
                    await websocket.send_json({
                        "type": "tts_audio",
                        "audio": base64.b64encode(audio_data).decode("utf-8"),
                    })

            # 发送完成信号
            await websocket.send_json({
                "type": "done",
                "full_reply": full_reply,
            })

    except WebSocketDisconnect:
        logger.info("🔌 WebSocket 连接断开")
    except Exception as e:
        logger.error(f"WebSocket 错误: {e}")


@app.post("/api/clear")
async def clear_history():
    """清空对话历史"""
    llm.clear_history()
    return JSONResponse(content={"success": True, "message": "对话历史已清空"})


@app.get("/api/voices")
async def list_voices():
    """获取可用语音列表"""
    return JSONResponse(content={"voices": TTSEngine.list_voices()})


@app.post("/api/voice/{voice_key}")
async def change_voice(voice_key: str):
    """切换语音"""
    tts.set_voice(voice_key)
    return JSONResponse(content={"success": True, "voice": voice_key})


# ======== 启动 ========
if __name__ == "__main__":
    import uvicorn

    # 检测 SSL 证书，优先 HTTPS 启动（远程 IP 访问麦克风必须 HTTPS）
    base_dir = Path(__file__).resolve().parent
    cert_file = base_dir / "cert.pem"
    key_file = base_dir / "key.pem"
    use_ssl = cert_file.exists() and key_file.exists()

    protocol = "https" if use_ssl else "http"
    logger.info(f"🌐 服务地址: {protocol}://localhost:{CONFIG['server_port']}")
    logger.info(f"🧠 LLM: DeepSeek ({CONFIG['deepseek_model']})")
    logger.info(f"🎤 STT: Whisper ({CONFIG['whisper_model']})")
    logger.info(f"🔊 TTS: Edge-TTS ({CONFIG['tts_voice']})")
    if use_ssl:
        logger.info(f"🔒 SSL 已启用（自签名证书），远程访问麦克风可用")
    else:
        logger.info(f"⚠️  未检测到 SSL 证书，远程 IP 访问将无法使用麦克风")
        logger.info(f"   生成证书: openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes -subj '/CN=WALLE'")

    ssl_kwargs = {}
    if use_ssl:
        ssl_kwargs["ssl_certfile"] = str(cert_file)
        ssl_kwargs["ssl_keyfile"] = str(key_file)

    uvicorn.run(
        "server:app",
        host=CONFIG["server_host"],
        port=CONFIG["server_port"],
        reload=False,
        log_level="info",
        **ssl_kwargs,
    )
