# WALLE — AI 语音对话系统

## 项目简介

WALLE 是一个端到端的 AI 语音对话系统，实现完整的语音交互管线：

```
麦克风录音 → STT(语音识别) → LLM(智能对话) → TTS(语音合成) → 语音播放
```

### 技术栈

| 模块 | 技术 | 说明 |
|------|------|------|
| STT（语音识别） | faster-whisper | 本地 Whisper 模型，支持 CPU/CUDA |
| LLM（智能对话） | DeepSeek API | 兼容 OpenAI SDK，支持流式/非流式 |
| TTS（语音合成） | Edge-TTS | 微软免费语音合成，8 种中文语音可选 |
| 后端服务 | FastAPI + Uvicorn | HTTP + WebSocket 双协议 |
| 前端界面 | 原生 HTML/CSS/JS | 单文件 SPA，深色主题，无框架依赖 |

### 项目结构

```
WALLE/
├── .env                 # 环境变量配置（API Key、模型参数等）
├── requirements.txt     # Python 依赖清单
├── start.sh             # 一键启动脚本
├── server.py            # 主服务器（FastAPI，路由 + 管线编排）
├── stt_engine.py        # STT 引擎（faster-whisper 语音识别）
├── llm_engine.py        # LLM 引擎（DeepSeek 对话）
├── tts_engine.py        # TTS 引擎（Edge-TTS 语音合成）
├── test_modules.py      # 模块测试脚本
└── static/
    └── index.html       # 前端单页面应用
```

---

## 编译安装

### 前置要求

- Linux 操作系统
- Conda（推荐 Miniconda）
- ffmpeg（音频解码必需）
- DeepSeek API Key

### 第一步：创建 Conda 环境

```bash
# 安装 Miniconda（如未安装）
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh -b -p ~/miniconda3
export PATH="$HOME/miniconda3/bin:$PATH"

# 创建 Python 3.10 虚拟环境
conda create -n voicechat python=3.10 -y
conda activate voicechat
```

### 第二步：安装系统依赖

```bash
# 安装 ffmpeg（音频格式转码必需，用于 WebM/Opus 解码）
conda install -y ffmpeg

# 安装 PyTorch CPU 版（faster-whisper 依赖）
pip install torch --index-url https://download.pytorch.org/whl/cpu

# 如有 NVIDIA GPU，可安装 CUDA 版以加速语音识别
# pip install torch --index-url https://download.pytorch.org/whl/cu118
```

### 第三步：安装 Python 依赖

```bash
cd WALLE/
pip install -r requirements.txt
```

依赖清单（`requirements.txt`）：

| 包名 | 用途 |
|------|------|
| openai>=1.12.0 | DeepSeek API 调用（兼容 OpenAI SDK） |
| faster-whisper>=1.0.0 | 本地 Whisper 语音识别 |
| edge-tts>=6.1.9 | 微软 Edge-TTS 语音合成 |
| fastapi>=0.109.0 | Web 框架 |
| uvicorn[standard]>=0.27.0 | ASGI 服务器 |
| python-multipart>=0.0.6 | 文件上传支持 |
| websockets>=12.0 | WebSocket 支持 |
| numpy>=1.24.0 | 数值计算 |
| soundfile>=0.12.1 | 音频文件读取 |
| pydub>=0.25.1 | 音频格式转码（WebM→WAV） |
| python-dotenv>=1.0.0 | 环境变量加载 |
| aiofiles>=23.2.1 | 异步文件操作 |

### 第四步：配置环境变量

编辑 `.env` 文件：

```bash
# DeepSeek API 配置
DEEPSEEK_API_KEY=sk-your-api-key-here    # ⚠️ 必须替换为你的 API Key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# STT 配置（whisper 模型大小: tiny, base, small, medium, large）
WHISPER_MODEL=base          # base 在 CPU 上推荐，GPU 可用 small/medium
WHISPER_LANGUAGE=zh

# TTS 配置（edge-tts 语音）
TTS_VOICE=zh-CN-XiaoxiaoNeural   # 默认晓晓（温柔女声）

# 服务器配置
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
```

### 第五步：验证安装

```bash
# 运行模块测试，逐一验证 TTS、LLM、STT 是否正常
python test_modules.py
```

---

## 启动与使用

### 一键启动

```bash
cd WALLE/
bash start.sh
```

或手动启动：

```bash
conda activate voicechat
cd WALLE/
python server.py
```

启动成功后输出：

```
==================================================
🎙️  语音对话系统启动中...
==================================================
🌐 服务地址: http://localhost:8000
🧠 LLM: DeepSeek (deepseek-chat)
🎤 STT: Whisper (base)
🔊 TTS: Edge-TTS (zh-CN-XiaoxiaoNeural)
```

### 访问界面

