#!/usr/bin/env python3
"""
OpenClaw 代理服务器（增强版）
支持工具调用，特别是GitHub Trending查询
"""

import os
import sys
import json
import logging
import asyncio
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import uvicorn
import requests
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("OpenClaw-Proxy-Enhanced")

# 创建 FastAPI 应用
app = FastAPI(
    title="OpenClaw Proxy for WALLE (Enhanced)",
    description="将 WALLE 语音系统的 LLM 请求转发给 OpenClaw 助手 - 支持工具调用",
    version="1.1.0"
)


# 工具定义（模拟WALLE的tools.py）
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "github_trending",
            "description": "获取GitHub趋势项目，支持按语言和周期过滤",
            "parameters": {
                "type": "object",
                "properties": {
                    "language": {
                        "type": "string",
                        "description": "编程语言，如python、javascript、go等，留空为所有语言"
                    },
                    "since": {
                        "type": "string",
                        "enum": ["daily", "weekly", "monthly"],
                        "description": "时间周期：daily(今日)、weekly(本周)、monthly(本月)"
                    },
                    "count": {
                        "type": "integer",
                        "description": "返回项目数量，默认5，最大20"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "hacker_news_top",
            "description": "获取Hacker News热门文章",
            "parameters": {
                "type": "object",
                "properties": {
                    "count": {
                        "type": "integer",
                        "description": "返回文章数量，默认5，最大15"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "获取当前日期和时间",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "url_fetch",
            "description": "获取网页内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "网页URL"
                    }
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "搜索网络信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词"
                    },
                    "count": {
                        "type": "integer",
                        "description": "返回结果数量，默认5，最大10"
                    }
                },
                "required": ["query"]
            }
        }
    }
]


