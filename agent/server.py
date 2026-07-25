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
CLAUDE_TIMEOUT = int(os.environ.get("AGENT_CLAUDE_TIMEOUT", "12"))
# Abort Claude Code after this many api_retry events (DeepSeek 502 storms).
CLAUDE_MAX_RETRIES = int(os.environ.get("AGENT_CLAUDE_MAX_RETRIES", "2"))
MAX_CONCURRENCY = int(os.environ.get("AGENT_MAX_CONCURRENCY", "3"))
MAX_QUEUE = int(os.environ.get("AGENT_MAX_QUEUE", "15"))
RATE_PER_MIN = int(os.environ.get("AGENT_RATE_PER_MIN", "20"))
RATE_GLOBAL_PER_MIN = int(os.environ.get("AGENT_RATE_GLOBAL_PER_MIN", "60"))
TRUST_PROXY = os.environ.get("AGENT_TRUST_PROXY", "1").lower() not in ("0", "false", "no", "")
BEARER = os.environ.get("AGENT_BEARER", os.environ.get("TUTOR_BEARER", ""))
LOG_DIR = os.environ.get("AGENT_LOG_DIR", str(ROOT / "logs"))
LOG_FULL = os.environ.get("AGENT_LOG_FULL", "0").lower() not in ("0", "false", "no", "")
RAG_BUDGET = int(os.environ.get("AGENT_RAG_BUDGET", "5500"))
TEMPERATURE = float(os.environ.get("AGENT_TEMPERATURE", "0.3"))
THINKING = os.environ.get("AGENT_THINKING", "disabled").strip().lower()
# Stream intermediate process events (status/thinking/tool) to the browser.
STREAM_PROCESS = os.environ.get("AGENT_STREAM_PROCESS", "1").lower() not in ("0", "false", "no", "")
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

    for name in ("profile.md", "taste.md"):
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


_PAPER_HINTS = (
    "uni-lavira",
    "lavira",
    "v-dreamer",
    "vdreamer",
    "acorm",
    "mfrs",
    "paper",
    "arxiv",
    "navigation",
    "reward",
    "marl",
    "robot",
    "embodied",
    "论文",
    "导航",
)