浏览器打开 `http://localhost:8000`，即可看到语音对话界面。

**界面功能：**
- 🎤 点击麦克风按钮或按空格键开始录音，再次点击/松开结束
- 🔊 语音输出开关（右上角 Toggle），开启时回复文字+语音，关闭时仅文字
- 🗣️ 语音选择器，切换 8 种中文语音
- 🗑️ 清空对话历史

---

## API 接口

### HTTP 接口

#### `POST /api/chat` — 语音对话

接收音频，返回识别文本 + AI 回复 + 语音合成结果。

**请求（multipart/form-data）：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| audio | File | 是 | 音频文件（支持 WAV/WebM/OGG/MP3） |
| voice_output | string | 否 | 是否生成语音，`"1"` 开启（默认），`"0"` 关闭 |

**响应（JSON）：**

```json
{
  "user_text": "你好",
  "reply": "你好！有什么我可以帮你的吗？",
  "audio_b64": "base64编码的MP3音频...",
  "stt_time": 0.82,
  "llm_time": 1.23,
  "tts_time": 0.45,
  "total_time": 2.50
}
```

**调用示例：**

```bash
# 发送音频并获取语音回复
curl -X POST http://localhost:8000/api/chat \
  -F "audio=@recording.wav" \
  -F "voice_output=1"

# 仅获取文字回复，不合成语音
curl -X POST http://localhost:8000/api/chat \
  -F "audio=@recording.wav" \
  -F "voice_output=0"
```

```python
import requests
import base64

# Python 调用示例
with open("recording.wav", "rb") as f:
    resp = requests.post(
        "http://localhost:8000/api/chat",
        files={"audio": ("recording.wav", f, "audio/wav")},
        data={"voice_output": "1"}
    )

result = resp.json()
print(f"用户说: {result['user_text']}")
print(f"AI回复: {result['reply']}")

# 保存语音回复
if result["audio_b64"]:
    audio_bytes = base64.b64decode(result["audio_b64"])
    with open("reply.mp3", "wb") as f:
        f.write(audio_bytes)
```

#### `POST /api/clear` — 清空对话历史

```bash
curl -X POST http://localhost:8000/api/clear
```

#### `GET /api/voices` — 获取可用语音列表

```bash
curl http://localhost:8000/api/voices
```

**响应：**

```json
{
  "voices": {
    "xiaoxiao": "晓晓 (温柔女声)",
    "xiaoyi": "晓伊 (活泼女声)",
    "yunjian": "云健 (沉稳男声)",
    "yunxi": "云希 (阳光男声)",
    "yunxia": "云夏 (少年音)",
    "yunyang": "云扬 (新闻播音)",
    "xiaobei": "晓贝 (活力女声)",
    "xiaoni": "晓妮 (温暖女声)"
  },
  "current": "xiaoxiao"
}
```

#### `POST /api/voice/{voice_key}` — 切换语音

```bash
curl -X POST http://localhost:8000/api/voice/yunjian
```

### WebSocket 接口

#### `WS /ws/chat` — 流式语音对话

支持实时流式交互，LLM 逐句生成 + TTS 逐句合成。

**客户端发送：** 二进制音频数据（WebM/WAV）

**服务端推送（JSON 消息流）：**

```json
// 1. 语音识别结果
{"type": "stt_result", "text": "你好", "stt_time": 0.82}

// 2. LLM 逐句回复 + 逐句语音
{"type": "tts_chunk", "text": "你好！", "audio_b64": "..."}
{"type": "tts_chunk", "text": "有什么可以帮你的吗？", "audio_b64": "..."}

// 3. 完成
{"type": "done", "full_reply": "你好！有什么可以帮你的吗？", "llm_time": 1.2, "tts_time": 0.9, "total_time": 2.9}

// 错误
{"type": "error", "message": "错误信息"}
```

**调用示例（Python）：**

```python
import asyncio
import websockets
import json

async def voice_chat():
    async with websockets.connect("ws://localhost:8000/ws/chat") as ws:
        # 发送音频
        with open("recording.webm", "rb") as f:
            await ws.send(f.read())

        # 接收流式结果
        while True:
            msg = json.loads(await ws.recv())
            if msg["type"] == "stt_result":
                print(f"识别: {msg['text']}")
            elif msg["type"] == "tts_chunk":
                print(f"回复: {msg['text']}")
            elif msg["type"] == "done":
                print(f"完成，总耗时: {msg['total_time']:.2f}s")
                break

asyncio.run(voice_chat())
```

---

## 核心模块说明

### STTEngine（stt_engine.py）

语音识别引擎，基于 faster-whisper。