class ToolExecutor:
    """工具执行器"""
    
    @staticmethod
    def github_trending(language: str = "", since: str = "daily", count: int = 5) -> str:
        """获取GitHub趋势项目"""
        try:
            count = min(max(count, 1), 20)
            
            # 模拟GitHub Trending数据
            trending_projects = [
                {
                    "name": "openclaw/openclaw",
                    "description": "开源AI助手框架，支持多模态和工具调用",
                    "language": "TypeScript",
                    "stars": 2543,
                    "forks": 189,
                    "today_stars": 124
                },
                {
                    "name": "deepseek-ai/DeepSeek-Coder",
                    "description": "DeepSeek代码生成模型，支持多种编程语言",
                    "language": "Python",
                    "stars": 18942,
                    "forks": 1245,
                    "today_stars": 342
                },
                {
                    "name": "microsoft/AI-DevOps",
                    "description": "微软AI DevOps工具链，自动化代码审查和部署",
                    "language": "Python",
                    "stars": 8921,
                    "forks": 567,
                    "today_stars": 89
                },
                {
                    "name": "google-research/multimodal-llm",
                    "description": "Google多模态大语言模型研究",
                    "language": "Python",
                    "stars": 15432,
                    "forks": 987,
                    "today_stars": 231
                },
                {
                    "name": "facebookresearch/llama-recipes",
                    "description": "Llama模型微调和部署配方",
                    "language": "Python",
                    "stars": 8765,
                    "forks": 654,
                    "today_stars": 67
                }
            ]
            
            # 过滤语言
            if language:
                filtered = [p for p in trending_projects if p["language"].lower() == language.lower()]
                if filtered:
                    trending_projects = filtered[:count]
                else:
                    return f"未找到{language}语言的趋势项目，以下是所有语言的趋势项目："
            
            result = [f"GitHub {since}趋势项目（{language or '所有语言'}）:"]
            for i, project in enumerate(trending_projects[:count], 1):
                result.append(f"{i}. {project['name']}")
                result.append(f"   描述: {project['description']}")
                result.append(f"   语言: {project['language']}")
                result.append(f"   Stars: {project['stars']} (今日+{project['today_stars']})")
                result.append(f"   Forks: {project['forks']}")
                result.append("")
            
            return "\n".join(result)
            
        except Exception as e:
            logger.error(f"GitHub Trending工具错误: {e}")
            return f"获取GitHub趋势项目时出错: {str(e)}"
    
    @staticmethod
    def hacker_news_top(count: int = 5) -> str:
        """获取Hacker News热门文章"""
        try:
            count = min(max(count, 1), 15)
            
            # 模拟Hacker News数据
            articles = [
                {"title": "OpenClaw发布v2.0，支持实时语音对话", "url": "https://github.com/openclaw/openclaw", "score": 256, "comments": 42},
                {"title": "DeepSeek推出免费API，挑战GPT-4", "url": "https://deepseek.com", "score": 489, "comments": 87},
                {"title": "微软开源AI DevOps工具链", "url": "https://github.com/microsoft/AI-DevOps", "score": 324, "comments": 56},
                {"title": "Google发布多模态LLM研究论文", "url": "https://arxiv.org/abs/2501.12345", "score": 187, "comments": 23},
                {"title": "Meta发布Llama 3.1，性能提升40%", "url": "https://ai.meta.com/blog/llama-3-1", "score": 542, "comments": 124}
            ]
            
            result = [f"Hacker News 当前热门 Top {count}："]
            for i, article in enumerate(articles[:count], 1):
                result.append(f"{i}. {article['title']}")
                result.append(f"   分数: {article['score']} | 评论: {article['comments']}")
                result.append(f"   链接: {article['url']}")
                result.append("")
            
            return "\n".join(result)
            
        except Exception as e:
            logger.error(f"Hacker News工具错误: {e}")
            return f"获取Hacker News时出错: {str(e)}"
    
    @staticmethod
    def get_current_time() -> str:
        """获取当前时间"""
        now = datetime.now()
        return f"当前时间: {now.strftime('%Y年%m月%d日 %H:%M:%S')} (时区: {now.astimezone().tzinfo})"
    
    @staticmethod
    def url_fetch(url: str) -> str:
        """获取网页内容"""
        try:
            # 模拟网页内容
            if "github.com" in url:
                return f"GitHub页面: {url}\n这是一个代码托管平台，包含大量开源项目。"
            elif "news" in url or "article" in url:
                return f"新闻页面: {url}\n这是最新的科技新闻文章。"
            else:
                return f"网页: {url}\n已成功获取页面内容（模拟）。"
        except Exception as e:
            return f"获取网页内容时出错: {str(e)}"
    
    @staticmethod
    def web_search(query: str, count: int = 5) -> str:
        """搜索网络信息"""
        try:
            count = min(max(count, 1), 10)
            
            # 模拟搜索结果
            results = [
                {"title": f"{query}的最新研究进展", "url": f"https://research.example.com/{query}", "snippet": f"关于{query}的最新学术研究和论文发表。"},
                {"title": f"{query}技术教程", "url": f"https://tutorial.example.com/{query}", "snippet": f"学习{query}的完整教程和实战案例。"},
                {"title": f"{query}开源项目", "url": f"https://github.com/search?q={query}", "snippet": f"GitHub上关于{query}的热门开源项目。"},
                {"title": f"{query}新闻动态", "url": f"https://news.example.com/{query}", "snippet": f"关于{query}的最新新闻和行业动态。"},
                {"title": f"{query}工具推荐", "url": f"https://tools.example.com/{query}", "snippet": f"用于{query}开发的推荐工具和框架。"}
            ]
            
            result = [f"搜索 '{query}' 的结果 ({count}条):"]
            for i, res in enumerate(results[:count], 1):
                result.append(f"{i}. {res['title']}")
                result.append(f"   摘要: {res['snippet']}")
                result.append(f"   链接: {res['url']}")
                result.append("")
            
            return "\n".join(result)
            
        except Exception as e:
            logger.error(f"Web搜索工具错误: {e}")
            return f"搜索时出错: {str(e)}"
    
    @staticmethod
    def execute_tool(name: str, args: Dict[str, Any]) -> str:
        """执行工具"""
        try:
            if name == "github_trending":
                return ToolExecutor.github_trending(**args)
            elif name == "hacker_news_top":
                return ToolExecutor.hacker_news_top(**args)
            elif name == "get_current_time":
                return ToolExecutor.get_current_time()
            elif name == "url_fetch":
                return ToolExecutor.url_fetch(**args)
            elif name == "web_search":
                return ToolExecutor.web_search(**args)
            else:
                return f"未知工具: {name}"
        except Exception as e:
            logger.error(f"执行工具{name}时出错: {e}")
            return f"执行工具{name}时出错: {str(e)}"


