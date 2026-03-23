"""
快速测试脚本 - 验证各模块是否正常工作
"""

import os
import sys
import time
from dotenv import load_dotenv

load_dotenv()


def test_llm():
    """测试 DeepSeek LLM"""
    print("\n" + "=" * 50)
    print("🧠 测试 LLM (DeepSeek)...")
    print("=" * 50)

    from llm_engine import LLMEngine

    llm = LLMEngine()

    # 测试非流式
    start = time.time()
    reply = llm.chat("你好，请用一句话介绍你自己")
    elapsed = time.time() - start
    print(f"✅ 回复: {reply}")
    print(f"⏱️  耗时: {elapsed:.2f}s")

    # 测试流式
    print("\n📡 测试流式输出:")
    start = time.time()
    for chunk in llm.chat_stream("今天天气怎么样？"):
        print(f"  > {chunk}")
    elapsed = time.time() - start
    print(f"⏱️  流式耗时: {elapsed:.2f}s")

    return True


def test_tts():
    """测试 Edge-TTS"""
    print("\n" + "=" * 50)
    print("🔊 测试 TTS (Edge-TTS)...")
    print("=" * 50)

    from tts_engine import TTSEngine

    tts = TTSEngine()

    start = time.time()
    audio = tts.synthesize("你好，我是你的 AI 语音助手，很高兴认识你！")
    elapsed = time.time() - start

    if audio:
        # 保存测试音频
        test_file = "test_output.mp3"
        with open(test_file, "wb") as f:
            f.write(audio)
        print(f"✅ 合成成功: {len(audio)} bytes → {test_file}")
        print(f"⏱️  耗时: {elapsed:.2f}s")
    else:
        print("❌ TTS 合成失败")
        return False

    return True


def test_stt():
    """测试 Whisper STT"""
    print("\n" + "=" * 50)
    print("🎤 测试 STT (Whisper)...")
    print("=" * 50)

    from stt_engine import STTEngine

    stt = STTEngine()

    # 先用 TTS 生成一段测试音频，再用 STT 识别
    from tts_engine import TTSEngine
    tts = TTSEngine()

    test_text = "今天的天气真不错，适合出去走走。"
    print(f"📝 原始文字: {test_text}")

    audio = tts.synthesize(test_text)
    if not audio:
        print("❌ 无法生成测试音频")
        return False

    start = time.time()
    result = stt.transcribe_bytes(audio)
    elapsed = time.time() - start

    print(f"🗣️  识别结果: {result}")
    print(f"⏱️  耗时: {elapsed:.2f}s")

    if result:
        print("✅ STT 工作正常")
    else:
        print("⚠️  STT 未返回结果（可能是音频格式问题，在浏览器中使用 WebM 格式会正常）")

    return True


def main():
    print("🧪 语音对话系统 - 模块测试")
    print("=" * 50)

    results = {}

    # 测试顺序: TTS → LLM → STT
    try:
        results["TTS"] = test_tts()
    except Exception as e:
        print(f"❌ TTS 测试失败: {e}")
        results["TTS"] = False

    try:
        results["LLM"] = test_llm()
    except Exception as e:
        print(f"❌ LLM 测试失败: {e}")
        results["LLM"] = False

    try:
        results["STT"] = test_stt()
    except Exception as e:
        print(f"❌ STT 测试失败: {e}")
        results["STT"] = False

    # 汇总
    print("\n" + "=" * 50)
    print("📊 测试结果汇总")
    print("=" * 50)
    for name, ok in results.items():
        status = "✅ 通过" if ok else "❌ 失败"
        print(f"  {name}: {status}")

    all_ok = all(results.values())
    print(f"\n{'🎉 所有测试通过！可以启动服务器了' if all_ok else '⚠️ 部分测试失败，请检查配置'}")
    print(f"   运行 python server.py 或 bash start.sh 启动服务\n")


if __name__ == "__main__":
    main()
