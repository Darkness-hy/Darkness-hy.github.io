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
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
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
# Claude Code built-in tools (comma-separated). Default: none.
# Local file access is server-side only (taste.md / papers inject). Model tools:
# MCP web_search + web_fetch only — free multi-call like Claude Code.
# Omit native WebSearch/WebFetch (broken on DeepSeek Anthropic gateway).
# Set AGENT_CC_TOOLS=Read to re-enable local Read (not recommended on shared hosts).
_DEFAULT_CC_TOOLS = ""
CC_TOOLS = [
    t.strip()
    for t in os.environ.get("AGENT_CC_TOOLS", _DEFAULT_CC_TOOLS).split(",")
    if t.strip()
]
# Survey queries: optional server-side search inject. Default OFF — model must
# web_search live (no pre-baked "Web search results" answer block in system).
SURVEY_PREFETCH = os.environ.get("AGENT_SURVEY_PREFETCH", "0").lower() in (
    "1",
    "true",
    "yes",
    "on",
)
# Extra dirs for Read beyond knowledge/ (comma-separated absolute paths).
# Leave empty under the xixi isolation user.
CC_ADD_DIRS = [
    p.strip()
    for p in os.environ.get("AGENT_CC_ADD_DIRS", "").split(",")
    if p.strip()
]
# When no local CC tools, do not pass --add-dir (hardens FS exposure).
CC_ENABLE_ADD_DIR = os.environ.get("AGENT_CC_ADD_DIR", "auto").strip().lower()
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