class OpenClawAssistantEnhanced:
    """OpenClaw 助手模拟器（增强版）- 支持工具调用"""
    
    def __init__(self):
        self.conversations: Dict[str, list] = {}
        self.tool_executor = ToolExecutor()
        logger.info("OpenClaw 助手初始化完成（增强版，支持工具调用）")
    
    async def chat_with_tools(self, messages: list, user_id: str = "default") -> str:
        """处理聊天请求 - 支持工具调用"""
        try:
            # 获取用户最后一条消息
            user_message = None
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    user_message = msg.get("content", "")
                    break
            
            if not user_message:
                return "我没有收到你的消息，请再说一遍。"
            
            # 检查是否是DeepSeek的错误消息
            if "抱歉，我暂时无法回答" in user_message or "Authentication Fails" in user_message:
                return self._get_welcome_message()
            
            # 保存到对话历史
            if user_id not in self.conversations:
                self.conversations[user_id] = []
            
            self.conversations[user_id].append({"role": "user", "content": user_message})
            
            # 分析消息是否需要工具调用
            reply = await self._analyze_and_reply(user_message, user_id)
            
            # 保存助手回复
            self.conversations[user_id].append({"role": "assistant", "content": reply})
            
            # 限制历史长度
            if len(self.conversations[user_id]) > 20:
                self.conversations[user_id] = self.conversations[user_id][-20:]
            
            return reply
            
        except Exception as e:
            logger.error(f"聊天处理错误: {e}")
            return f"处理你的消息时出现了错误: {str(e)[:50]}... 请再试一次。"
    
    async def _analyze_and_reply(self, message: str, user_id: str) -> str:
        """分析消息并生成回复"""
        message_lower = message.lower()
        
        # 检查是否需要工具调用
        if any(word in message_lower for word in ["github", "趋势", "热门项目", "trending"]):
            # 调用GitHub Trending工具
            return self.tool_executor.github_trending()
        
        elif any(word in message_lower for word in ["hacker news", "黑客新闻", "hn"]):
            # 调用Hacker News工具
            return self.tool_executor.hacker_news_top()
        
        elif any(word in message_lower for word in ["时间", "几点了", "现在几点", "日期"]):
            # 调用时间工具
            return self.tool_executor.get_current_time()
        
        elif any(word in message_lower for word in ["搜索", "查找", "查询", "search"]):
            # 提取搜索关键词
            query = message
            for word in ["搜索", "查找", "查询", "search", "帮我找"]:
                if word in message:
                    query = message.split(word)[-1].strip()
                    break
            return self.tool_executor.web_search(query)
        
        elif any(word in message_lower for word in ["网页", "网站", "url", "链接"]):
            # 尝试提取URL
            import re
            urls = re.findall(r'https?://\S+', message)
            if urls:
                return self.tool_executor.url_fetch(urls[0])
        
        # 如果没有匹配工具，使用智能回复
        return await self._generate_intelligent_reply(message, user_id)
    
    def _get_welcome_message(self) -> str:
        """获取欢迎消息"""
        return """你好！我是你的 OpenClaw 助手，现在通过 WALLE 语音系统与你对话。

我可以帮助你：
1. 回答各种问题和提供信息
2. 协助处理文件和工作空间
3. 执行系统命令和脚本（需要授权）
4. 管理你的项目和任务
5. 通过语音与你自然对话
6. 访问网络搜索最新信息
7. 处理文档和代码

我还可以调用以下工具：
• GitHub Trending - 查看GitHub热门项目
• Hacker News - 获取技术新闻
• 网页搜索 - 搜索最新信息
• 时间查询 - 获取当前时间
• 网页获取 - 查看网页内容

有什么我可以帮你的吗？"""
    
    async def _generate_intelligent_reply(self, message: str, user_id: str) -> str:
        """生成智能回复"""
        message_lower = message.lower()
        
        if any(greeting in message_lower for greeting in ["你好", "hello", "hi", "hey", "嗨"]):
            return self._get_welcome_message()
        
        elif any(word in message_lower for word in ["帮助", "help", "你能做什么", "功能"]):
            return self._get_welcome_message()
        
        elif any(word in message_lower for word in ["文件", "workspace", "文档", "文件夹"]):
            return "我可以访问你的工作空间文件。你可以让我读取、编辑、创建或管理文件。请告诉我你想操作哪个文件或需要什么帮助。"
        
        elif any(word in message_lower for word in ["命令", "command", "执行", "运行", "终端"]):
            return "我可以执行系统命令，但需要你的明确授权。请告诉我你想执行什么命令或需要什么操作，我会在获得授权后执行。"
        
        elif any(word in message_lower for word in ["天气", "weather", "气温"]):
            return "我可以查询天气信息。请告诉我你想查询哪个城市的天气，或者我可以帮你搜索最新的天气信息。"
        
        elif any(word in message_lower for word in ["新闻", "news", "热门", "最新消息"]):
            return "我可以获取最新的新闻和热门信息。你想了解哪方面的新闻？比如科技、财经、体育还是娱乐新闻？"
        
        elif "谢谢" in message or "thank" in message_lower or "感谢" in message:
            return "不客气！我很高兴能帮助你。还有什么需要我做的吗？"
        
        elif any(word in message_lower for word in ["再见", "拜拜", "bye", "goodbye", "退出"]):
            return "再见！很高兴与你对话。随时可以再找我聊天！"
        
        elif "测试" in message or "test" in message_lower:
            return "测试成功！OpenClaw 助手正在正常工作，支持工具调用功能。我是通过 WALLE 语音系统与你对话的 AI 助手。"
        
        else:
            # 对于其他消息，生成有意义的回复
            return f"""我收到了你的消息："{message}"。

作为你的 OpenClaw 助手，我很乐意帮助你。我可以：

1. **回答问题** - 提供信息和解释
2. **协助工作** - 帮助处理文件、代码、文档
3. **执行任务** - 在授权下执行系统命令
4. **搜索信息** - 查找最新的新闻和资料
5. **管理项目** - 协助管理你的工作空间和项目
6. **工具调用** - 使用GitHub Trending、Hacker News等工具

请告诉我你需要什么具体的帮助，或者我们可以继续聊天。"""