def select_rag(query: str, budget: int = RAG_BUDGET) -> str:
    """Compact RAG: pin short profile/taste; papers only when query needs them."""
    docs = _load_docs()
    if not docs:
        return ""

    q = _tokens(query)
    ql = query.lower()
    want_papers = any(kw in ql for kw in _PAPER_HINTS) or any(
        t in q for t in ("paper", "arxiv", "lavira", "mfrs", "acorm", "dreamer")
    )
    want_taste = any(
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

    ordered: List[Tuple[str, str, float]] = []
    for doc_id, text in docs:
        if doc_id == "profile.md":
            score = 1e6
        elif doc_id == "taste.md":
            score = 1e5 if want_taste or not want_papers else 50.0
        else:
            if not want_papers:
                continue
            dt = _tokens(text[:6000])
            overlap = len(q & dt) if q else 0
            boost = 0.0
            for kw in _PAPER_HINTS:
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
            per_cap = 1600
        elif doc_id == "taste.md":
            per_cap = 2200 if want_taste else 1200
        elif doc_id.endswith("INDEX.md"):
            per_cap = 2800
        else:
            per_cap = 1800
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
        # at most profile + taste + 2 papers
        if len(parts) >= (4 if want_papers else 2):
            break
    return "\n".join(parts)


def system_prompt(lang: str, rag: str, extra_context: Optional[str]) -> str:
    """Minimal persona — short system; knowledge appended tightly (no Claude boilerplate)."""
    if lang == "zh":
        lines = [
            "你是 Hongyu Ding 个人主页 AI 助理「茜茜」。勿主动报名字；被问到才说。",
            "专业、简洁、友好；每条最多 1 个 emoji。只依据资料回答，不编造。不确定就说不确定。",
            "先结论后展开；本轮用简体中文。",
        ]
    else:
        lines = [
            "You are Cici (茜茜), the AI assistant on Hongyu Ding's homepage. Name yourself only if asked.",
            "Be clear, concise, friendly; at most one emoji. Answer only from materials; never invent facts. If unsure, say so.",
            "Lead with the answer. Use English this turn.",
        ]
    if rag:
        # Keep knowledge tight to cut prefill latency.
        lines.append("Materials:\n" + rag)
    if extra_context:
        lines.append("Page context:\n" + extra_context[:2000])
    return "\n".join(lines)

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


async def stream_claude(sys_prompt: str, prompt: str) -> AsyncIterator[Tuple[str, str]]:
    """Headless Claude Code; yields (sse_frame, text_chunk). Raises RuntimeError on soft fail for fallback."""
    if not shutil.which(CLAUDE_BIN):
        raise RuntimeError("missing_claude_cli")

    env = os.environ.copy()
    # Route Claude Code to DeepSeek Anthropic-compatible API.
    # Clear host/proxy Claude-Code overrides that would steal auth (e.g. cc-connect).
    for k in list(env):
        ku = k.upper()
        if ku.startswith("ANTHROPIC_") or ku.startswith("CLAUDE_CODE") or ku in {
            "CLAUDECODE",
            "API_TIMEOUT_MS",
            "DISABLE_AUTOUPDATER",
        }:
            env.pop(k, None)
    env["ANTHROPIC_BASE_URL"] = ANTHROPIC_BASE_URL
    env["ANTHROPIC_API_KEY"] = DEEPSEEK_KEY
    env["ANTHROPIC_AUTH_TOKEN"] = DEEPSEEK_KEY
    env["ANTHROPIC_MODEL"] = MODEL
    env["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = "1"

    cmd = [
        CLAUDE_BIN,
        "-p",
        "--model",
        MODEL,
        "--effort",
        EFFORT,
        "--tools",
        "",
        "--system-prompt",
        sys_prompt,  # full replace of default system prompt
        "--output-format",
        "stream-json",
        "--verbose",
        "--include-partial-messages",
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
        start_new_session=True,
    )
    assert proc.stdin and proc.stdout
    deadline = time.time() + CLAUDE_TIMEOUT
    got_text = False
    err_msg: Optional[str] = None
    api_retries = 0
    # Track open content blocks for tool/thinking labels
    open_blocks: Dict[int, str] = {}

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
                    frame, _ = _proc("status", str(msg.get("status")))
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
                        frame, _ = _proc("tool", f"→ {name}", name=name, phase="start")
                        if frame:
                            yield frame, ""
                    elif btype in ("thinking", "reasoning"):
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
                        if text:
                            frame, _ = _proc("thinking", text)
                            if frame:
                                yield frame, ""
                    elif dtype == "input_json_delta":
                        partial = delta.get("partial_json") or ""
                        if partial:
                            frame, _ = _proc("tool", partial, phase="input")
                            if frame:
                                yield frame, ""
                elif et == "content_block_stop":
                    idx = int(ev.get("index") or 0)
                    open_blocks.pop(idx, None)
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
                            if text and not got_text:
                                got_text = True
                                yield sse({"type": "delta", "text": text}), text
                        elif btype in ("thinking", "reasoning"):
                            text = block.get("thinking") or block.get("text") or ""
                            if text:
                                frame, _ = _proc("thinking", text)
                                if frame:
                                    yield frame, ""
                        elif btype == "tool_use":
                            name = block.get("name") or "tool"
                            inp = block.get("input")
                            detail = f"{name} {json.dumps(inp, ensure_ascii=False)[:400]}" if inp else name
                            frame, _ = _proc("tool", detail, name=name, phase="use")
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
            yield sse({"type": "done", "truncated": True}), ""
        else:
            yield sse({"type": "done"}), ""
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
    rag = select_rag(req.message)
    sys_p = system_prompt(lang, rag, req.context)
    prompt = user_prompt(req.message, req.history)

    async def gen():
        global _inflight
        started = time.time()
        reply_parts: List[str] = []
        status = "ok"
        try:
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