# Named Hongyu papers → server Read of papers/<arxiv>/INDEX.md (with UI bubble).
# Order matters: longer / more specific aliases first (uni-lavira before lavira).
_PAPER_CATALOG: List[Tuple[str, Tuple[str, ...]]] = [
    ("2605.27582", ("uni-lavira", "unilavira", "uni lavira")),
    ("2510.19655", ("lavira",)),
    ("2603.18811", ("v-dreamer", "vdreamer", "v dreamer")),
    ("2312.04819", ("acorm",)),
    ("2307.08033", ("mfrs",)),
]
_PAPER_NAME_HINTS = tuple(
    alias
    for _, aliases in _PAPER_CATALOG
    for alias in aliases
) + ("paper", "arxiv", "论文", "summarize", "概括", "这篇")
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
    """Server Read of full taste.md with a visible Read UI bubble.

    System prompt only ever silent-injects taste.summary.md. Research taste /
    beliefs questions must show Read(knowledge/taste.md) then answer from it.
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
    max_chars = 14000
    if len(body) > max_chars:
        body = body[:max_chars] + "\n…[truncated]…"
    display = "knowledge/taste.md"
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
        f"## file: {display}\n{body}\n"
    )
    return ctx, ui


def _alias_hit(ql: str, ql_norm: str, alias: str) -> bool:
    """True if alias appears as its own token (uni-lavira ≠ lavira)."""
    a = (alias or "").lower().strip()
    if not a:
        return False
    # "lavira" must not match inside "uni-lavira"
    if a == "lavira" and re.search(r"uni[\s_\-]*lavira", ql):
        return False
    # flexible separators: uni-lavira / unilavira / uni lavira
    parts = re.split(r"[\s_\-]+", a)
    if len(parts) > 1:
        flex = r"[\s_\-]*".join(re.escape(p) for p in parts if p)
        if re.search(rf"(?<![a-z0-9]){flex}(?![a-z0-9])", ql):
            return True
        if re.sub(r"[\s_\-]+", "", a) in ql_norm:
            # only whole-token for collapsed form
            token = re.sub(r"[\s_\-]+", "", a)
            if re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", ql_norm):
                return True
        return False
    return bool(re.search(rf"(?<![a-z0-9]){re.escape(a)}(?![a-z0-9])", ql))


def _match_papers(message: str) -> List[str]:
    """Return arxiv ids mentioned / implied by the visitor message (max 2)."""
    ql = (message or "").lower()
    ql_norm = re.sub(r"[\s_\-]+", "", ql)
    found: List[str] = []
    for m in re.finditer(r"\b(\d{4}\.\d{4,5})\b", ql):
        aid = m.group(1)
        if (KNOWLEDGE_DIR / "papers" / aid / "INDEX.md").is_file() and aid not in found:
            found.append(aid)
    for arxiv_id, aliases in _PAPER_CATALOG:
        if arxiv_id in found:
            continue
        if any(_alias_hit(ql, ql_norm, a) for a in aliases):
            found.append(arxiv_id)
        if len(found) >= 2:
            break
    return found[:2]


def _paper_excerpt(raw: str, max_chars: int = 5500) -> str:
    """Keep title/abstract/intro signal; drop long LaTeX preamble when possible."""
    text = (raw or "").strip()
    if not text:
        return ""
    lines = text.splitlines()
    head = lines[0] if lines else ""
    # Prefer content after \begin{document}
    body = text
    m_doc = re.search(r"\\begin\{document\}", text, flags=re.I)
    if m_doc:
        body = text[m_doc.end() :]
    # Abstract environment
    m_abs = re.search(
        r"\\begin\{abstract\}(.*?)\\end\{abstract\}", body, flags=re.I | re.S
    )
    chunks: List[str] = []
    if head.startswith("#"):
        chunks.append(head)
    # title
    m_title = re.search(r"\\title\{(.*?)\}", body, flags=re.S)
    if m_title:
        title = re.sub(r"\s+", " ", m_title.group(1))
        title = re.sub(r"\\[a-zA-Z]+\*?\{?", " ", title)
        title = re.sub(r"[{}]", "", title).strip()
        if title:
            chunks.append(f"Title: {title[:240]}")
    if m_abs:
        abs_txt = re.sub(r"\\[a-zA-Z]+\*?\{?", " ", m_abs.group(1))
        abs_txt = re.sub(r"[{}$~]", " ", abs_txt)
        abs_txt = re.sub(r"\s+", " ", abs_txt).strip()
        if abs_txt:
            chunks.append(f"Abstract: {abs_txt[:1800]}")
    # First intro-ish paragraphs after abstract
    rest = body
    if m_abs:
        rest = body[m_abs.end() :]
    rest = re.sub(r"\\(section|subsection)\*?\{([^}]*)\}", r"\n## \2\n", rest)
    rest = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?\{?", " ", rest)
    rest = re.sub(r"[{}$~&%]", " ", rest)
    rest = re.sub(r"\s+", " ", rest).strip()
    if rest:
        chunks.append(rest[: max(800, max_chars - sum(len(c) for c in chunks))])
    out = "\n\n".join(chunks).strip()
    if len(out) > max_chars:
        out = out[:max_chars] + "\n…[truncated]…"
    if not out:
        out = text[:max_chars] + ("\n…[truncated]…" if len(text) > max_chars else "")
    return out


def paper_read_context(message: str) -> Tuple[str, List[dict]]:
    """Server-side Read of paper INDEX.md with a visible Read UI bubble.

    Local Read surfaces with UI: knowledge/taste.md and knowledge/papers/**.
    Returns (context, ui_tool_calls).
    """
    if _is_taste_skill_query(message):
        return "", []
    if _is_survey_query(message.lower()) and not _match_papers(message):
        return "", []
    ids = _match_papers(message)
    if not ids:
        return "", []

    blocks: List[str] = [
        "# Paper sources (server Read — answer from these INDEX excerpts; do not invent results)"
    ]
    ui: List[dict] = []
    for arxiv_id in ids:
        path = KNOWLEDGE_DIR / "papers" / arxiv_id / "INDEX.md"
        if not path.is_file():
            continue
        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        display = f"knowledge/papers/{arxiv_id}/INDEX.md"
        ui.append(
            {
                "type": "tool_call",
                "name": "Read",
                "text": f"Read({display})",
            }
        )
        excerpt = _paper_excerpt(raw, max_chars=5500)
        blocks.append(f"## {display}\n{excerpt}\n")
    if len(blocks) <= 1:
        return "", []
    return "\n".join(blocks), ui


def select_rag(query: str, budget: int = RAG_BUDGET) -> str:
    """Silent system-prompt RAG only: profile + taste.summary (never full taste.md).

    Papers / full taste.md use explicit Read bubbles (paper_read_context /
    taste_skill_context).
    """
    docs = _load_docs()
    if not docs:
        return ""

    ql = query.lower()
    survey = _is_survey_query(ql)
    taste_skill = _is_taste_skill_query(query)
    paper_ids = _match_papers(query)
    want_papers = bool(paper_ids) or (
        (not survey)
        and any(
            k in ql
            for k in ("paper", "arxiv", "论文", "publication", "发表", "work on", "研究什么")
        )
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

    # Open survey: no local RAG — web results are injected separately
    if survey and not paper_ids:
        return ""

    ordered: List[Tuple[str, str, float]] = []
    for doc_id, text in docs:
        if doc_id == "profile.md":
            score = 1e6
        elif doc_id == "taste.summary.md":
            # Always available as the only silent taste inject
            score = 1e5 if want_taste else 50.0
        elif doc_id == "taste.md":
            # Full skill only via taste_skill_context + Read bubble
            continue
        elif doc_id.startswith("papers/") or doc_id.endswith("INDEX.md"):
            # Papers only via paper_read_context (shows Read bubble)
            continue
        else:
            continue
        ordered.append((doc_id, text, score))

    ordered.sort(key=lambda x: x[2], reverse=True)

    parts: List[str] = []
    used = 0
    for doc_id, text, score in ordered:
        chunk = text.strip()
        if doc_id == "profile.md":
            # Shorter when a specific paper is already being Read
            per_cap = 600 if paper_ids else 1200
        elif doc_id == "taste.summary.md":
            per_cap = 900
        else:
            per_cap = 800
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
        # at most profile + taste.summary (papers / full taste are separate)
        if len(parts) >= 2:
            break
    if want_taste and not taste_skill:
        parts.append(
            "### note\nTaste summary is above. For research taste / beliefs, "
            "Read knowledge/taste.md (full skill).\n"
        )
    if want_papers and not paper_ids:
        parts.append(
            "### note\nFor a specific paper, visitor should name it "
            "(Uni-LaViRA / LaViRA / V-Dreamer / ACORM / MFRS); then Read that INDEX.md.\n"
        )
    return "\n".join(parts)


def _knowledge_map() -> str:
    """Tool map aligned with Claude Code free multi-tool use (MCP web only)."""
    papers_dir = KNOWLEDGE_DIR / "papers"
    paper_ids: List[str] = []
    if papers_dir.exists():
        paper_ids = sorted(d.name for d in papers_dir.iterdir() if d.is_dir())
    catalog = ", ".join(
        f"{aliases[0]}→{aid}" for aid, aliases in _PAPER_CATALOG
    )
    lines = [
        "Tools (use freely, multiple times, like Claude Code — no artificial call limit):",
        "- web_search — Wikipedia + arXiv + OpenAlex + Crossref "
        "(+ optional Brave/Serper/SearXNG). Call again with refined queries anytime.",
        "- web_fetch — open a specific URL/paper page for more text.",
        "Local files are NOT model-Read (server injects when needed):",
        "- profile + taste.summary may appear as system excerpts (do not claim you Read them).",
        "- Research taste / beliefs → server already Read knowledge/taste.md into context.",
        f"- Named paper → server already Read knowledge/papers/<id>/INDEX.md "
        f"(ids: {', '.join(paper_ids)}; aliases: {catalog}).",
        "No Bash / Edit / Glob / Grep / local filesystem tools. Do not invent citations.",
    ]
    return "\n".join(lines)


def system_prompt(
    lang: str,
    rag: str,
    extra_context: Optional[str],
    *,
    survey: bool = False,
    taste_skill: bool = False,
    paper_read: bool = False,
) -> str:
    """Minimal persona + tool map; light RAG; survey uses web_search."""
    if lang == "zh":
        lines = [
            "你是 Hongyu Ding 个人主页上的 AI 研究助手（内部名茜茜/Cici，勿默认说出）。",
            "【名字】仅当访客明确问「你是谁 / 你叫什么 / 你的名字 / who are you / your name」时，"
            "才简短自称「茜茜」或 Cici（例如：我是茜茜，Hongyu 主页上的 AI 助手）。"
            "其他任何时候禁止出现「茜茜」「Cici」、禁止自我介绍开场。",
            "【模型/技术栈】无论是否被问，都不要提底层模型名、厂商、服务器、agent、部署方式。"
            "若被问「什么模型」：只答「我是这个主页上的 AI 助手」，到此为止。"
            "禁止声称自己是 Claude / GPT / Anthropic / OpenAI 产品。",
            "【强制精简】默认 2–4 句 / ≤80 汉字；先结论。禁止长文、多级分点、领域综述式铺陈。"
            "访客说「详细/展开」才可加长。最多 1 个 emoji。不编造。本轮简体中文。",
            "【工具】可自由多次调用 web_search / web_fetch；"
            "调研/未知论文/公开领域问题必须先 web_search 再答，答案只能基于本轮工具结果与对话，"
            "不要背诵预设稿或未检索的固定段落。"
            "可讨论任何公开论文，不限于 Hongyu 的工作。"
            "本地无文件系统工具；Hongyu 论文/taste 仅在服务端注入时使用。"
            "禁止说没有搜索工具。",
        ]
    else:
        lines = [
            "You are the AI research assistant on Hongyu Ding's homepage "
            "(internal name Cici/茜茜 — do not use unless asked).",
            "NAME: Only if the visitor clearly asks who you are / your name / who are you, "
            "briefly say you are Cici (茜茜), the homepage AI assistant. "
            "Otherwise never say Cici/茜茜 and never self-introduce.",
            "MODEL / INFRA: Never mention model names, vendors, servers, or agent hosting — "
            "even if asked. If asked which model: only say you are the homepage AI assistant. "
            "Never claim to be Claude / GPT / Anthropic / OpenAI.",
            "Conciseness mandatory: 2–4 short sentences / ~60 words default. Lead with the answer. "
            "No long essays or multi-level bullet dumps unless the visitor asks for detail. ≤1 emoji. English this turn.",
            "TOOLS: freely call web_search / web_fetch (multiple times OK). "
            "For surveys, unknown papers, or open-web topics, you MUST web_search first; "
            "answer only from this turn's tool results and the conversation — "
            "no canned/prewritten blurbs. "
            "You may discuss any public research (not only Hongyu's papers). "
            "No local filesystem tools — Hongyu paper/taste files are server-injected only when relevant. "
            "Never claim search is unavailable.",
        ]
    if taste_skill:
        if lang == "zh":
            lines.append(
                "【本轮=research taste / 信念】服务端已注入完整 taste.md skill。"
                "system 里只有 taste 摘要；必须以完整 skill 回答：insight 标准、判断启发式、写作偏好；"
                "2–5 句，先结论。禁止编造项目名/论文名/工具名。本轮不必 web_search。"
            )
        else:
            lines.append(
                "TASTE SKILL TURN: full taste.md skill is already in context (server Read). "
                "System only has the short summary; answer from the full skill: insight standards, "
                "judgment heuristics, writing taste. 2–5 sentences. No invented project/paper names. "
                "No web_search needed this turn."
            )
    elif paper_read:
        if lang == "zh":
            lines.append(
                "【本轮=论文】上下文已有 Paper sources（INDEX 摘录）。"
                "用 1 段 / 2–4 句概括；不要编造实验数字。一般无需再搜；缺公开页可用 web_fetch。"
            )
        else:
            lines.append(
                "PAPER TURN: Paper sources are already in context. "
                "Summarize in one short paragraph / 2–4 sentences. Do not invent numbers. "
                "Usually no search needed; web_fetch a public project page only if useful."
            )
    elif survey:
        if lang == "zh":
            lines.append(
                "【本轮=领域调研】必须先 web_search（可再 web_fetch），再根据工具结果用 2–4 句回答"
                "（定义、趋势、1 个开放问题）。禁止不经搜索就直接写综述。"
                "Hongyu 相关最多半句。不要使用本地论文文件。"
            )
        else:
            lines.append(
                "FIELD SURVEY: You MUST web_search first (web_fetch if needed), then answer in "
                "2–4 sentences (definition, trends, one open problem) from tool results only. "
                "Do not write a canned survey without searching. "
                "At most half a sentence on Hongyu. No local paper files."
            )
    else:
        lines.append(_knowledge_map())
    if rag and not survey:
        # Silent inject only: profile + taste.summary (never full taste.md / papers)
        lines.append(
            "System excerpts (profile + taste.summary only — do NOT show/claim Read for these):\n"
            + rag
        )
    # taste.md full skill ~10k; paper excerpts ~6k each (via extra_context after Read)
    extra_cap = URL_PREFETCH_CHARS * URL_PREFETCH_MAX + 2000
    if taste_skill:
        extra_cap += 16000
    if paper_read:
        extra_cap += 12000
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


def _survey_query(message: str) -> str:
    """Compact English query for multi_search (shared by UI bubble + prefetch)."""
    q = re.sub(r"\s+", " ", (message or "")).strip()
    query = q
    if re.search(r"[A-Za-z]{3,}", q):
        latin = " ".join(re.findall(r"[A-Za-z][A-Za-z0-9\-_/]+", q))
        if latin:
            query = f"{latin} robotics"
    ql = q.lower()
    if "mobile" in ql and "manipulation" in ql:
        query = "mobile manipulation robotics"
    elif "操控" in q and ("移动" in q or "mobile" in ql):
        query = "mobile manipulation robotics"
    return query


def survey_search_context(message: str) -> Tuple[str, List[dict]]:
    """Server-side multi-source search for field-survey questions.

    Sources: Wikipedia + arXiv + OpenAlex + Crossref (budget-capped multi_search).
    Returns (context_for_model, ui_tool_bubbles). Avoids broken native WebSearch.
    """
    if not SURVEY_PREFETCH or not _is_survey_query(message.lower()):
        return "", []
    query = _survey_query(message)

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
    t0 = time.time()
    hits = multi_search(query, max_results=6)
    logger.info(
        "survey multi_search q=%r hits=%d ms=%d",
        query,
        len(hits),
        int((time.time() - t0) * 1000),
    )
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
        "# Web search results (multi-source: Wikipedia + arXiv + OpenAlex + Crossref "
        "[+ optional Brave/Serper/SearXNG] — use freely; may web_search again)",
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
    """Append metadata-only chat log. Never write secrets or full tool dumps.

    LOG_FULL=1 adds truncated message/reply only (still no env / API keys).
    """
    if not LOG_DIR:
        return
    # Hard strip any accidental secret-looking fields
    safe = {k: v for k, v in rec.items() if k.lower() not in {
        "api_key", "authorization", "deepseek_api_key", "anthropic_api_key",
        "env", "system_prompt", "sys_prompt", "tool_result", "raw",
    }}
    if not LOG_FULL:
        safe.pop("message", None)
        safe.pop("reply", None)
    else:
        # Cap full-mode payloads
        if isinstance(safe.get("message"), str) and len(safe["message"]) > 500:
            safe["message"] = safe["message"][:500] + "…"
        if isinstance(safe.get("reply"), str) and len(safe["reply"]) > 800:
            safe["reply"] = safe["reply"][:800] + "…"
    try:
        Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with open(Path(LOG_DIR) / f"chat-{day}.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(safe, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _proc(kind: str, text: str, **extra) -> Tuple[str, str]:
    """SSE process/status event (not counted as answer text)."""
    if not STREAM_PROCESS or not text:
        return "", ""
    obj = {"type": kind, "text": text}
    obj.update(extra)
    return sse(obj), ""


def _suppress_tool_ui(name: str, summary: str) -> bool:
    """Hide tool bubbles that violate allow-list or re-read system files.

    Local Read may only surface taste.md and papers/** in the UI.
    profile.md / taste.summary.md live in system prompt — never show Read.
    """
    short = (name or "").strip()
    if short.startswith("mcp__"):
        short = short.split("__")[-1]
    s = (summary or "").lower()
    if short in ("Read", "read"):
        if "profile.md" in s or "taste.summary" in s:
            return True
        if "papers/" in s or "taste.md" in s:
            return False
        # unknown / disallowed path — hide
        return True
    if short in ("Glob", "Grep", "glob", "grep"):
        return True
    return False


def _tool_msg(kind: str, name: str, body: str, **extra) -> Tuple[str, str]:
    """Chat-facing tool call / tool result (frontend shows as its own bubble).

    Always emitted (not gated by STREAM_PROCESS) so the UI can render separate turns.
    Keep `text` compact (CC-style); put long dumps only in model context.
    """
    if kind == "tool_call" and _suppress_tool_ui(name, body):
        return "", ""
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
            # Headless allow-list. Local FS tools only if CC_TOOLS includes them.
            "allow": (
                [
                    *(
                        [f"{t}(*)" for t in CC_TOOLS if t in ("Read", "Glob", "Grep")]
                    ),
                    "mcp__websearch__web_search",
                    "mcp__websearch__web_fetch",
                    "mcp__websearch__*",
                ]
            ),
            "deny": [
                "Bash(*)",
                "Edit(*)",
                "Write(*)",
                "MultiEdit(*)",
                "NotebookEdit(*)",
                # Hard-deny local discovery unless explicitly re-enabled in CC_TOOLS
                *(
                    []
                    if "Glob" in CC_TOOLS
                    else ["Glob(*)"]
                ),
                *(
                    []
                    if "Grep" in CC_TOOLS
                    else ["Grep(*)"]
                ),
                *(
                    []
                    if "Read" in CC_TOOLS
                    else ["Read(*)"]
                ),
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
    # Built-in tools: only those in CC_TOOLS (default empty).
    # MCP web_search / web_fetch always available via mcp-config.
    # Local knowledge is server-injected — no --add-dir by default.
    tools = list(CC_TOOLS)
    enable_add = CC_ENABLE_ADD_DIR
    if enable_add == "auto":
        enable_add_dir = bool(tools) or bool(CC_ADD_DIRS)
    else:
        enable_add_dir = enable_add not in ("0", "false", "no", "off")
    add_dirs: List[str] = []
    if enable_add_dir:
        add_dirs.append(str(KNOWLEDGE_DIR.resolve()))
        for d in CC_ADD_DIRS:
            p = Path(d)
            if p.exists():
                add_dirs.append(str(p.resolve()))
        seen: set = set()
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
        "--dangerously-skip-permissions",
        "--system-prompt",
        sys_prompt,  # full replace of default system prompt
        "--output-format",
        "stream-json",
        "--verbose",
        "--include-partial-messages",
        "--no-session-persistence",
    ]
    # Empty --tools can error; omit flag when no built-ins (MCP still works).
    if tools:
        cmd.extend(["--tools", *tools])
    else:
        cmd.extend(["--tools", ""])  # explicit none; MCP tools still from mcp-config
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

# OpenAI-compatible tool schemas (same capabilities as MCP websearch).
_HTTP_TOOLS: List[dict] = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Free web+academic search (ddgs metasearch + arXiv/OpenAlex/Crossref/Wikipedia). "
                "Use for unknown papers, field facts, SOTA. Call freely, multiple times."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Concise English search query",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "1-8 results (default 6)",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": "Fetch a public URL as readable text (HTML stripped).",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "http(s) URL"},
                    "max_chars": {"type": "integer", "description": "Max chars (default 8000)"},
                },
                "required": ["url"],
            },
        },
    },
]
HTTP_TOOL_ROUNDS = int(os.environ.get("AGENT_HTTP_TOOL_ROUNDS", "3"))


def _search_relevance(query: str, title: str) -> int:
    """Overlap score between query and a result title (higher = better).

    Method names like AGiLe in the title are a strong hit (score >= 10).
    If the query has such a name and the title lacks it → score 0.
    """
    q = query or ""
    t = (title or "").lower()
    # Mixed-case / camel-ish method names (AGiLe, LaViRA, Uni-LaViRA, …)
    mixed = re.findall(r"\b[A-Za-z]*[A-Z][a-z]+[A-Z][A-Za-z0-9\-]*\b", q)
    mixed += re.findall(r"\b[A-Z]{2,}[a-z]+\b", q)
    # Also bare tokens that look like product names in quotes or leading
    mixed = list(dict.fromkeys(mixed))
    if mixed:
        hit_any = False
        for m in mixed:
            ml = m.lower().replace("-", "")
            tl = t.replace("-", "")
            if ml in tl or m.lower() in t:
                hit_any = True
                break
        if not hit_any:
            return 0
        # Strong positive: method name present
        base = 10
    else:
        base = 0
    q_toks = set(re.findall(r"[A-Za-z0-9]{4,}", q.lower()))
    stop = {
        "the", "and", "for", "via", "with", "from", "into", "using", "learning",
        "robust", "paper", "arxiv", "robot", "robotic", "robots", "based",
        "that", "this", "what", "about",
    }
    q_toks = {tok for tok in q_toks if tok not in stop}
    return base + sum(1 for tok in q_toks if tok in t)


def _exec_http_tool(name: str, arguments: str) -> Tuple[str, str, str, int]:
    """Run web_search / web_fetch.

    Returns (ui_call_line, ui_result_line, tool_content, hit_count).
    hit_count is *relevant* search hits (0 for fetch/error/unrelated noise).
    """
    try:
        args = json.loads(arguments or "{}")
        if not isinstance(args, dict):
            args = {}
    except json.JSONDecodeError:
        args = {}
    short = (name or "").split("__")[-1]

    if short in ("web_search", "WebSearch"):
        q = str(args.get("query") or args.get("q") or "").strip()
        n = int(args.get("max_results") or 6)
        call = f"WebSearch({q})" if q else "WebSearch()"
        try:
            from mcp_websearch import multi_search  # type: ignore

            hits = multi_search(q, max_results=n) if q else []
        except Exception as e:
            content = json.dumps({"error": str(e)[:200]}, ensure_ascii=False)
            return call, "⎿  search error", content, 0
        ok = [h for h in hits if h.get("title") != "search_empty"]
        # Keep only titles that share distinctive tokens with the query
        # (avoids "6 unrelated papers" looking like a successful find)
        scored = []
        for h in ok:
            sc = _search_relevance(q, str(h.get("title") or ""))
            scored.append((sc, h))
        scored.sort(key=lambda x: x[0], reverse=True)
        # Method-name hits score >= 10; else need modest token overlap
        has_method = bool(
            re.findall(r"\b[A-Za-z]*[A-Z][a-z]+[A-Z][A-Za-z0-9\-]*\b", q)
            or re.findall(r"\b[A-Z]{2,}[a-z]+\b", q)
        )
        min_score = 10 if has_method else (2 if len(q.split()) >= 4 else 1)
        relevant = [h for sc, h in scored if sc >= min_score]
        lines = []
        for h in (relevant or ok)[:8]:
            lines.append(
                f"- [{h.get('source')}] {h.get('title')}\n  {h.get('url')}\n  {h.get('snippet') or ''}"
            )
        if not ok:
            content = (
                "No results found in Wikipedia/arXiv/OpenAlex/Crossref. "
                "The paper may be unpublished, mis-titled, or not yet indexed. "
                "Do NOT invent details. Ask for arXiv ID or URL."
            )
            return call, "⎿  0 results (not indexed)", content, 0
        if not relevant:
            content = (
                "Search returned items, but NONE match the query title closely "
                f"(query={q!r}). Treat as NOT FOUND. Do not attribute unrelated papers "
                "to this name. Stop searching after one more focused try at most; "
                "then ask for arXiv id/URL.\n\nTop unrelated hits:\n"
                + "\n".join(lines[:4])
            )
            titles = " · ".join((h.get("title") or "")[:36] for h in ok[:2])
            return (
                call,
                f"⎿  0 relevant (noise: {titles})"[:400],
                content,
                0,
            )
        content = "\n".join(lines)
        titles = " · ".join((h.get("title") or "")[:40] for h in relevant[:3])
        result = f"⎿  {len(relevant)} results" + (f" · {titles}" if titles else "")
        return call, result[:400], content, len(relevant)

    if short in ("web_fetch", "WebFetch"):
        url = str(args.get("url") or "").strip()
        max_chars = int(args.get("max_chars") or 8000)
        call = f"WebFetch({url})" if url else "WebFetch()"
        try:
            from mcp_websearch import web_fetch  # type: ignore

            payload = web_fetch(url, max_chars=max_chars)
        except Exception as e:
            payload = {"ok": False, "error": str(e)[:200], "url": url}
        if payload.get("ok"):
            text = str(payload.get("text") or "")
            result = f"⎿  {payload.get('status', '')} · {len(text)} chars"
            return call, result, text[:12000], 1
        result = f"⎿  error · {payload.get('error', '')}"[:200]
        return call, result, json.dumps(payload, ensure_ascii=False), 0

    return (
        f"{short}()",
        "⎿  unknown tool",
        json.dumps({"error": f"unknown tool {name}"}),
        0,
    )


async def _stream_openai_round(
    client: httpx.AsyncClient,
    url: str,
    headers: dict,
    payload: dict,
    *,
    thinking_on: bool,
) -> AsyncIterator[Tuple[str, Any]]:
    """Stream one chat.completions round. Yields ('delta'|'thinking'|'tool_calls'|'error', value)."""
    payload = {**payload, "stream": True}
    content_parts: List[str] = []
    # tool_calls assembled by index from streaming deltas
    tc_acc: Dict[int, dict] = {}
    finish_reason: Optional[str] = None

    async with client.stream("POST", url, headers=headers, json=payload) as resp:
        if resp.status_code >= 400:
            detail = (await resp.aread()).decode("utf-8", "replace")[:1000]
            logger.error("http stream error %s: %s", resp.status_code, detail)
            yield "error", "助理暂时不可用,请稍后再试"
            return
        async for line in resp.aiter_lines():
            line = (line or "").strip()
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
            ch0 = choices[0]
            fr = ch0.get("finish_reason")
            if fr:
                finish_reason = fr
            delta = ch0.get("delta") or {}
            if thinking_on:
                for key in ("reasoning_content", "reasoning", "thinking"):
                    r = delta.get(key)
                    if isinstance(r, str) and r:
                        yield "thinking", r
            text = delta.get("content")
            if isinstance(text, str) and text:
                content_parts.append(text)
                yield "delta", text
            # Streaming tool_calls (OpenAI style)
            for tc in delta.get("tool_calls") or []:
                if not isinstance(tc, dict):
                    continue
                idx = int(tc.get("index") or 0)
                slot = tc_acc.setdefault(
                    idx,
                    {
                        "id": "",
                        "type": "function",
                        "function": {"name": "", "arguments": ""},
                    },
                )
                if tc.get("id"):
                    slot["id"] = tc["id"]
                if tc.get("type"):
                    slot["type"] = tc["type"]
                fn = tc.get("function") or {}
                if fn.get("name"):
                    slot["function"]["name"] = (
                        slot["function"].get("name") or ""
                    ) + str(fn.get("name") or "")
                if fn.get("arguments"):
                    slot["function"]["arguments"] = (
                        slot["function"].get("arguments") or ""
                    ) + str(fn.get("arguments") or "")

    tool_calls = [tc_acc[i] for i in sorted(tc_acc.keys())] if tc_acc else []
    # Drop empty tool shells
    tool_calls = [
        t
        for t in tool_calls
        if (t.get("function") or {}).get("name")
        or (t.get("function") or {}).get("arguments")
    ]
    yield "round_done", {
        "content": "".join(content_parts),
        "tool_calls": tool_calls,
        "finish_reason": finish_reason,
    }


async def stream_http(sys_prompt: str, prompt: str) -> AsyncIterator[Tuple[str, str]]:
    """DeepSeek HTTP path with true token streaming + tool loop (no CC cold start).

    Every intermediate text token is yielded as delta; tool_call / tool_result are
    emitted between segments with text_break so the UI builds a CC-like timeline.
    """
    if not DEEPSEEK_KEY:
        yield sse({"type": "error", "message": "助理服务缺少模型 API Key"}), ""
        return

    frame, _ = _proc("status", f"DeepSeek · {MODEL}")
    if frame:
        yield frame, ""

    thinking_on = THINKING not in ("0", "false", "no", "off", "disabled", "")
    # Nudge: stop thrashing empty searches; stream answers; open literature OK
    sys_extra = (
        "\nWhen web_search returns 0 relevant hits twice, stop searching and say so briefly "
        "(ask for arXiv id/URL). Do not invent paper claims. Prefer 1–2 focused searches. "
        "Do not volunteer your name. Do not mention model names or servers."
    )
    messages: List[dict] = [
        {"role": "system", "content": sys_prompt + sys_extra},
        {"role": "user", "content": prompt},
    ]
    url = f"{OPENAI_BASE_URL}/chat/completions"
    timeout = httpx.Timeout(connect=15.0, read=float(TIMEOUT), write=15.0, pool=15.0)
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_KEY}",
        "Content-Type": "application/json",
    }
    got_text = False
    open_text_segment = False
    empty_search_streak = 0

    def _close_text_segment() -> Optional[str]:
        nonlocal open_text_segment
        if open_text_segment:
            open_text_segment = False
            return sse({"type": "text_break"})
        return None

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            for round_i in range(max(1, HTTP_TOOL_ROUNDS)):
                force_final = empty_search_streak >= 2 or round_i == HTTP_TOOL_ROUNDS - 1
                payload: dict = {
                    "model": MODEL,
                    "messages": messages,
                    "temperature": TEMPERATURE,
                }
                if not force_final:
                    payload["tools"] = _HTTP_TOOLS
                    payload["tool_choice"] = "auto"
                if thinking_on:
                    payload["thinking"] = {"type": "enabled"}
                else:
                    payload["thinking"] = {"type": "disabled"}
                if force_final:
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                "Give a short final answer NOW as plain text only. "
                                "Do not emit tool XML/tags. If the paper was not found in indexes, "
                                "say so and ask for an arXiv id or URL."
                            ),
                        }
                    )

                content = ""
                tool_calls: List[dict] = []
                async for kind, val in _stream_openai_round(
                    client, url, headers, payload, thinking_on=thinking_on
                ):
                    if kind == "error":
                        yield sse({"type": "error", "message": str(val)}), ""
                        return
                    if kind == "thinking":
                        frame, _ = _proc("thinking", str(val))
                        if frame:
                            yield frame, ""
                    elif kind == "delta":
                        text = str(val)
                        if text:
                            got_text = True
                            open_text_segment = True
                            yield sse({"type": "delta", "text": text}), text
                    elif kind == "round_done":
                        content = str((val or {}).get("content") or "")
                        tool_calls = list((val or {}).get("tool_calls") or [])

                if not tool_calls or force_final:
                    br = _close_text_segment()
                    if br:
                        yield br, ""
                    break

                # Tool phase: close text bubble first
                br = _close_text_segment()
                if br:
                    yield br, ""

                messages.append(
                    {
                        "role": "assistant",
                        "content": content if content else None,
                        "tool_calls": tool_calls,
                    }
                )

                round_hits = 0
                for tc in tool_calls:
                    if not isinstance(tc, dict):
                        continue
                    fn = tc.get("function") or {}
                    name = str(fn.get("name") or "tool")
                    raw_args = fn.get("arguments") or "{}"
                    if not isinstance(raw_args, str):
                        raw_args = json.dumps(raw_args, ensure_ascii=False)
                    tid = str(tc.get("id") or "")
                    call_line, result_line, tool_body, hits = await asyncio.to_thread(
                        _exec_http_tool, name, raw_args
                    )
                    round_hits += hits
                    frame, _ = _tool_msg("tool_call", name, call_line)
                    if frame:
                        yield frame, ""
                    # Do not stream verbose tool_result previews to the UI
                    # (model still receives full tool_body in messages).
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tid,
                            "content": tool_body[:12000],
                        }
                    )

                if round_hits == 0:
                    empty_search_streak += 1
                else:
                    empty_search_streak = 0

        br = _close_text_segment()
        if br:
            yield br, ""
        if got_text:
            yield sse({"type": "done", "path": "http-tools"}), ""
        else:
            yield sse({"type": "error", "message": "助理暂时没有返回内容,请重试"}), ""
    except httpx.TimeoutException:
        yield sse({"type": "error", "message": "响应超时,请重试"}), ""
    except httpx.HTTPError as e:
        logger.error("http chat failed: %s", e)
        yield sse({"type": "error", "message": "助理暂时不可用,请稍后再试"}), ""


async def stream_model(sys_prompt: str, prompt: str) -> AsyncIterator[Tuple[str, str]]:
    """Route harness. Default: HTTP+tools (no per-request Claude Code cold start).

    AGENT_HARNESS:
      - http / openai / deepseek / auto  → HTTP tool loop (fast)
      - claude-code / claude             → headless Claude Code (slower cold start)
    """
    mode = HARNESS
    # Prefer HTTP tool loop — eliminates claude process spawn (~5–10s)
    if mode in ("http", "openai", "deepseek", "auto", ""):
        async for item in stream_http(sys_prompt, prompt):
            yield item
        return

    if mode in ("claude-code", "claude"):
        try:
            async for item in stream_claude(sys_prompt, prompt):
                yield item
            return
        except RuntimeError as e:
            logger.warning("claude harness failed (%s); falling back to HTTP tools", e)
            frame, _ = _proc("status", f"fallback → HTTP ({e})")
            if frame:
                yield frame, ""
            if os.environ.get("AGENT_NO_HTTP_FALLBACK", "").lower() in (
                "1",
                "true",
                "yes",
            ):
                yield sse({"type": "error", "message": "助理暂时不可用,请稍后再试"}), ""
                return
            async for item in stream_http(sys_prompt, prompt):
                yield item
            return

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



# Optional: serve latest frontend assets (bypass stale GitHub Pages cache during deploy lag)
_FRONTEND_ROOT = Path(os.environ.get(
    "AGENT_FRONTEND_ROOT",
    str(ROOT.parent),  # Darkness-hy.github.io/
))

@app.get("/frontend/tutor.js")
async def frontend_tutor_js():
    path = _FRONTEND_ROOT / "assets" / "js" / "tutor.js"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="tutor.js missing")
    return FileResponse(
        path,
        media_type="application/javascript",
        headers={"Cache-Control": "no-store"},
    )

@app.get("/frontend/tutor.css")
async def frontend_tutor_css():
    path = _FRONTEND_ROOT / "assets" / "css" / "tutor.css"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="tutor.css missing")
    return FileResponse(
        path,
        media_type="text/css",
        headers={"Cache-Control": "no-store"},
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
    # Paths are mutually exclusive priority: taste > paper > survey
    if taste_skill:
        survey = False
    paper_ctx, paper_ui = (
        ("", []) if taste_skill else paper_read_context(req.message)
    )
    paper_read = bool(paper_ui)
    if paper_read:
        survey = False

    # Kick off multi_search immediately so it overlaps local RAG / URL work.
    # Hard wait budget inside gen() — never block response open on slow sources.
    need_survey = bool(SURVEY_PREFETCH and survey and not taste_skill and not paper_read)
    survey_task: Optional[asyncio.Task] = None
    survey_q = _survey_query(req.message) if need_survey else ""
    if need_survey:
        survey_task = asyncio.create_task(
            asyncio.to_thread(survey_search_context, req.message)
        )

    rag = select_rag(req.message)
    # Reliable URL access: server pre-fetches links in the question
    fetched, prefetch_ui = await prefetch_urls(req.message)
    # Full taste.md via Read bubble (system only has taste.summary)
    taste_ctx, taste_ui = taste_skill_context(req.message)

    # Base extra without survey (survey injected after wait in gen)
    base_extra_bits = [x for x in (req.context, fetched, taste_ctx, paper_ctx) if x]
    prompt = user_prompt(req.message, req.history)

    # UI bubbles for local/server reads (survey bubble emitted in gen ASAP)
    ui_tool_items: List[dict] = []
    seen_ui: set = set()
    for item in list(paper_ui) + list(taste_ui) + list(prefetch_ui):
        if item.get("type") != "tool_call":
            continue
        key = (item.get("name"), item.get("text"))
        if key in seen_ui:
            continue
        seen_ui.add(key)
        ui_tool_items.append(item)

    # Survey wait budget: slightly above multi_search budget
    survey_wait_s = float(os.environ.get("AGENT_SURVEY_WAIT_S", "3.2"))

    async def gen():
        global _inflight
        started = time.time()
        reply_parts: List[str] = []
        status = "ok"
        survey_ctx = ""
        survey_ms = 0
        sys_p = ""
        try:
            # 1) Instant UI feedback (Read bubbles) — do not wait on web
            for item in ui_tool_items:
                frame, _ = _tool_msg(
                    "tool_call",
                    item.get("name") or "WebSearch",
                    item.get("text") or "",
                )
                if frame:
                    yield frame

            # 2) Survey: show WebSearch bubble immediately, then await budget-capped search
            if survey_task is not None:
                frame, _ = _tool_msg(
                    "tool_call",
                    "WebSearch",
                    f"WebSearch({survey_q})",
                )
                if frame:
                    yield frame
                t_s = time.time()
                try:
                    survey_ctx, _survey_ui = await asyncio.wait_for(
                        survey_task, timeout=survey_wait_s
                    )
                except asyncio.TimeoutError:
                    logger.warning(
                        "survey search timed out after %.1fs q=%r",
                        survey_wait_s,
                        survey_q,
                    )
                    survey_ctx = ""
                    if not survey_task.done():
                        survey_task.cancel()
                except Exception as e:
                    logger.warning("survey search failed: %s", e)
                    survey_ctx = ""
                survey_ms = int((time.time() - t_s) * 1000)

            extra_bits = list(base_extra_bits)
            if survey_ctx:
                extra_bits.append(survey_ctx)
            extra = "\n\n".join(extra_bits) if extra_bits else None
            sys_p = system_prompt(
                lang,
                rag,
                extra,
                survey=survey,
                taste_skill=taste_skill,
                paper_read=paper_read,
            )

            # 3) Model stream
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
            # Metadata-only by default (no full prompt/tools/secrets).
            rec = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "ip": ip,
                "lang": lang,
                "status": status,
                "ms": int((time.time() - started) * 1000),
                "rag_chars": len(rag),
                "sys_chars": len(sys_p) if sys_p else 0,
                "reply_chars": len("".join(reply_parts)),
                "msg_chars": len(req.message or ""),
                "harness": HARNESS,
                "taste_skill": taste_skill,
                "paper_read": paper_read,
                "survey": survey,
                "survey_ms": survey_ms,
            }
            if LOG_FULL:
                rec["message"] = req.message
                rec["reply"] = "".join(reply_parts)
            await asyncio.to_thread(log_turn, rec)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",  # disable nginx/caddy response buffering
            "Connection": "keep-alive",
        },
    )


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8788"))
    uvicorn.run(app, host="0.0.0.0", port=port)