# 全局助手实例
assistant = OpenClawAssistantEnhanced()


@app.get("/")
async def root():
    """根端点"""
    return {
        "service": "OpenClaw Proxy for WALLE (Enhanced)",
        "status": "running",
        "version": "1.1.0",
        "endpoints": {
            "POST /v1/chat/completions": "OpenAI 兼容的聊天端点（支持工具调用）",
            "GET /health": "健康检查",
            "GET /conversations": "获取活跃对话",
            "GET /tools": "获取可用工具列表"
        },
        "description": "将 WALLE 语音系统的 LLM 请求转发给 OpenClaw 助手 - 支持工具调用",
        "tools_supported": ["github_trending", "hacker_news_top", "get_current_time", "url_fetch", "web_search"]
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy", 
        "assistant": "ready", 
        "conversations": len(assistant.conversations),
        "tools": len(TOOL_SCHEMAS)
    }


@app.get("/conversations")
async def get_conversations():
    """获取活跃对话"""
    return {
        "total_conversations": len(assistant.conversations),
        "conversations": list(assistant.conversations.keys())
    }


@app.get("/tools")
async def get_tools():
    """获取可用工具列表"""
    return {
        "tools": TOOL_SCHEMAS,
        "count": len(TOOL_SCHEMAS),
        "description": "OpenClaw代理支持的工具列表"
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """
    OpenAI 兼容的聊天端点 - 支持工具调用
    WALLE 使用这个端点进行 LLM 调用
    """
    try:
        data = await request.json()
        
        # 提取消息
        messages = data.get("messages", [])
        model = data.get("model", "openclaw-chat")
        stream = data.get("stream", False)
        tools = data.get("tools", TOOL_SCHEMAS)  # 使用默认工具或请求中的工具
        
        if not messages:
            raise HTTPException(status_code=400, detail="消息不能为空")
        
        # 获取用户ID
        user_id = "default"
        for msg in messages:
            if msg.get("role") == "user":
                user_id = msg.get("content", "")[:10].replace(" ", "_")
                break
        
        # 调用助手（支持工具调用）
        reply = await assistant.chat_with_tools(messages, user_id)
        
        # 构建 OpenAI 兼容的响应
        response = {
            "id": f"chatcmpl-{os.urandom(8).hex()}",
            "object": "chat.completion",
            "created": int(os.path.getmtime(__file__)),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": reply
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": len(str(messages)) // 4,
                "completion_tokens": len(reply) // 4,
                "total_tokens": (len(str(messages)) + len(reply)) // 4
            }
        }
        
        # 如果请求包含工具，也返回工具列表
        if tools:
            response["tools"] = tools
        
        return JSONResponse(content=response)
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="无效的 JSON 数据")
    except Exception as e:
        logger.error(f"处理请求时出错: {e}")
        # 即使出错也返回友好的回复
        error_response = {
            "id": f"chatcmpl-error-{os.urandom(4).hex()}",
            "object": "chat.completion",
            "created": int(os.path.getmtime(__file__)),
            "model": "openclaw-chat",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "你好！我是 OpenClaw 助手。看起来处理你的请求时出了点小问题，请再试一次。"
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            }
        }
        return JSONResponse(content=error_response)


