#!/usr/bin/env python3
"""Homepage agent server for darkness-hy.github.io.

Primary harness: Claude Code headless CLI (`claude -p`) with a minimal custom
system prompt (replaces Claude Code defaults). Model: DeepSeek v4 Flash via
DeepSeek Anthropic-compatible API.

Fallback harness: direct DeepSeek OpenAI-compatible HTTP streaming (same model)
when Claude Code is unavailable or the Anthropic-compat path errors/timeouts.

Local RAG: knowledge/profile.md + taste.md + paper TeX indexes under
knowledge/papers/*/INDEX.md. Relevant chunks are selected per query.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import signal
import tempfile
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator, Dict, List, Optional, Tuple
import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent
KNOWLEDGE_DIR = Path(os.environ.get("AGENT_KNOWLEDGE_DIR", ROOT / "knowledge"))

# auto: HTTP first (fast); Claude Code only if AGENT_HARNESS=claude-code|claude
# (DeepSeek Anthropic-compat often 502s under Claude Code, burning ~20s on retries.)
HARNESS = os.environ.get("AGENT_HARNESS", "http").strip().lower()
CLAUDE_BIN = os.environ.get("AGENT_CLAUDE_BIN", os.environ.get("TUTOR_CLAUDE_BIN", "claude"))
MODEL = os.environ.get("AGENT_MODEL", os.environ.get("TUTOR_MODEL", "deepseek-v4-flash"))
EFFORT = os.environ.get("AGENT_EFFORT", "low")
TIMEOUT = int(os.environ.get("AGENT_TIMEOUT", os.environ.get("TUTOR_TIMEOUT", "120")))
CLAUDE_TIMEOUT = int(os.environ.get("AGENT_CLAUDE_TIMEOUT", "90"))
# Abort Claude Code after this many api_retry events (real failures only).
CLAUDE_MAX_RETRIES = int(os.environ.get("AGENT_CLAUDE_MAX_RETRIES", "3"))
MAX_CONCURRENCY = int(os.environ.get("AGENT_MAX_CONCURRENCY", "3"))
MAX_QUEUE = int(os.environ.get("AGENT_MAX_QUEUE", "15"))
RATE_PER_MIN = int(os.environ.get("AGENT_RATE_PER_MIN", "20"))
RATE_GLOBAL_PER_MIN = int(os.environ.get("AGENT_RATE_GLOBAL_PER_MIN", "60"))
TRUST_PROXY = os.environ.get("AGENT_TRUST_PROXY", "1").lower() not in ("0", "false", "no", "")
BEARER = os.environ.get("AGENT_BEARER", os.environ.get("TUTOR_BEARER", ""))
LOG_DIR = os.environ.get("AGENT_LOG_DIR", str(ROOT / "logs"))
LOG_FULL = os.environ.get("AGENT_LOG_FULL", "0").lower() not in ("0", "false", "no", "")
RAG_BUDGET = int(os.environ.get("AGENT_RAG_BUDGET", "3500"))
TEMPERATURE = float(os.environ.get("AGENT_TEMPERATURE", "0.3"))
THINKING = os.environ.get("AGENT_THINKING", "disabled").strip().lower()
# Stream intermediate process events (status/thinking/tool) to the browser.
STREAM_PROCESS = os.environ.get("AGENT_STREAM_PROCESS", "1").lower() not in ("0", "false", "no", "")
# Claude Code tools (comma-separated). No Bash/Edit.
# Omit native WebSearch/WebFetch — they often fail on DeepSeek Anthropic gateway
# ("no WebSearch tool"). Use MCP web_search / web_fetch + server prefetch instead.
_DEFAULT_CC_TOOLS = "Read,Glob,Grep"
CC_TOOLS = [
    t.strip()
    for t in os.environ.get("AGENT_CC_TOOLS", _DEFAULT_CC_TOOLS).split(",")
    if t.strip()
]
# Survey queries: server-side DDG search injected into context (reliable).
SURVEY_PREFETCH = os.environ.get("AGENT_SURVEY_PREFETCH", "1").lower() not in (
    "0",
    "false",
    "no",
    "",
)
# Extra dirs for Read beyond knowledge/ (comma-separated absolute paths).
CC_ADD_DIRS = [
    p.strip()
    for p in os.environ.get("AGENT_CC_ADD_DIRS", "").split(",")
    if p.strip()
]
# Pre-fetch http(s) URLs from the user message into context (reliable vs model skipping tools).
URL_PREFETCH = os.environ.get("AGENT_URL_PREFETCH", "1").lower() not in ("0", "false", "no", "")
URL_PREFETCH_MAX = int(os.environ.get("AGENT_URL_PREFETCH_MAX", "3"))
URL_PREFETCH_CHARS = int(os.environ.get("AGENT_URL_PREFETCH_CHARS", "8000"))

# Claude Code talks to DeepSeek through Anthropic-compatible endpoint.
DEEPSEEK_KEY = (
    os.environ.get("DEEPSEEK_API_KEY")
    or os.environ.get("TUTOR_API_KEY")
    or ""
)
ANTHROPIC_BASE_URL = os.environ.get(
    "ANTHROPIC_BASE_URL", "https://api.deepseek.com/anthropic"
).rstrip("/")
OPENAI_BASE_URL = os.environ.get(
    "AGENT_OPENAI_BASE", os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
).rstrip("/")
_DEFAULT_ORIGINS = ",".join(
    [
        "https://darkness-hy.github.io",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://localhost:8080",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8080",
        "null",  # file:// previews
    ]
)
ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "AGENT_ALLOWED_ORIGINS",
        os.environ.get("TUTOR_ALLOWED_ORIGINS", _DEFAULT_ORIGINS),
    ).split(",")
    if o.strip()
]

logger = logging.getLogger("homepage-agent")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

app = FastAPI(title="Hongyu homepage agent")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
)

_sem = asyncio.Semaphore(MAX_CONCURRENCY)
_inflight = 0
_hits: Dict[str, deque] = defaultdict(deque)
_global_hits: deque = deque()


class Turn(BaseModel):
    role: str
    content: str = Field(default="", max_length=8000)


class ChatRequest(BaseModel):
    message: str = Field(max_length=4000)
    history: List[Turn] = Field(default_factory=list, max_length=50)
    context: Optional[str] = Field(default=None, max_length=16000)
    lang: str = Field(default="en", max_length=8)
    stream: bool = True


def _window_ok(q: deque, limit: int) -> bool:
    if limit <= 0:
        return True
    now = time.time()
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= limit:
        return False
    q.append(now)
    return True


def rate_ok(ip: str) -> bool:
    if not _window_ok(_hits[ip], RATE_PER_MIN):
        return False
    return _window_ok(_global_hits, RATE_GLOBAL_PER_MIN)


def client_ip(request: Request, xff: Optional[str]) -> str:
    if TRUST_PROXY and xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def readiness() -> Tuple[bool, Optional[str]]:
    if not DEEPSEEK_KEY:
        return False, "missing_deepseek_api_key"
    if HARNESS in ("claude-code", "claude", "auto") and not shutil.which(CLAUDE_BIN):
        if HARNESS == "auto":
            return True, None  # HTTP fallback still works
        return False, "missing_claude_cli"
    return True, None

# ── Local RAG ──────────────────────────────────────────────────────────────

_DOC_CACHE: List[Tuple[str, str]] = []  # (doc_id, text)


def _load_docs() -> List[Tuple[str, str]]:
    global _DOC_CACHE
    if _DOC_CACHE:
        return _DOC_CACHE
    docs: List[Tuple[str, str]] = []
    if not KNOWLEDGE_DIR.exists():
        logger.warning("knowledge dir missing: %s", KNOWLEDGE_DIR)
        _DOC_CACHE = docs
        return docs

    for name in ("profile.md", "taste.summary.md", "taste.md"):
        p = KNOWLEDGE_DIR / name
        if p.exists():
            docs.append((name, p.read_text(encoding="utf-8", errors="ignore")))

    papers = KNOWLEDGE_DIR / "papers"
    if papers.exists():
        for index in sorted(papers.glob("*/INDEX.md")):
            docs.append((str(index.relative_to(KNOWLEDGE_DIR)), index.read_text(encoding="utf-8", errors="ignore")))
        # also keep raw main tex snippets if INDEX missing
        for tex in sorted(papers.glob("*/*.tex")):
            rel = str(tex.relative_to(KNOWLEDGE_DIR))
            if any(rel.startswith(Path(d).parent.as_posix()) for d, _ in docs if d.endswith("INDEX.md")):
                continue
            docs.append((rel, tex.read_text(encoding="utf-8", errors="ignore")[:20000]))

    _DOC_CACHE = docs
    logger.info("loaded %d knowledge docs from %s", len(docs), KNOWLEDGE_DIR)
    return docs


def _tokens(text: str) -> set:
    return {t for t in re.findall(r"[a-zA-Z一-鿿]{2,}", text.lower()) if len(t) > 1}


# Only named Hongyu papers / explicit paper asks pull local paper RAG.
_PAPER_NAME_HINTS = (
    "uni-lavira",
    "lavira",
    "v-dreamer",
    "vdreamer",
    "acorm",
    "mfrs",
    "paper",
    "arxiv",
    "论文",
)
# Open-field survey → web first, not local INDEX spam
_SURVEY_HINTS = (
    "调研",
    "综述",
    "领域",
    "survey",
    "landscape",
    "state of the art",
    "sota",
    "field",
    "community",
    "literature",
    "related work",
    "research area",
)


def _is_survey_query(ql: str) -> bool:
    return any(k in ql for k in _SURVEY_HINTS)


def _is_taste_skill_query(message: str) -> bool:
    """True for the homepage suggestion and clear taste/belief questions.

    These must load the full hongyu-insight-taste skill (taste.md) before answering.
    """
    ql = (message or "").lower().strip()
    if not ql:
        return False
    # Exact / near-exact homepage suggestion chips
    suggestion_needles = (
        "what is hongyu's research taste / beliefs?",
        "what is hongyu's research taste/beliefs?",
        "what is hongyu's research taste",
        "research taste / beliefs",
        "research taste/beliefs",
        "hongyu 的 research taste / 信念是什么",
        "hongyu 的 research taste/信念是什么",
        "research taste / 信念",
        "research taste /信念",
    )
    if any(n in ql for n in suggestion_needles):
        return True
    # Explicit skill file / full skill
    if any(
        k in ql
        for k in (
            "taste.md",
            "taste skill",
            "hongyu-insight-taste",
            "hongyuding-skill",
            "hongyu_insight_taste",
            "insight & taste",
            "insight and taste",
        )
    ):
        return True
    # "research taste" + beliefs/philosophy style
    has_taste = any(k in ql for k in ("research taste", "taste", "品味", "insight"))
    has_belief = any(
        k in ql for k in ("belief", "beliefs", "信念", "philosophy", "原则", "观点", "value")
    )
    if has_taste and has_belief:
        return True
    # standalone strong ask
    if re.search(r"\b(research\s+)?taste\b", ql) and any(
        k in ql for k in ("what", "hongyu", "his", "是什么", "怎样", "如何")
    ):
        return True
    return False


def _want_full_taste(ql: str) -> bool:
    """True when visitor needs the full taste skill (not summary)."""
    if _is_taste_skill_query(ql):
        return True
    deep = (
        "taste.md",
        "full taste",
        "detailed taste",
        "taste skill",
        "writing taste",
        "visual",
        "collaboration",
        "展开",
        "详细",
        "完整",
        "taste 细节",
        "写作",
        "审美",
        "协作",
    )
    return any(k in ql for k in deep)


def taste_skill_context(message: str) -> Tuple[str, List[dict]]:
    """Server-side Read of full hongyu-insight-taste skill (knowledge/taste.md).

    Used for the fixed suggestion and clear taste/beliefs questions so the
    model always answers from the full skill, not taste.summary.md alone.
    Returns (context_for_model, ui_tool_bubbles).
    """
    if not _is_taste_skill_query(message):
        return "", []
    path = KNOWLEDGE_DIR / "taste.md"
    if not path.is_file():
        return "", []
    try:
        body = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return "", []
    # Cap very long skill files (~10k is fine; keep headroom)
    max_chars = 14000
    if len(body) > max_chars:
        body = body[:max_chars] + "\n…[truncated]…"
    # Prefer short display path in the UI bubble
    try:
        display = str(path.relative_to(ROOT))
    except ValueError:
        display = "knowledge/taste.md"
    abs_path = str(path)
    ui = [
        {
            "type": "tool_call",
            "name": "Read",
            "text": f"Read({display})",
        }
    ]
    ctx = (
        "# Full taste skill (server Read of hongyu-insight-taste / taste.md — "
        "answer ONLY from this skill content; do not invent project names)\n"
        f"## file: {abs_path}\n{body}\n"
    )
    return ctx, ui


def select_rag(query: str, budget: int = RAG_BUDGET) -> str:
    """Compact RAG: profile + taste.summary; full taste via taste_skill_context."""
    docs = _load_docs()
    if not docs:
        return ""

    q = _tokens(query)
    ql = query.lower()
    survey = _is_survey_query(ql)
    taste_skill = _is_taste_skill_query(query)
    want_papers = (not survey) and (
        any(kw in ql for kw in _PAPER_NAME_HINTS)
        or any(t in q for t in ("paper", "arxiv", "lavira", "mfrs", "acorm", "dreamer"))
    )
    want_taste = taste_skill or any(
        k in ql
        for k in (
            "taste",
            "belief",
            "beliefs",
            "philosophy",
            "value",
            "insight",
            "信念",
            "品味",
            "观点",
            "原则",
        )
    )
    full_taste = _want_full_taste(ql)

    # Open survey: no local RAG — web results are injected separately
    if survey and not want_papers:
        return ""
    # Full skill path: skill body injected separately; skip summary RAG noise
    if taste_skill:
        return ""

    ordered: List[Tuple[str, str, float]] = []
    for doc_id, text in docs:
        if doc_id == "profile.md":
            score = 1e6
        elif doc_id == "taste.summary.md":
            score = 1e5 if want_taste else 80.0
        elif doc_id == "taste.md":
            # Full skill only via taste_skill_context (Read bubble path)
            continue
        else:
            if not want_papers:
                continue
            dt = _tokens(text[:6000])
            overlap = len(q & dt) if q else 0
            boost = 0.0
            for kw in _PAPER_NAME_HINTS:
                hay = doc_id.lower().replace("-", "") + text[:1500].lower()
                if kw in ql and kw.replace("-", "") in hay.replace("-", ""):
                    boost += 8
            score = overlap + boost
            if score <= 0:
                continue
        ordered.append((doc_id, text, score))

    ordered.sort(key=lambda x: x[2], reverse=True)

    parts: List[str] = []
    used = 0
    for doc_id, text, score in ordered:
        chunk = text.strip()
        if doc_id == "profile.md":
            per_cap = 1200
        elif doc_id == "taste.summary.md":
            per_cap = 900
        elif doc_id.endswith("INDEX.md"):
            per_cap = 1800  # one paper summary at a time
        else:
            per_cap = 1200
        if len(chunk) > per_cap:
            chunk = chunk[:per_cap] + "\n[...truncated...]\n"
        block = f"### {doc_id}\n{chunk}\n"
        if used + len(block) > budget:
            remain = budget - used
            if remain < 300:
                break
            block = block[:remain] + "\n[...truncated...]\n"
            parts.append(block)
            break
        parts.append(block)
        used += len(block)
        # at most profile + taste.summary + 1 paper INDEX
        if len(parts) >= (3 if want_papers else 2):
            break
    # Hint when full taste may be needed later
    if want_taste and not full_taste:
        parts.append(
            "### note\nTaste detail: use taste.summary.md above. "
            f"Only Read {KNOWLEDGE_DIR / 'taste.md'} if visitor asks for full/deep taste.\n"
        )
    return "\n".join(parts)


def _knowledge_map() -> str:
    """Short map so Claude Code Read can open the right files."""
    papers_dir = KNOWLEDGE_DIR / "papers"
    paper_ids: List[str] = []
    if papers_dir.exists():
        paper_ids = sorted(d.name for d in papers_dir.iterdir() if d.is_dir())
    lines = [
        "Local files (Read sparingly — do not open every paper):",
        f"- {KNOWLEDGE_DIR / 'profile.md'} — bio / paper list",
        f"- {KNOWLEDGE_DIR / 'taste.summary.md'} — taste short summary (default for light mentions)",
        f"- {KNOWLEDGE_DIR / 'taste.md'} — full hongyu-insight-taste skill "
        "(auto-Read for research taste / beliefs)",
        f"- {KNOWLEDGE_DIR / 'papers'}/<arxiv-id>/INDEX.md — one paper at a time; ids: {', '.join(paper_ids)}",
        "Tools:",
        "- Field survey: use injected Web search results (or MCP web_search). Do NOT Read all INDEX.md.",
        "- Specific Hongyu paper → Read that paper's INDEX.md only.",
        "- Research taste / beliefs → full taste.md is pre-Read into context.",
        "- URL → Fetched pages or MCP web_fetch.",
        "- No Bash/Edit. Do not invent citations.",
    ]
    return "\n".join(lines)


def system_prompt(
    lang: str,
    rag: str,
    extra_context: Optional[str],
    *,
    survey: bool = False,
    taste_skill: bool = False,
) -> str:
    """Minimal persona + tool map; light RAG; survey uses web_search."""
    if lang == "zh":
        lines = [
            "你是 Hongyu Ding 个人主页 AI 助理「茜茜」。勿主动报名字；被问到才说。",
            "【强制精简】默认 2–4 句 / ≤80 汉字；先结论。禁止长文、多级分点、领域综述式铺陈。"
            "访客说「详细/展开」才可加长。最多 1 个 emoji。不编造。本轮简体中文。",
            "【工具】联网用 MCP web_search / web_fetch（不要用已禁用的原生 WebSearch）。"
            "调研题若上下文已有「Web search results」段落，直接用它回答，不要说没有搜索工具，也不要乱读本地论文。"
            "taste 默认 taste.summary.md；研究 taste/信念题会注入完整 taste.md skill。"
            "某篇 Hongyu 论文 → 只 Read 对应一篇。URL → Fetched pages 或 web_fetch。"
            "禁止说没有浏览器。",
        ]
    else:
        lines = [
            "You are Cici (茜茜) on Hongyu Ding's homepage. Name yourself only if asked.",
            "Conciseness mandatory: 2–4 short sentences / ~60 words default. Lead with the answer. "
            "No long essays or multi-level bullet dumps unless the visitor asks for detail. ≤1 emoji. English this turn.",
            "TOOLS: use MCP web_search / web_fetch for the open web (native WebSearch is disabled). "
            "If context has 'Web search results', use them — never claim search is unavailable. "
            "Do not Read many local paper INDEX files for open field surveys. "
            "Taste: taste.summary.md by default; research taste/beliefs loads full taste.md skill. "
            "One Hongyu paper → Read that one only. URL → Fetched pages or web_fetch.",
        ]
    if taste_skill:
        if lang == "zh":
            lines.append(
                "【本轮=research taste / 信念】上下文已有完整 hongyu-insight-taste skill（taste.md）。"
                "必须基于该 skill 回答：insight 标准、判断启发式、写作/叙事偏好；2–5 句，先结论。"
                "禁止编造具体项目名/论文名/工具名（skill 本身也不写这些）。"
                "本轮不要再 Read 其他本地文件；不要用 taste.summary。"
            )
        else:
            lines.append(
                "TASTE SKILL TURN: Full hongyu-insight-taste skill (taste.md) is already in context. "
                "Answer from that skill only: insight standards, judgment heuristics, writing/narrative taste. "
                "2–5 sentences; lead with the point. Do not invent project/paper/tool names. "
                "Do not Read other local files; do not use the short summary."
            )
        lines.append(
            "Tools this turn: none required (skill already Read). Do not call Read/Glob/Grep."
        )
    elif survey:
        if lang == "zh":
            lines.append(
                "【本轮=领域调研】上下文已有 Web search results：只根据这些结果用 2–4 句回答（定义、趋势、1 个开放问题）。"
                "本轮禁止 Read 任何本地文件（profile/taste/INDEX 都不要读）。Hongyu 相关最多半句。"
            )
        else:
            lines.append(
                "FIELD SURVEY: Web search results are already in context. Answer in 2–4 sentences only. "
                "Do NOT Read any local files this turn. At most half a sentence on Hongyu."
            )
        # Survey: skip heavy knowledge map to avoid encouraging Read spam
        lines.append(
            "Tools this turn: none required (results prefetched). Do not call Read/Glob/Grep."
        )
    else:
        lines.append(_knowledge_map())
    if rag and not survey and not taste_skill:
        lines.append("Hint excerpts (truncated; Read only if needed):\n" + rag)
    # taste skill body can be ~10k; allow more headroom than URL prefetch alone
    extra_cap = URL_PREFETCH_CHARS * URL_PREFETCH_MAX + (16000 if taste_skill else 2000)
    if extra_context:
        lines.append(extra_context[:extra_cap])
    return "\n".join(lines)


_URL_RE = re.compile(r"https?://[^\s<>\"')\]]+", re.I)


def extract_urls(text: str, limit: int = 3) -> List[str]:
    found: List[str] = []
    for m in _URL_RE.finditer(text or ""):
        u = m.group(0).rstrip(".,;:!?")
        if u not in found:
            found.append(u)
        if len(found) >= limit:
            break
    return found


def _html_to_text(html: str) -> str:
    # drop scripts/styles
    html = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    html = re.sub(r"(?is)<!--.*?-->", " ", html)
    # titles/headings keep some structure
    html = re.sub(r"(?is)<title[^>]*>(.*?)</title>", r"\n# \1\n", html)
    html = re.sub(r"(?is)<h[1-3][^>]*>(.*?)</h[1-3]>", r"\n## \1\n", html)
    html = re.sub(r"(?is)<(br|p|div|li|tr)[^>]*>", "\n", html)
    text = re.sub(r"(?is)<[^>]+>", " ", html)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def survey_search_context(message: str) -> Tuple[str, List[dict]]:
    """Server-side multi-source search for field-survey questions.

    Sources: Wikipedia + arXiv + OpenAlex + DuckDuckGo (see mcp_websearch.multi_search).
    Returns (context_for_model, ui_tool_bubbles). Avoids broken native WebSearch.
    """
    if not SURVEY_PREFETCH or not _is_survey_query(message.lower()):
        return "", []
    # Build one focused English-friendly query
    q = re.sub(r"\s+", " ", message).strip()
    query = q
    if re.search(r"[A-Za-z]{3,}", q):
        latin = " ".join(re.findall(r"[A-Za-z][A-Za-z0-9\-_/]+", q))
        if latin:
            # academic-oriented query improves arXiv / OpenAlex hit quality
            query = f"{latin} robotics survey"
    if "mobile" in q.lower() and "manipulation" in q.lower():
        query = "mobile manipulation robotics"
    elif "操控" in q and ("移动" in q or "mobile" in q.lower()):
        query = "mobile manipulation robotics"

    try:
        from mcp_websearch import multi_search  # type: ignore
    except Exception:
        try:
            from mcp_websearch import ddg_search as multi_search  # type: ignore
        except Exception:
            return "", []

    ui: List[dict] = [
        {
            "type": "tool_call",
            "name": "WebSearch",
            "text": f"WebSearch({query})",
        }
    ]
    hits = multi_search(query, max_results=7)
    ok_hits = [
        h
        for h in hits
        if h.get("title") != "search_empty" and (h.get("url") or h.get("snippet"))
    ]
    if not ok_hits:
        ui.append(
            {
                "type": "tool_result",
                "name": "WebSearch",
                "text": "⎿  0 results",
            }
        )
        return "", ui

    sources = sorted({(h.get("source") or "?").split(":")[0] for h in ok_hits})
    ui.append(
        {
            "type": "tool_result",
            "name": "WebSearch",
            "text": f"⎿  {len(ok_hits)} results ({'+'.join(sources)})",
        }
    )
    blocks: List[str] = [
        "# Web search results (multi-source: Wikipedia + arXiv + OpenAlex + DDG — "
        "use these; do not claim no WebSearch)",
        f"## query: {query}",
    ]
    seen_urls: set = set()
    for h in ok_hits:
        u = h.get("url") or ""
        if u and u in seen_urls:
            continue
        if u:
            seen_urls.add(u)
        src = h.get("source") or ""
        blocks.append(
            f"- [{src}] {h.get('title')}\n  {u}\n  {h.get('snippet') or ''}"
        )
    return "\n".join(blocks), ui


async def prefetch_urls(message: str) -> Tuple[str, List[dict]]:
    """Server-side fetch of URLs in the user message.

    Returns (full_text_for_model, ui_items) where ui_items are compact
    Claude-Code-style tool call/result summaries for the chat UI.
    """
    if not URL_PREFETCH:
        return "", []
    urls = extract_urls(message, URL_PREFETCH_MAX)
    if not urls:
        return "", []
    blocks: List[str] = ["# Fetched pages (server pre-fetch — use this content)"]
    ui_items: List[dict] = []
    timeout = httpx.Timeout(connect=8.0, read=12.0, write=8.0, pool=8.0)
    headers = {
        "User-Agent": "HomepageAgent/1.0 (+https://hongyuding.site; research assistant)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
        for url in urls:
            # CC-style call line (compact)
            ui_items.append(
                {
                    "type": "tool_call",
                    "name": "WebFetch",
                    "text": f"WebFetch({url})",
                }
            )
            try:
                resp = await client.get(url)
                ctype = (resp.headers.get("content-type") or "").lower()
                raw = resp.text if resp.status_code < 400 else ""
                if "html" in ctype or raw.lstrip().startswith("<"):
                    body = _html_to_text(raw)[:URL_PREFETCH_CHARS]
                else:
                    body = raw[:URL_PREFETCH_CHARS]
                if not body:
                    body = f"(empty or HTTP {resp.status_code})"
                blocks.append(f"## {url}\nstatus={resp.status_code}\n{body}\n")
                # title from first markdown heading if any
                title = ""
                for line in body.splitlines():
                    s = line.strip()
                    if s.startswith("#"):
                        title = s.lstrip("#").strip()[:80]
                        break
                summary = f"⎿  {resp.status_code}"
                if title:
                    summary += f" · {title}"
                summary += f" · {len(body)} chars"
                ui_items.append(
                    {
                        "type": "tool_result",
                        "name": "WebFetch",
                        "text": summary,
                    }
                )
            except Exception as e:
                blocks.append(f"## {url}\n(fetch failed: {e})\n")
                ui_items.append(
                    {
                        "type": "tool_result",
                        "name": "WebFetch",
                        "text": f"⎿  error · {str(e)[:80]}",
                    }
                )
    return "\n".join(blocks), ui_items
def user_prompt(message: str, history: List[Turn]) -> str:
    parts: List[str] = []
    for t in history[-8:]:
        who = "Visitor" if t.role == "user" else "Assistant"
        parts.append(f"{who}: {t.content}")
    parts.append(f"Visitor: {message}")
    return "\n".join(parts)


def sse(obj: dict) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


def log_turn(rec: dict) -> None:
    if not LOG_DIR:
        return
    try:
        Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with open(Path(LOG_DIR) / f"chat-{day}.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _proc(kind: str, text: str, **extra) -> Tuple[str, str]:
    """SSE process/status event (not counted as answer text)."""
    if not STREAM_PROCESS or not text:
        return "", ""
    obj = {"type": kind, "text": text}
    obj.update(extra)
    return sse(obj), ""


def _tool_msg(kind: str, name: str, body: str, **extra) -> Tuple[str, str]:
    """Chat-facing tool call / tool result (frontend shows as its own bubble).

    Always emitted (not gated by STREAM_PROCESS) so the UI can render separate turns.
    Keep `text` compact (CC-style); put long dumps only in model context.
    """
    obj = {
        "type": kind,  # tool_call | tool_result
        "name": name or "tool",
        "text": (body or "")[:500],  # UI one-liner / short result
    }
    obj.update(extra)
    return sse(obj), ""


def _summarize_tool_input(name: str, raw_in: str) -> str:
    """Claude Code style: ToolName(arg)."""
    raw_in = (raw_in or "").strip()
    short = name or "tool"
    # strip MCP prefix for display
    if short.startswith("mcp__"):
        parts = short.split("__")
        short = parts[-1] if parts else short
    if not raw_in:
        return f"{short}()"
    try:
        data = json.loads(raw_in)
        if isinstance(data, dict):
            if short in ("Read", "read"):
                path = data.get("file_path") or data.get("path") or ""
                # basename for compactness, full path if short
                disp = path
                if len(disp) > 72:
                    disp = "…/" + Path(path).name
                return f"Read({disp})" if path else f"Read()"
            if short in ("WebSearch", "web_search", "WebSearchTool"):
                q = data.get("query") or data.get("q") or ""
                q = (q[:60] + "…") if len(q) > 60 else q
                return f"WebSearch({q!r})" if q else "WebSearch()"
            if short in ("WebFetch", "web_fetch", "url_prefetch"):
                u = data.get("url") or ""
                return f"WebFetch({u})" if u else "WebFetch()"
            if short in ("Glob",):
                pat = data.get("pattern") or data.get("glob_pattern") or ""
                return f"Glob({pat!r})" if pat else "Glob()"
            if short in ("Grep",):
                pat = data.get("pattern") or ""
                return f"Grep({pat!r})" if pat else "Grep()"
            # generic: first stringy arg
            for k, v in data.items():
                if isinstance(v, str) and v:
                    vv = v if len(v) <= 64 else v[:61] + "…"
                    return f"{short}({vv!r})"
    except json.JSONDecodeError:
        pass
    arg = raw_in if len(raw_in) <= 64 else raw_in[:61] + "…"
    return f"{short}({arg})"


def _summarize_tool_result(name: str, body: str) -> str:
    """Compact result line like CC: ⎿  n lines / short preview."""
    body = (body or "").strip()
    short = name or "tool"
    if short.startswith("mcp__"):
        short = short.split("__")[-1]
    if not body:
        return "⎿  (empty)"
    # JSON list of search hits
    try:
        data = json.loads(body)
        if isinstance(data, dict) and "results" in data:
            n = len(data.get("results") or [])
            return f"⎿  {n} results"
        if isinstance(data, dict) and data.get("ok") and data.get("url"):
            return f"⎿  {data.get('status', '')} · {len(str(data.get('text') or ''))} chars"
    except json.JSONDecodeError:
        pass
    lines = [ln for ln in body.splitlines() if ln.strip()]
    n = len(lines)
    # file-number prefix from Read tool: "1\t---"
    if n and re.match(r"^\d+\t", lines[0]):
        return f"⎿  Read {n} lines"
    preview = re.sub(r"\s+", " ", lines[0])[:72] if lines else body[:72]
    return f"⎿  {n} lines · {preview}"


def _truncate_tool_result(text: str, limit: int = 6000) -> str:
    text = text or ""
    if len(text) <= limit:
        return text
    return text[:limit] + "\n…[truncated]…"

def _claude_isolated_settings() -> Tuple[str, str, Optional[str]]:
    """Write one-shot Claude settings + optional MCP websearch config.

    Returns (settings_path, cfg_dir, mcp_config_path|None).

    Global ~/.claude/settings.json may point ANTHROPIC_BASE_URL at a local
    cli-proxy (e.g. 127.0.0.1:8317) with Grok models — that yields 502
    "unknown provider for model deepseek-v4-flash". Isolation is required.
    """
    cfg_dir = Path(tempfile.mkdtemp(prefix="homepage-agent-cc-"))
    settings_path = cfg_dir / "settings.json"
    # WebSearch needs nonessential traffic; keep telemetry off.
    settings = {
        "env": {
            "ANTHROPIC_BASE_URL": ANTHROPIC_BASE_URL,
            "ANTHROPIC_API_KEY": DEEPSEEK_KEY,
            "ANTHROPIC_AUTH_TOKEN": DEEPSEEK_KEY,
            "ANTHROPIC_MODEL": MODEL,
            "ANTHROPIC_DEFAULT_SONNET_MODEL": MODEL,
            "ANTHROPIC_DEFAULT_OPUS_MODEL": MODEL,
            "ANTHROPIC_DEFAULT_HAIKU_MODEL": MODEL,
            "ANTHROPIC_SMALL_FAST_MODEL": MODEL,
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "0",
            "DISABLE_TELEMETRY": "1",
            "DO_NOT_TRACK": "1",
            # Empty proxies so local 7892 / etc. cannot intercept DeepSeek TLS.
            "HTTP_PROXY": "",
            "HTTPS_PROXY": "",
            "http_proxy": "",
            "https_proxy": "",
            "ALL_PROXY": "",
            "all_proxy": "",
            "NO_PROXY": "*",
            "no_proxy": "*",
        },
        "permissions": {
            # Headless allow-list (also pass --dangerously-skip-permissions).
            "allow": [
                "Read(*)",
                "Glob(*)",
                "Grep(*)",
                "mcp__websearch__web_search",
                "mcp__websearch__web_fetch",
                "mcp__websearch__*",
            ],
            "deny": [
                "Bash(*)",
                "Edit(*)",
                "Write(*)",
                "MultiEdit(*)",
                "NotebookEdit(*)",
            ],
        },
        "effortLevel": EFFORT if EFFORT in ("low", "medium", "high") else "low",
    }
    settings_path.write_text(json.dumps(settings), encoding="utf-8")

    # Free DuckDuckGo MCP (no API key)
    mcp_path: Optional[str] = None
    mcp_script = ROOT / "mcp_websearch.py"
    if mcp_script.exists():
        py = ROOT / ".venv" / "bin" / "python3"
        cmd_py = str(py) if py.exists() else "python3"
        mcp_cfg = {
            "mcpServers": {
                "websearch": {
                    "command": cmd_py,
                    "args": [str(mcp_script.resolve())],
                }
            }
        }
        p = cfg_dir / "mcp.json"
        p.write_text(json.dumps(mcp_cfg), encoding="utf-8")
        mcp_path = str(p)
    return str(settings_path), str(cfg_dir), mcp_path
async def stream_claude(sys_prompt: str, prompt: str) -> AsyncIterator[Tuple[str, str]]:
    """Headless Claude Code; yields (sse_frame, text_chunk). Raises RuntimeError on soft fail for fallback."""
    if not shutil.which(CLAUDE_BIN):
        raise RuntimeError("missing_claude_cli")
    if not DEEPSEEK_KEY:
        raise RuntimeError("missing_deepseek_api_key")

    settings_path, cfg_dir, mcp_config_path = _claude_isolated_settings()
    env = os.environ.copy()
    # Drop host Claude Code / Anthropic / proxy overrides; settings file re-injects DeepSeek.
    for k in list(env):
        ku = k.upper()
        if ku.startswith("ANTHROPIC_") or ku.startswith("CLAUDE_CODE") or ku in {
            "CLAUDECODE",
            "API_TIMEOUT_MS",
            "DISABLE_AUTOUPDATER",
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "ALL_PROXY",
            "http_proxy",
            "https_proxy",
            "all_proxy",
        }:
            env.pop(k, None)
    env["ANTHROPIC_BASE_URL"] = ANTHROPIC_BASE_URL
    env["ANTHROPIC_API_KEY"] = DEEPSEEK_KEY
    env["ANTHROPIC_AUTH_TOKEN"] = DEEPSEEK_KEY
    env["ANTHROPIC_MODEL"] = MODEL
    # Must be 0 so WebSearch/WebFetch are available.
    env["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = "0"
    env["CLAUDE_CONFIG_DIR"] = cfg_dir
    env["CLAUDE_CODE_SIMPLE"] = "1"

    # Isolation via CLAUDE_CONFIG_DIR + --settings (DeepSeek, not local proxy).
    # Native WebSearch/WebFetch omitted — use MCP web_search/web_fetch.
    tools = CC_TOOLS or ["Read", "Glob", "Grep"]
    add_dirs: List[str] = [str(KNOWLEDGE_DIR.resolve())]
    code_root = Path("/home/nvme03/dhy/workspace/code")
    if code_root.exists():
        add_dirs.append(str(code_root.resolve()))
    for d in CC_ADD_DIRS:
        p = Path(d)
        if p.exists():
            add_dirs.append(str(p.resolve()))
    # de-dupe preserve order
    seen = set()
    add_dirs = [d for d in add_dirs if not (d in seen or seen.add(d))]

    cmd = [
        CLAUDE_BIN,
        "-p",
        "--settings",
        settings_path,
        "--model",
        MODEL,
        "--effort",
        EFFORT,
        "--tools",
        *tools,
        "--dangerously-skip-permissions",
        "--system-prompt",
        sys_prompt,  # full replace of default system prompt
        "--output-format",
        "stream-json",
        "--verbose",
        "--include-partial-messages",
        "--no-session-persistence",
    ]
    if mcp_config_path:
        cmd.extend(["--mcp-config", mcp_config_path])
    for d in add_dirs:
        cmd.extend(["--add-dir", d])

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
        start_new_session=True,
        cwd=str(ROOT),
    )
    assert proc.stdin and proc.stdout
    deadline = time.time() + CLAUDE_TIMEOUT
    got_text = False
    err_msg: Optional[str] = None
    api_retries = 0
    # Track open content blocks for tool/thinking labels
    open_blocks: Dict[int, str] = {}
    tool_json_buf: Dict[int, str] = {}
    tool_names: Dict[int, str] = {}
    tool_id_names: Dict[str, str] = {}
    emitted_tool_calls: set = set()  # avoid double tool_call from stream+assistant snapshots
    thinking_on = THINKING not in ("0", "false", "no", "off", "disabled", "")

    # Quiet status (CC doesn't dump tool lists every turn)
    frame, _ = _proc("status", f"Claude Code · {MODEL}")
    if frame:
        yield frame, ""

    try:
        try:
            proc.stdin.write(prompt.encode("utf-8"))
            await asyncio.wait_for(proc.stdin.drain(), timeout=min(10, CLAUDE_TIMEOUT))
            proc.stdin.close()
        except (asyncio.TimeoutError, BrokenPipeError, ConnectionResetError):
            err_msg = "claude_timeout"
        while err_msg is None:
            remaining = deadline - time.time()
            if remaining <= 0:
                err_msg = "claude_timeout"
                break
            try:
                raw = await asyncio.wait_for(proc.stdout.readline(), timeout=remaining)
            except asyncio.TimeoutError:
                err_msg = "claude_timeout"
                break
            if not raw:
                break
            line = raw.decode("utf-8", "replace").strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue

            mtype = msg.get("type")
            if mtype == "system":
                subtype = msg.get("subtype")
                if subtype == "api_retry":
                    api_retries += 1
                    status = msg.get("error_status")
                    logger.warning("claude api_retry %s: %s", api_retries, status)
                    frame, _ = _proc(
                        "status",
                        f"API retry {api_retries}/{CLAUDE_MAX_RETRIES} (HTTP {status})",
                    )
                    if frame:
                        yield frame, ""
                    if api_retries >= CLAUDE_MAX_RETRIES:
                        err_msg = "claude_api_retry"
                        break
                elif subtype == "status" and msg.get("status"):
                    # Skip noisy intermediate statuses like "requesting"
                    st = str(msg.get("status"))
                    if st not in ("requesting", "thinking"):
                        frame, _ = _proc("status", st)
                        if frame:
                            yield frame, ""
                continue

            if mtype == "stream_event":
                ev = msg.get("event") or {}
                et = ev.get("type")
                if et == "content_block_start":
                    idx = int(ev.get("index") or 0)
                    block = ev.get("content_block") or {}
                    btype = block.get("type") or "text"
                    open_blocks[idx] = btype
                    if btype == "tool_use":
                        name = block.get("name") or "tool"
                        tool_names[idx] = name
                        tool_json_buf[idx] = ""
                        tid = block.get("id")
                        if isinstance(tid, str) and tid:
                            tool_id_names[tid] = name
                        frame, _ = _proc("tool", f"→ {name}", name=name, phase="start")
                        if frame:
                            yield frame, ""
                    elif btype == "server_tool_use":
                        name = block.get("name") or "server_tool"
                        tool_names[idx] = name
                        tool_json_buf[idx] = ""
                        tid = block.get("id")
                        if isinstance(tid, str) and tid:
                            tool_id_names[tid] = name
                        frame, _ = _proc("tool", f"→ {name} (server)", name=name, phase="start")
                        if frame:
                            yield frame, ""
                    elif btype in ("thinking", "reasoning") and thinking_on:
                        frame, _ = _proc("status", "thinking…")
                        if frame:
                            yield frame, ""
                elif et == "content_block_delta":
                    idx = int(ev.get("index") or 0)
                    delta = ev.get("delta") or {}
                    dtype = delta.get("type")
                    btype = open_blocks.get(idx, "")
                    if dtype == "text_delta":
                        text = delta.get("text") or ""
                        if text:
                            got_text = True
                            yield sse({"type": "delta", "text": text}), text
                    elif dtype in ("thinking_delta", "reasoning_delta"):
                        text = delta.get("thinking") or delta.get("text") or delta.get("reasoning") or ""
                        if text and thinking_on:
                            frame, _ = _proc("thinking", text)
                            if frame:
                                yield frame, ""
                    elif dtype == "input_json_delta":
                        partial = delta.get("partial_json") or ""
                        if partial:
                            tool_json_buf[idx] = tool_json_buf.get(idx, "") + partial
                elif et == "content_block_stop":
                    idx = int(ev.get("index") or 0)
                    btype = open_blocks.pop(idx, None)
                    if btype in ("tool_use", "server_tool_use"):
                        name = tool_names.pop(idx, "tool")
                        raw_in = tool_json_buf.pop(idx, "").strip()
                        summary = _summarize_tool_input(name, raw_in)
                        key = f"{name}|{raw_in[:200]}"
                        if key not in emitted_tool_calls:
                            emitted_tool_calls.add(key)
                            # Close any in-progress assistant text segment before the tool bubble
                            yield sse({"type": "text_break"}), ""
                            frame, _ = _proc("tool", summary, name=name, phase="use")
                            if frame:
                                yield frame, ""
                            frame, _ = _tool_msg("tool_call", name, summary)
                            if frame:
                                yield frame, ""
                    else:
                        tool_json_buf.pop(idx, None)
                        tool_names.pop(idx, None)
                continue

            if mtype == "user":
                # Tool results come back as user messages with tool_result blocks
                content = msg.get("message", {}).get("content") or msg.get("content") or []
                if isinstance(content, list):
                    for block in content:
                        if not isinstance(block, dict):
                            continue
                        if block.get("type") != "tool_result":
                            continue
                        body = block.get("content")
                        if isinstance(body, list):
                            parts = []
                            for b in body:
                                if isinstance(b, dict) and b.get("type") == "text":
                                    parts.append(b.get("text") or "")
                                elif isinstance(b, str):
                                    parts.append(b)
                            body = "\n".join(parts)
                        elif not isinstance(body, str):
                            body = json.dumps(body, ensure_ascii=False)
                        tid = block.get("tool_use_id") or ""
                        name = (
                            block.get("name")
                            or tool_id_names.get(str(tid))
                            or "tool"
                        )
                        body_full = _truncate_tool_result(str(body))
                        summary = _summarize_tool_result(name, body_full)
                        # process log stays short too
                        frame, _ = _proc("tool", summary, name=name, phase="result")
                        if frame:
                            yield frame, ""
                        frame, _ = _tool_msg(
                            "tool_result",
                            name,
                            summary,
                            tool_use_id=tid or None,
                        )
                        if frame:
                            yield frame, ""
                continue

            if mtype == "assistant":
                content = msg.get("message", {}).get("content") or msg.get("content") or []
                if isinstance(content, list):
                    for block in content:
                        if not isinstance(block, dict):
                            continue
                        btype = block.get("type")
                        if btype == "text":
                            text = block.get("text") or ""
                            # Prefer stream_event text_delta; only use snapshot if nothing streamed yet
                            if text and not got_text:
                                got_text = True
                                yield sse({"type": "delta", "text": text}), text
                        elif btype in ("thinking", "reasoning"):
                            text = block.get("thinking") or block.get("text") or ""
                            if text and thinking_on:
                                frame, _ = _proc("thinking", text)
                                if frame:
                                    yield frame, ""
                        elif btype == "tool_use":
                            name = block.get("name") or "tool"
                            tid = block.get("id")
                            if isinstance(tid, str) and tid:
                                tool_id_names[tid] = name
                            inp = block.get("input")
                            raw_in = json.dumps(inp, ensure_ascii=False) if inp is not None else ""
                            summary = _summarize_tool_input(name, raw_in)
                            key = tid or f"{name}|{raw_in[:200]}"
                            if key not in emitted_tool_calls:
                                emitted_tool_calls.add(key)
                                yield sse({"type": "text_break"}), ""
                                frame, _ = _proc("tool", summary, name=name, phase="use")
                                if frame:
                                    yield frame, ""
                                frame, _ = _tool_msg("tool_call", name, summary)
                                if frame:
                                    yield frame, ""
                continue

            if mtype == "result" and not got_text:
                result_text = msg.get("result") or ""
                if isinstance(result_text, str) and result_text:
                    got_text = True
                    yield sse({"type": "delta", "text": result_text}), result_text

        if err_msg is None:
            try:
                await asyncio.wait_for(proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                pass
            if proc.returncode not in (0, None) and not got_text:
                stderr = b""
                if proc.stderr:
                    try:
                        stderr = await asyncio.wait_for(proc.stderr.read(), timeout=5)
                    except asyncio.TimeoutError:
                        stderr = b""
                detail = stderr.decode("utf-8", "replace").strip()
                if detail:
                    logger.error("claude exited %s: %s", proc.returncode, detail[:1000])
                err_msg = "claude_failed"

        if err_msg is not None and not got_text:
            raise RuntimeError(err_msg)
        if got_text and err_msg is not None:
            yield sse({"type": "done", "truncated": True, "path": "claude-code"}), ""
        else:
            yield sse({"type": "done", "path": "claude-code"}), ""
    finally:
        if proc.returncode is None:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
                await asyncio.wait_for(proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
            except (ProcessLookupError, PermissionError):
                pass
        # Remove one-shot settings dir (contains API key).
        try:
            shutil.rmtree(cfg_dir, ignore_errors=True)
        except Exception:
            pass

async def stream_http(sys_prompt: str, prompt: str) -> AsyncIterator[Tuple[str, str]]:
    """Direct DeepSeek OpenAI-compatible streaming (default fast path)."""
    if not DEEPSEEK_KEY:
        yield sse({"type": "error", "message": "助理服务缺少模型 API Key"}), ""
        return

    frame, _ = _proc("status", f"DeepSeek · {MODEL}")
    if frame:
        yield frame, ""

    payload: dict = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": prompt},
        ],
        "stream": True,
        "temperature": TEMPERATURE,
    }
    thinking_on = THINKING not in ("0", "false", "no", "off", "disabled", "")
    if thinking_on:
        payload["thinking"] = {"type": "enabled"}
    else:
        payload["thinking"] = {"type": "disabled"}

    url = f"{OPENAI_BASE_URL}/chat/completions"
    timeout = httpx.Timeout(connect=15.0, read=float(TIMEOUT), write=15.0, pool=15.0)
    got_text = False
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                url,
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            ) as resp:
                if resp.status_code >= 400:
                    detail = (await resp.aread()).decode("utf-8", "replace")
                    logger.error("http chat error %s: %s", resp.status_code, detail[:1000])
                    yield sse({"type": "error", "message": "助理暂时不可用,请稍后再试"}), ""
                    return
                async for line in resp.aiter_lines():
                    line = line.strip()
                    if not line or line.startswith(":") or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        msg = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    choices = msg.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    # DeepSeek reasoning / thinking channels when enabled
                    for key in ("reasoning_content", "reasoning", "thinking"):
                        r = delta.get(key)
                        if isinstance(r, str) and r:
                            frame, _ = _proc("thinking", r)
                            if frame:
                                yield frame, ""
                    text = delta.get("content") or ""
                    if text:
                        got_text = True
                        yield sse({"type": "delta", "text": text}), text
        if got_text:
            yield sse({"type": "done"}), ""
        else:
            yield sse({"type": "error", "message": "助理暂时没有返回内容,请重试"}), ""
    except httpx.TimeoutException:
        yield sse({"type": "error", "message": "响应超时,请重试"}), ""
    except httpx.HTTPError as e:
        logger.error("http chat failed: %s", e)
        yield sse({"type": "error", "message": "助理暂时不可用,请稍后再试"}), ""


async def stream_model(sys_prompt: str, prompt: str) -> AsyncIterator[Tuple[str, str]]:
    mode = HARNESS
    # Default / http: direct DeepSeek (low latency).
    if mode in ("http", "openai", "deepseek"):
        async for item in stream_http(sys_prompt, prompt):
            yield item
        return

    # auto: Claude Code first (fail-fast), then HTTP.
    # claude-code / claude: Claude only (optional no-fallback).
    if mode in ("claude-code", "claude", "auto"):
        try:
            async for item in stream_claude(sys_prompt, prompt):
                yield item
            return
        except RuntimeError as e:
            logger.warning("claude harness failed (%s); falling back to HTTP", e)
            frame, _ = _proc("status", f"fallback → HTTP ({e})")
            if frame:
                yield frame, ""
            if mode in ("claude-code", "claude") and os.environ.get("AGENT_NO_HTTP_FALLBACK", "").lower() in (
                "1",
                "true",
                "yes",
            ):
                yield sse({"type": "error", "message": "助理暂时不可用,请稍后再试"}), ""
                return
            async for item in stream_http(sys_prompt, prompt):
                yield item
            return

    # unknown harness → HTTP
    async for item in stream_http(sys_prompt, prompt):
        yield item
@app.on_event("startup")
async def _startup() -> None:
    _load_docs()
    ready, reason = readiness()
    logger.info(
        "homepage agent ready=%s reason=%s harness=%s model=%s anthropic=%s openai=%s docs=%d",
        ready,
        reason,
        HARNESS,
        MODEL,
        ANTHROPIC_BASE_URL,
        OPENAI_BASE_URL,
        len(_DOC_CACHE),
    )


@app.get("/health")
async def health():
    ready, reason = readiness()
    return {
        "ok": True,
        "ready": ready,
        "reason": reason,
        "provider": "claude-code" if HARNESS in ("claude-code", "claude", "auto") else "http",
        "harness": HARNESS,
        "model": MODEL,
        "anthropic_base_url": ANTHROPIC_BASE_URL,
        "openai_base_url": OPENAI_BASE_URL,
        "knowledge_docs": len(_DOC_CACHE) or len(_load_docs()),
        "max_concurrency": MAX_CONCURRENCY,
        "inflight": _inflight,
    }


@app.post("/chat")
async def chat(
    req: ChatRequest,
    request: Request,
    authorization: Optional[str] = Header(default=None),
    x_forwarded_for: Optional[str] = Header(default=None),
):
    global _inflight
    if BEARER and authorization != f"Bearer {BEARER}":
        raise HTTPException(status_code=401, detail="unauthorized")
    ip = client_ip(request, x_forwarded_for)
    if not rate_ok(ip):
        raise HTTPException(status_code=429, detail="rate limited")
    if _inflight >= MAX_CONCURRENCY + MAX_QUEUE:
        raise HTTPException(status_code=429, detail="服务繁忙,请稍后再试")
    _inflight += 1

    lang = "zh" if req.lang.lower().startswith("zh") else "en"
    ql = req.message.lower()
    survey = _is_survey_query(ql)
    taste_skill = _is_taste_skill_query(req.message)
    # Taste skill and field survey are mutually exclusive paths
    if taste_skill:
        survey = False
    rag = select_rag(req.message)
    # Reliable URL access: server pre-fetches links in the question
    fetched, prefetch_ui = await prefetch_urls(req.message)
    # Full hongyu-insight-taste skill for research taste / beliefs suggestion
    taste_ctx, taste_ui = taste_skill_context(req.message)
    # Multi-source survey search — avoids broken native WebSearch
    survey_ctx, survey_ui = (
        ("", []) if taste_skill else survey_search_context(req.message)
    )
    extra_bits = [x for x in (req.context, fetched, taste_ctx, survey_ctx) if x]
    extra = "\n\n".join(extra_bits) if extra_bits else None
    sys_p = system_prompt(
        lang, rag, extra, survey=survey, taste_skill=taste_skill
    )
    prompt = user_prompt(req.message, req.history)
    # UI: one bubble per unique call line (Read skill / URL / survey search)
    ui_tool_items: List[dict] = []
    seen_ui: set = set()
    for item in list(taste_ui) + list(prefetch_ui) + list(survey_ui):
        if item.get("type") != "tool_call":
            continue  # only show call bubbles in UI
        key = (item.get("name"), item.get("text"))
        if key in seen_ui:
            continue
        seen_ui.add(key)
        ui_tool_items.append(item)

    async def gen():
        global _inflight
        started = time.time()
        reply_parts: List[str] = []
        status = "ok"
        try:
            for item in ui_tool_items:
                frame, _ = _tool_msg(
                    "tool_call",
                    item.get("name") or "WebSearch",
                    item.get("text") or "",
                )
                if frame:
                    yield frame
            async with _sem:
                async for frame, text in stream_model(sys_p, prompt):
                    if not frame:
                        continue
                    if text:
                        reply_parts.append(text)
                    elif '"type": "error"' in frame or '"type":"error"' in frame:
                        status = "error"
                    yield frame
        finally:
            _inflight -= 1
            rec = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "ip": ip,
                "lang": lang,
                "status": status,
                "ms": int((time.time() - started) * 1000),
                "rag_chars": len(rag),
                "sys_chars": len(sys_p),
                "harness": HARNESS,
            }
            if LOG_FULL:
                rec["message"] = req.message
                rec["reply"] = "".join(reply_parts)
            await asyncio.to_thread(log_turn, rec)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8788"))
    uvicorn.run(app, host="0.0.0.0", port=port)
