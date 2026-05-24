"""radar_agent.py — AI 技术情报雷达 (Kilo Code 方式: 直连 API/URL 获取)"""
import asyncio, os, json, re, html as html_mod
from datetime import datetime
from pathlib import Path

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph, MessagesState
import httpx
from dotenv import load_dotenv

# ═══════════════════════════════════════════════════════════════════════════
#  V4 Fix — monkey-patch ChatDeepSeek BEFORE any init_chat_model call
# ═══════════════════════════════════════════════════════════════════════════
import re
from langchain_deepseek.chat_models import ChatDeepSeek

_V4_PATTERN = re.compile(r"(?:^|[-:])v?4[-_]", re.IGNORECASE)
_orig_payload = ChatDeepSeek._get_request_payload
_orig_bind = ChatDeepSeek.bind_tools

def _patched_payload(self, input_, *, stop=None, **kwargs):
    p = _orig_payload(self, input_, stop=stop, **kwargs)
    if _V4_PATTERN.search(self.model_name or ""):
        p.setdefault("extra_body", {})
        p["extra_body"]["thinking"] = {"type": "disabled"}
    return p

def _patched_bind(self, tools, *, tool_choice=None, **kwargs):
    if _V4_PATTERN.search(self.model_name or "") and tool_choice in (None, False):
        tool_choice = "any"
    return _orig_bind(self, tools, tool_choice=tool_choice, **kwargs)

ChatDeepSeek._get_request_payload = _patched_payload
ChatDeepSeek.bind_tools = _patched_bind
# ═══════════════════════════════════════════════════════════════════════════

# ── State ──────────────────────────────────────────────────────────────────
class AgentInputState(MessagesState):
    pass

class AgentState(MessagesState):
    sources_raw: str = ""
    final_report: str = ""

# ── 直连 API/URL（Kilo Code 方式） ────────────────────────────────────────
_API_URLS = {
    "OPENROUTER_MODELS": "https://openrouter.ai/api/v1/models",
    "GITHUB_TRENDING":   "https://api.github.com/search/repositories?q=AI+agent+2026&sort=stars&per_page=10",
    "ARXIV":             "https://arxiv.org/list/cs.AI/recent",
}

_PROMPTS_DIR = Path(__file__).parent / "prompts"
_REPORT_PROMPT = (_PROMPTS_DIR / "report_prompt.txt").read_text(encoding="utf-8")


def _strip_html(html: str) -> str:
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
    html = re.sub(r'<br\s*/?>', '\n', html)
    html = re.sub(r'</(p|div|li|tr|h[1-6])>', '\n', html)
    html = re.sub(r'<[^>]+>', '', html)
    html = html_mod.unescape(html)
    html = re.sub(r'\n{3,}', '\n\n', html)
    html = re.sub(r'[ \t]+', ' ', html)
    return html.strip()[:6000]


async def search_all(state: AgentState, config: RunnableConfig) -> dict:
    """直连各目标 API/URL（Kilo Code 方式：webfetch + 结构化数据）。"""
    parts = []
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        for label, url in _API_URLS.items():
            try:
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code != 200:
                    parts.append("=== %s ===\nHTTP %d" % (label, resp.status_code))
                    continue
                text = ""
                if "api.github" in url:
                    data = resp.json()
                    for item in data.get("items", [])[:10]:
                        text += "- %s\n  Stars: %d  Lang: %s\n  %s\n  URL: https://github.com/%s\n" % (
                            item["full_name"], item["stargazers_count"],
                            item.get("language", "") or "N/A", (item.get("description", "") or "")[:200],
                            item["full_name"])
                elif "openrouter.ai/api" in url:
                    data = resp.json().get("data", [])
                    for m in data[:30]:
                        p = m.get("pricing", {})
                        text += "- %s\n  Context: %s  Pricing: $%s/$%s per token\n  %s\n" % (
                            m["name"], m.get("context_length", "?"),
                            p.get("prompt", "?"), p.get("completion", "?"),
                            m.get("description", "")[:250])
                else:
                    text = _strip_html(resp.text)
                parts.append("=== %s [%s] ===\n%s" % (label, url, text))
            except Exception as e:
                parts.append("=== %s ERROR: %s ===" % (label, e))
    return {"sources_raw": "\n\n".join(parts), "messages": []}


async def final_report(state: AgentState, config: RunnableConfig) -> dict:
    """V4-pro 生成编号引用报告。"""
    model = init_chat_model("deepseek:deepseek-v4-pro", max_tokens=5000,
                            api_key=os.environ.get("DEEPSEEK_API_KEY", ""))
    sources = state.get("sources_raw", "")
    today = datetime.now()
    week = today.strftime("%Y-W%W")
    prompt = _REPORT_PROMPT.format(date=today.strftime("%Y-%m-%d"), week=week)
    user_msg = state.get("messages", [None])[0]
    brief = (user_msg.content or "")[:500] if user_msg else ""

    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content="<Sources>\n%s\n</Sources>\n\n%s" % (sources, brief)),
    ]
    r = await asyncio.wait_for(model.ainvoke(messages), timeout=120.0)
    return {"final_report": r.content or "", "messages": [r]}


# ── Graph ──────────────────────────────────────────────────────────────────
builder = StateGraph(AgentState, input_schema=AgentInputState)
builder.add_node("search_all",   search_all)
builder.add_node("final_report", final_report)
builder.add_edge(START, "search_all")
builder.add_edge("search_all", "final_report")
builder.add_edge("final_report", END)
radar_agent = builder.compile()


# ── CLI Entry ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Try multiple locations for .env
    for env_path in [Path(__file__).parent.parent.parent / ".env",
                      Path(__file__).parent.parent / ".env",
                      Path(__file__).parent / ".env"]:
        if env_path.exists():
            load_dotenv(env_path, override=True)
            break

    query = ("2026 年 AI 技术情报周报：OpenRouter 模型排行、GitHub 趋势 AI 项目、"
             "arXiv 最新论文、HuggingFace 新模型。只写搜索结果中真实存在的数据。")

    async def _main():
        result = await radar_agent.ainvoke(
            {"messages": [HumanMessage(content=query)]},
        )
        report = result.get("final_report", "(empty)")
        out = Path(__file__).parent / "report_demo.md"
        out.write_text(report, encoding="utf-8")
        print("Written:", out)
        print(report[:200], "...")

    asyncio.run(_main())