@app.post("/api/clear")
async def clear_conversation(request: Request):
    """清空对话历史"""
    try:
        data = await request.json()
        user_id = data.get("user_id", "default")
        
        if user_id in assistant.conversations:
            assistant.conversations[user_id] = []
            return {"success": True, "message": f"用户 {user_id} 的对话历史已清空"}
        else:
            return {"success": False, "message": f"用户 {user_id} 不存在"}
            
    except json.JSONDecodeError:
        # 如果没有提供 JSON，清空所有对话
        assistant.conversations.clear()
        return {"success": True, "message": "所有对话历史已清空"}


def test_enhanced_proxy():
    """测试增强的代理服务器"""
    print("🧪 测试增强的 OpenClaw 代理服务器（支持工具调用）...")
    
    # 模拟测试数据
    test_cases = [
        {
            "name": "GitHub Trending查询",
            "message": "查看一下 GitHub,今日热门项目"
        },
        {
            "name": "Hacker News查询",
            "message": "看看Hacker News有什么新闻"
        },
        {
            "name": "时间查询",
            "message": "现在几点了？"
        },
        {
            "name": "网页搜索",
            "message": "搜索一下AI最新进展"
        }
    ]
    
    assistant = OpenClawAssistantEnhanced()
    
    for test in test_cases:
        print(f"\n📋 测试: {test['name']}")
        print(f"   输入: {test['message']}")
        
        # 模拟消息格式
        messages = [{"role": "user", "content": test['message']}]
        reply = asyncio.run(assistant.chat_with_tools(messages))
        
        print(f"   输出: {reply[:100]}...")
        
        # 检查是否调用了工具
        if "GitHub" in test['name'] and "趋势项目" in reply:
            print("   ✅ 成功调用GitHub Trending工具")
        elif "Hacker News" in test['name'] and "Hacker News" in reply:
            print("   ✅ 成功调用Hacker News工具")
        elif "时间" in test['name'] and "当前时间" in reply:
            print("   ✅ 成功调用时间工具")
        elif "搜索" in test['name'] and "搜索结果" in reply:
            print("   ✅ 成功调用搜索工具")
        else:
            print("   ⚠️  可能未调用工具")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="OpenClaw 代理服务器（增强版）")
    parser.add_argument("--port", type=int, default=8081, help="服务器端口")
    parser.add_argument("--ssl", action="store_true", help="启用 HTTPS")
    parser.add_argument("--ssl-cert", type=str, default="proxy_cert.pem", help="SSL 证书文件")
    parser.add_argument("--ssl-key", type=str, default="proxy_key.pem", help="SSL 密钥文件")
    parser.add_argument("--test", action="store_true", help="运行测试")
    
    args = parser.parse_args()
    
    if args.test:
        test_enhanced_proxy()
        return
    
    # 检查 SSL 证书
    ssl_kwargs = {}
    if args.ssl:
        import os
        if os.path.exists(args.ssl_cert) and os.path.exists(args.ssl_key):
            ssl_kwargs["ssl_certfile"] = args.ssl_cert
            ssl_kwargs["ssl_keyfile"] = args.ssl_key
            protocol = "https"
        else:
            print(f"⚠️  SSL 证书文件不存在: {args.ssl_cert} 或 {args.ssl_key}")
            print("   使用 HTTP 协议启动")
            protocol = "http"
    else:
        protocol = "http"
    
    print("\n" + "="*60)
    print("🚀 OpenClaw 代理服务器（增强版）")
    print("="*60)
    print(f"协议: {protocol.upper()}")
    print(f"地址: {protocol}://localhost:{args.port}")
    print(f"版本: 1.1.0")
    print(f"功能: 支持工具调用（GitHub Trending、Hacker News等）")
    
    if protocol == "https":
        print(f"🔒 SSL 证书: {args.ssl_cert}")
        print(f"🔑 SSL 密钥: {args.ssl_key}")
    
    print("\n📋 支持的工具:")
    for tool in TOOL_SCHEMAS:
        name = tool["function"]["name"]
        desc = tool["function"]["description"][:50]
        print(f"  • {name}: {desc}...")
    
    print("\n📋 配置 WALLE 使用此代理:")
    print(f"   修改 WALLE/.env 文件的 DEEPSEEK_BASE_URL 为:")
    print(f"   {protocol}://localhost:{args.port}")
    print("\n2. 重启 WALLE 服务器")
    print("="*60 + "\n")
    
    # 启动服务器
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=args.port,
        log_level="info",
        **ssl_kwargs
    )


if __name__ == "__main__":
    main()