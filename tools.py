"""
工具模块 - Function Calling 工具集
提供真实的外部 API 调用能力：Hacker News、GitHub Trending、天气查询等
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional, Callable

import httpx

logger = logging.getLogger(__name__)

# HTTP 客户端（复用连接池）
_client = httpx.Client(timeout=15, follow_redirects=True)


# ============================================================
# 工具实现
# ============================================================

def hacker_news_top(count: int = 5) -> str:
    """获取 Hacker News 热门文章"""
    try:
        count = min(max(count, 1), 15)
        # 1. 获取 Top Story IDs
        resp = _client.get("https://hacker-news.firebaseio.com/v0/topstories.json")
        ids = resp.json()[:count]

        # 2. 批量获取文章详情
        articles = []
        for story_id in ids:
            r = _client.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json")
            item = r.json()
            if item:
                articles.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "score": item.get("score", 0),
                    "comments": item.get("descendants", 0),
                    "by": item.get("by", ""),
                })

        if not articles:
            return "暂时无法获取 Hacker News 数据"

        lines = [f"Hacker News 当前热门 Top {len(articles)}："]
        for i, a in enumerate(articles, 1):
            lines.append(
                f"{i}. {a['title']}（{a['score']}分，{a['comments']}评论）"
            )
        return "\n".join(lines)

    except Exception as e:
        logger.error(f"Hacker News API 失败: {e}")
        return f"获取 Hacker News 失败: {e}"


def github_trending(language: str = "", since: str = "daily", count: int = 5) -> str:
    """获取 GitHub Trending 热门仓库（通过非官方 API）"""
    try:
        count = min(max(count, 1), 15)
        # 使用 GitHub 搜索 API（按 star 数排序，最近创建/更新的项目）
        query_parts = ["stars:>100"]
        if language:
            query_parts.append(f"language:{language}")

        sort = "stars"
        order = "desc"

        # 按 since 参数调整搜索策略
        import datetime
        if since == "daily":
            date_str = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
            query_parts.append(f"created:>{date_str}")
        elif since == "weekly":
            date_str = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
            query_parts.append(f"created:>{date_str}")

        q = " ".join(query_parts)
        resp = _client.get(
            "https://api.github.com/search/repositories",
            params={"q": q, "sort": sort, "order": order, "per_page": count},
            headers={"Accept": "application/vnd.github.v3+json"},
        )
        data = resp.json()
        repos = data.get("items", [])

        if not repos:
            return f"暂时没找到 GitHub 热门项目" + (f"（语言: {language}）" if language else "")

        lines = [f"GitHub 热门项目 Top {len(repos)}："]
        for i, r in enumerate(repos, 1):
            desc = (r.get("description") or "")[:60]
            lines.append(
                f"{i}. {r['full_name']} ⭐{r['stargazers_count']} "
                f"— {desc}"
            )
        return "\n".join(lines)

    except Exception as e:
        logger.error(f"GitHub API 失败: {e}")
        return f"获取 GitHub Trending 失败: {e}"


def get_current_time(timezone: str = "Asia/Shanghai") -> str:
    """获取当前日期和时间"""
    import datetime
    try:
        from zoneinfo import ZoneInfo
        now = datetime.datetime.now(ZoneInfo(timezone))
    except Exception:
        now = datetime.datetime.now()
    return f"当前时间: {now.strftime('%Y年%m月%d日 %H:%M:%S')}（{timezone}）"


def web_search(query: str, count: int = 5) -> str:
    """通过 DuckDuckGo Instant Answer API 进行简单搜索"""
    try:
        resp = _client.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
        )
        data = resp.json()

        results = []
        # Abstract (维基百科等摘要)
        if data.get("AbstractText"):
            results.append(f"摘要: {data['AbstractText'][:200]}")
            if data.get("AbstractURL"):
                results.append(f"来源: {data['AbstractURL']}")

        # Related topics
        for topic in data.get("RelatedTopics", [])[:count]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append(f"- {topic['Text'][:100]}")

        if not results:
            return f"未找到关于「{query}」的搜索结果，建议换个关键词试试"

        return f"搜索「{query}」的结果：\n" + "\n".join(results)

    except Exception as e:
        logger.error(f"搜索 API 失败: {e}")
        return f"搜索失败: {e}"


def url_fetch(url: str) -> str:
    """获取指定 URL 的网页标题和摘要"""
    try:
        resp = _client.get(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; WALLE-Bot/1.0)"
        })
        text = resp.text[:5000]
        # 简单提取 title
        import re
        title_m = re.search(r"<title[^>]*>(.*?)</title>", text, re.IGNORECASE | re.DOTALL)
        title = title_m.group(1).strip() if title_m else "无标题"
        # 去掉 HTML 标签提取纯文本摘要
        clean = re.sub(r"<[^>]+>", " ", text)
        clean = re.sub(r"\s+", " ", clean).strip()[:500]
        return f"标题: {title}\n摘要: {clean}"
    except Exception as e:
        logger.error(f"URL 获取失败: {e}")
        return f"无法访问 {url}: {e}"


# ============================================================
# 工具注册表（Function Calling Schema）
# ============================================================

# 工具名 → 实际函数的映射
TOOL_FUNCTIONS: Dict[str, Callable] = {
    "hacker_news_top": hacker_news_top,
    "github_trending": github_trending,
    "get_current_time": get_current_time,
    "web_search": web_search,
    "url_fetch": url_fetch,
}

# OpenAI Function Calling 格式的工具定义
TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "hacker_news_top",
            "description": "获取 Hacker News 当前热门文章列表，包含标题、得分和评论数",
            "parameters": {
                "type": "object",
                "properties": {
                    "count": {
                        "type": "integer",
                        "description": "返回文章数量，默认5，最多15",
                        "default": 5,
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "github_trending",
            "description": "获取 GitHub 热门/高星项目列表，支持按编程语言筛选",
            "parameters": {
                "type": "object",
                "properties": {
                    "language": {
                        "type": "string",
                        "description": "编程语言过滤，如 python、javascript、rust 等，空字符串表示不限",
                        "default": "",
                    },
                    "since": {
                        "type": "string",
                        "enum": ["daily", "weekly", "monthly"],
                        "description": "时间范围: daily(近一周新项目), weekly(近一月), monthly(不限)",
                        "default": "daily",
                    },
                    "count": {
                        "type": "integer",
                        "description": "返回项目数量，默认5，最多15",
                        "default": 5,
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "获取当前日期和时间",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "时区，如 Asia/Shanghai、America/New_York",
                        "default": "Asia/Shanghai",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "搜索互联网信息，获取某个话题的相关内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词",
                    },
                    "count": {
                        "type": "integer",
                        "description": "返回结果数量，默认5",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "url_fetch",
            "description": "获取指定网页URL的内容摘要",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "要访问的完整网页URL",
                    }
                },
                "required": ["url"],
            },
        },
    },
]


def execute_tool(name: str, arguments: Dict[str, Any]) -> str:
    """执行工具调用并返回结果字符串"""
    func = TOOL_FUNCTIONS.get(name)
    if not func:
        return f"未知工具: {name}"

    start = time.time()
    try:
        result = func(**arguments)
        elapsed = time.time() - start
        logger.info(f"🔧 工具 {name} 执行完成 ({elapsed:.2f}s)")
        return result
    except Exception as e:
        logger.error(f"🔧 工具 {name} 执行失败: {e}")
        return f"工具调用失败: {e}"
