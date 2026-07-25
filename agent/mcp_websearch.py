#!/usr/bin/env python3
"""Minimal MCP server: free web search via DuckDuckGo (package: ddgs).

No API key. Tools:
  - web_search: DuckDuckGo text results
  - web_fetch: fetch a public URL as text
"""
from __future__ import annotations

import json
import re
import sys
import urllib.parse
import urllib.request
from html import unescape
from typing import Any, Dict, List, Optional


def _read_message() -> Optional[Dict[str, Any]]:
    headers: Dict[str, str] = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        if line in (b"\r\n", b"\n"):
            break
        try:
            k, v = line.decode("utf-8", "replace").split(":", 1)
            headers[k.strip().lower()] = v.strip()
        except ValueError:
            continue
    n = int(headers.get("content-length", "0") or 0)
    if n <= 0:
        return None
    body = sys.stdin.buffer.read(n)
    return json.loads(body.decode("utf-8"))


def _write_message(msg: Dict[str, Any]) -> None:
    raw = json.dumps(msg, ensure_ascii=False).encode("utf-8")
    sys.stdout.buffer.write(f"Content-Length: {len(raw)}\r\n\r\n".encode("ascii") + raw)
    sys.stdout.buffer.flush()


def ddg_search(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """Free DuckDuckGo search via `ddgs` (preferred) or legacy package."""
    q = (query or "").strip()
    if not q:
        return []
    max_results = max(1, min(int(max_results or 5), 8))

    # Prefer new package name
    for mod_name in ("ddgs", "duckduckgo_search"):
        try:
            mod = __import__(mod_name)
            DDGS = getattr(mod, "DDGS")
            out: List[Dict[str, str]] = []
            with DDGS() as ddgs:
                # ddgs supports backend=auto; don't force deprecated backends
                for row in ddgs.text(q, max_results=max_results):
                    out.append(
                        {
                            "title": str(row.get("title") or ""),
                            "url": str(row.get("href") or row.get("link") or ""),
                            "snippet": str(row.get("body") or row.get("snippet") or "")[:320],
                        }
                    )
            if out:
                return out
        except Exception:
            continue

    # arXiv free fallback for robotics/academic queries
    try:
        aq = "all:" + "+".join(q.split()[:8])
        url = "http://export.arxiv.org/api/query?" + urllib.parse.urlencode(
            {
                "search_query": aq,
                "start": 0,
                "max_results": max_results,
                "sortBy": "relevance",
                "sortOrder": "descending",
            }
        )
        req = urllib.request.Request(
            url, headers={"User-Agent": "HomepageAgent/1.0 (+https://hongyuding.site)"}
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            xml = resp.read().decode("utf-8", "replace")
        titles = re.findall(r"<title>([^<]+)</title>", xml)[1:]
        ids = re.findall(r"<id>(https?://arxiv.org/abs/[^<]+)</id>", xml)
        summaries = re.findall(r"<summary>([^<]+)</summary>", xml)
        out = []
        for i, title in enumerate(titles[:max_results]):
            out.append(
                {
                    "title": unescape(title.strip()),
                    "url": ids[i] if i < len(ids) else "",
                    "snippet": unescape(re.sub(r"\s+", " ", summaries[i])).strip()[:320]
                    if i < len(summaries)
                    else "",
                }
            )
        if out:
            return out
    except Exception:
        pass

    return [
        {
            "title": "search_empty",
            "url": "",
            "snippet": "No results. Prefer local knowledge or rephrase the query.",
        }
    ]


def web_fetch(url: str, max_chars: int = 8000) -> Dict[str, Any]:
    url = (url or "").strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        return {"ok": False, "error": "url must start with http:// or https://", "url": url}
    max_chars = max(500, min(int(max_chars or 8000), 20000))
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; HomepageAgent/1.0; +https://hongyuding.site)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
        method="GET",
    )
    status = 0
    ctype = ""
    text = ""
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            ctype = resp.headers.get("Content-Type", "") or ""
            raw = resp.read()
            text = raw.decode("utf-8", "replace")
            status = int(getattr(resp, "status", 200) or 200)
    except Exception as e:
        return {"ok": False, "error": str(e)[:300], "url": url}

    if "html" in ctype.lower() or text.lstrip().startswith("<"):
        text = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", text)
        text = re.sub(r"(?is)<!--.*?-->", " ", text)
        text = re.sub(r"(?is)<title[^>]*>(.*?)</title>", r"\n# \1\n", text)
        text = re.sub(r"(?is)<h[1-3][^>]*>(.*?)</h[1-3]>", r"\n## \1\n", text)
        text = re.sub(r"(?is)<(br|p|div|li|tr)[^>]*>", "\n", text)
        text = re.sub(r"(?is)<[^>]+>", " ", text)
        text = unescape(re.sub(r"[ \t]+", " ", text))
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) > max_chars:
        text = text[:max_chars] + "\n…[truncated]…"
    return {"ok": True, "url": url, "status": status, "content_type": ctype, "text": text}


TOOLS = [
    {
        "name": "web_search",
        "description": (
            "Free web search via DuckDuckGo (no API key). Use for public facts, "
            "field surveys, arXiv/SOTA. Returns title/url/snippet list."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "max_results": {
                    "type": "integer",
                    "description": "Max results 1-8 (default 5)",
                    "minimum": 1,
                    "maximum": 8,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "web_fetch",
        "description": (
            "Fetch a public http(s) URL and return readable text (HTML stripped). "
            "Use when the visitor pastes a specific link."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Full http(s) URL"},
                "max_chars": {
                    "type": "integer",
                    "description": "Max characters (default 8000)",
                    "minimum": 500,
                    "maximum": 20000,
                },
            },
            "required": ["url"],
        },
    },
]


def handle(msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    mid = msg.get("id")
    method = msg.get("method")
    params = msg.get("params") or {}

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": mid,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "homepage-ddg-websearch", "version": "1.2.0"},
            },
        }
    if method == "notifications/initialized":
        return None
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS}}
    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        if name == "web_search":
            results = ddg_search(
                str(args.get("query") or ""), int(args.get("max_results") or 5)
            )
            text = json.dumps(
                {"provider": "duckduckgo", "results": results},
                ensure_ascii=False,
                indent=2,
            )
            return {
                "jsonrpc": "2.0",
                "id": mid,
                "result": {
                    "content": [{"type": "text", "text": text}],
                    "isError": False,
                },
            }
        if name == "web_fetch":
            payload = web_fetch(
                str(args.get("url") or ""),
                int(args.get("max_chars") or 8000),
            )
            text = json.dumps(payload, ensure_ascii=False, indent=2)
            return {
                "jsonrpc": "2.0",
                "id": mid,
                "result": {
                    "content": [{"type": "text", "text": text}],
                    "isError": not payload.get("ok", False),
                },
            }
        return {
            "jsonrpc": "2.0",
            "id": mid,
            "error": {"code": -32601, "message": f"unknown tool {name}"},
        }
    if method == "ping":
        return {"jsonrpc": "2.0", "id": mid, "result": {}}
    if mid is None:
        return None
    return {
        "jsonrpc": "2.0",
        "id": mid,
        "error": {"code": -32601, "message": f"method not found: {method}"},
    }


def main() -> None:
    while True:
        msg = _read_message()
        if msg is None:
            break
        resp = handle(msg)
        if resp is not None:
            _write_message(resp)


if __name__ == "__main__":
    main()