```python
from stt_engine import STTEngine

stt = STTEngine(model_size="base", language="zh")

# 从文件识别
text = stt.transcribe_file("recording.wav")

# 从字节流识别（支持 WAV/WebM/OGG/MP3）
with open("recording.webm", "rb") as f:
    text = stt.transcribe_bytes(f.read())
```

**音频解码策略（三级降级）：**
1. `soundfile` 直接读取 — 支持 WAV/FLAC/OGG
2. `pydub` + ffmpeg 转码 — 支持 WebM/MP3/AAC 等所有格式
3. `ffmpeg` 命令行兜底 — 最终降级方案

### LLMEngine（llm_engine.py）

对话引擎，基于 DeepSeek API（兼容 OpenAI SDK）。

```python
from llm_engine import LLMEngine

llm = LLMEngine(
    api_key="sk-xxx",
    base_url="https://api.deepseek.com",
    model="deepseek-chat"
)

# 非流式对话
reply = llm.chat("你好")

# 流式对话（按句子逐句返回）
for sentence in llm.chat_stream("给我讲个故事"):
    print(sentence, end="", flush=True)

# 清空历史
llm.clear_history()
```

### TTSEngine（tts_engine.py）

语音合成引擎，基于 Edge-TTS。

```python
from tts_engine import TTSEngine

tts = TTSEngine(voice="zh-CN-XiaoxiaoNeural")

# 合成 MP3 字节
mp3_bytes = tts.synthesize("你好，很高兴认识你")

# 合成到文件
tts.synthesize_to_file("你好", "output.mp3")

# 异步合成（FastAPI 中使用）
import asyncio
mp3_bytes = asyncio.run(tts.synthesize_async("你好"))

# 切换语音
tts.set_voice("zh-CN-YunxiNeural")

# 列出可用语音
voices = tts.list_voices()
```

**可用语音：**

| Key | 语音名称 | 完整标识 |
|-----|----------|----------|
| xiaoxiao | 晓晓（温柔女声） | zh-CN-XiaoxiaoNeural |
| xiaoyi | 晓伊（活泼女声） | zh-CN-XiaoYiNeural |
| yunjian | 云健（沉稳男声） | zh-CN-YunJianNeural |
| yunxi | 云希（阳光男声） | zh-CN-YunxiNeural |
| yunxia | 云夏（少年音） | zh-CN-YunxiaNeural |
| yunyang | 云扬（新闻播音） | zh-CN-YunyangNeural |
| xiaobei | 晓贝（活力女声） | zh-CN-XiaoBeiNeural |
| xiaoni | 晓妮（温暖女声） | zh-CN-XiaoNiNeural |

---

## 配置参考

所有配置通过 `.env` 文件管理：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_API_KEY` | — | DeepSeek API 密钥（**必填**） |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | API 地址，可替换为其他兼容 OpenAI 的服务 |
| `DEEPSEEK_MODEL` | `deepseek-chat` | 模型名称 |
| `WHISPER_MODEL` | `base` | Whisper 模型大小：tiny/base/small/medium/large |
| `WHISPER_LANGUAGE` | `zh` | 语音识别语言 |
| `TTS_VOICE` | `zh-CN-XiaoxiaoNeural` | 默认 TTS 语音 |
| `SERVER_HOST` | `0.0.0.0` | 监听地址 |
| `SERVER_PORT` | `8000` | 监听端口 |

**Whisper 模型选择建议：**

| 模型 | 大小 | 速度 | 准确度 | 推荐场景 |
|------|------|------|--------|----------|
| tiny | ~39MB | 最快 | 一般 | 快速测试 |
| base | ~74MB | 快 | 较好 | CPU 日常使用（推荐） |
| small | ~244MB | 中等 | 好 | GPU 环境 |
| medium | ~769MB | 较慢 | 很好 | 高准确度需求 |
| large | ~1.5GB | 慢 | 最好 | 最高质量 |

---

## 常见问题

### Q: 启动报 `ModuleNotFoundError: No module named 'fastapi'`

确认已激活 conda 环境：

```bash
conda activate voicechat
python server.py
```

或直接使用环境中的 Python：

```bash
/path/to/miniconda3/envs/voicechat/bin/python server.py
```

### Q: 录音后提示"未识别到语音内容"

检查 ffmpeg 是否安装：

```bash
ffmpeg -version
```

若未安装：`conda install -y ffmpeg`

### Q: 浏览器打开后语音无法播放

首次打开页面后，**需要点击页面任意位置**触发浏览器的 AudioContext 解锁。系统已内置自动解锁逻辑，正常交互即可自动解锁。

### Q: 如何替换为其他 LLM？

修改 `.env` 中的 API 配置即可，支持所有兼容 OpenAI API 格式的服务：

```bash
DEEPSEEK_API_KEY=your-key
DEEPSEEK_BASE_URL=https://your-api-endpoint
DEEPSEEK_MODEL=your-model-name
```
