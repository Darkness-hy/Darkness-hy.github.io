#!/usr/bin/env python3
"""Minimal MCP server: multi-source free web/academic search.

No API key required. Sources (merged, deduped):
  1. Wikipedia (definitions / overview)
  2. arXiv API (recent academic abstracts)
  3. OpenAlex (scholarly works, year-filtered)
  4. DuckDuckGo via `ddgs` (general web; backends auto/bing/yahoo)

Tools:
  - web_search: multi-source search
  - web_fetch: fetch a public URL as text
"""
from __future__ import annotations

import json
import re
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape
from typing import Any, Dict, List, Optional, Tuple


_UA = "HomepageAgent/1.0 (+https://hongyuding.site; research assistant)"
_WIKI_UA = "HomepageAgent/1.0 (https://hongyuding.site; academic homepage assistant)"


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


def _http_get(url: str, timeout: float = 12.0, headers: Optional[Dict[str, str]] = None) -> str:
    h = {"User-Agent": _UA}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def _norm_title(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").lower()).strip()[:120]


def _clean_snippet(s: str, n: int = 420) -> str:
    s = unescape(re.sub(r"\s+", " ", s or "")).strip()
    return s[:n]


# ---------- individual sources ----------


def ddg_search(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """DuckDuckGo via ddgs; try multiple backends (auto/bing/yahoo)."""
    q = (query or "").strip()
    if not q:
        return []
    max_results = max(1, min(int(max_results or 5), 8))

    for mod_name in ("ddgs", "duckduckgo_search"):
        try:
            mod = __import__(mod_name)
            DDGS = getattr(mod, "DDGS")
        except Exception:
            continue
        # Prefer backends that actually return results in practice
        for backend in ("auto", "bing", "yahoo"):
            try:
                out: List[Dict[str, str]] = []
                with DDGS() as ddgs:
                    kwargs: Dict[str, Any] = {"max_results": max_results}
                    if backend != "auto":
                        kwargs["backend"] = backend
                    for row in ddgs.text(q, **kwargs):
                        out.append(
                            {
                                "title": str(row.get("title") or ""),
                                "url": str(row.get("href") or row.get("link") or ""),
                                "snippet": _clean_snippet(
                                    str(row.get("body") or row.get("snippet") or ""), 320
                                ),
                                "source": f"ddg:{backend}",
                            }
                        )
                if out:
                    return out
            except Exception:
                continue
    return []


def arxiv_search(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """arXiv Atom API — good for robotics / ML surveys and recent papers."""
    q = (query or "").strip()
    if not q:
        return []
    max_results = max(1, min(int(max_results or 5), 8))
    # Prefer relevance; add a second recent-biased query if needed upstream
    terms = "+".join(q.split()[:10])
    aq = f"all:{terms}"
    url = "http://export.arxiv.org/api/query?" + urllib.parse.urlencode(
        {
            "search_query": aq,
            "start": 0,
            "max_results": max_results,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
    )
    try:
        xml = _http_get(url, timeout=12.0)
    except Exception:
        return []

    # Split entries
    entries = re.findall(r"<entry>(.*?)</entry>", xml, flags=re.S)
    out: List[Dict[str, str]] = []
    for ent in entries[:max_results]:
        title_m = re.search(r"<title>([^<]+)</title>", ent)
        id_m = re.search(r"<id>(https?://arxiv\.org/abs/[^<]+)</id>", ent)
        sum_m = re.search(r"<summary>([^<]+)</summary>", ent)
        year_m = re.search(r"<published>(\d{4})", ent)
        if not title_m:
            continue
        title = unescape(re.sub(r"\s+", " ", title_m.group(1))).strip()
        year = year_m.group(1) if year_m else ""
        if year:
            title = f"[{year}] {title}"
        out.append(
            {
                "title": title,
                "url": id_m.group(1) if id_m else "",
                "snippet": _clean_snippet(sum_m.group(1) if sum_m else "", 420),
                "source": "arxiv",
            }
        )
    return out


def wiki_search(query: str, max_results: int = 2) -> List[Dict[str, str]]:
    """Wikipedia OpenSearch + REST summary for short high-quality overviews."""
    q = (query or "").strip()
    if not q:
        return []
    max_results = max(1, min(int(max_results or 2), 4))
    latin = " ".join(re.findall(r"[A-Za-z][A-Za-z0-9\- ]+", q)).strip()
    words = re.findall(r"[A-Za-z][A-Za-z0-9\-]+", latin or q)
    # Try short noun phrases first — long "X survey trends 2024" often misses
    candidates: List[str] = []
    ql = (latin or q).lower()
    if "mobile" in ql and "manipulat" in ql:
        candidates.extend(["Mobile manipulator", "Mobile robot"])
    if "foundation model" in ql or "embodied" in ql:
        candidates.append("Foundation model")
    if words:
        candidates.append(" ".join(words[:3]))
        candidates.append(" ".join(words[:2]))
        if words:
            candidates.append(words[0])
    if latin:
        candidates.append(latin[:60])
    candidates.append(q[:60])
    # unique preserve order
    seen_q: set = set()
    search_qs: List[str] = []
    for c in candidates:
        c = re.sub(r"\s+", " ", c).strip()
        if not c or c.lower() in seen_q:
            continue
        seen_q.add(c.lower())
        search_qs.append(c)

    titles: List[str] = []
    urls: List[str] = []
    for search_q in search_qs[:4]:
        try:
            surl = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
                {
                    "action": "opensearch",
                    "search": search_q,
                    "limit": max_results,
                    "namespace": 0,
                    "format": "json",
                }
            )
            raw = _http_get(surl, timeout=8.0, headers={"User-Agent": _WIKI_UA})
            data = json.loads(raw)
            tlist = data[1] if isinstance(data, list) and len(data) > 1 else []
            ulist = data[3] if isinstance(data, list) and len(data) > 3 else []
            if tlist:
                titles, urls = tlist, ulist
                break
        except Exception:
            continue
    if not titles:
        return []

    out: List[Dict[str, str]] = []
    for i, title in enumerate(titles[:max_results]):
        page_url = urls[i] if i < len(urls) else ""
        extract = ""
        try:
            sum_url = (
                "https://en.wikipedia.org/api/rest_v1/page/summary/"
                + urllib.parse.quote(title.replace(" ", "_"))
            )
            sraw = _http_get(sum_url, timeout=8.0, headers={"User-Agent": _WIKI_UA})
            sdata = json.loads(sraw)
            extract = sdata.get("extract") or ""
            page_url = sdata.get("content_urls", {}).get("desktop", {}).get("page") or page_url
        except Exception:
            pass
        out.append(
            {
                "title": f"[Wikipedia] {title}",
                "url": page_url,
                "snippet": _clean_snippet(extract, 420),
                "source": "wikipedia",
            }
        )
    return out


def openalex_search(
    query: str, max_results: int = 4, min_year: int = 2018
) -> List[Dict[str, str]]:
    """OpenAlex scholarly works (free, no key). Filter to recent years."""
    q = (query or "").strip()
    if not q:
        return []
    max_results = max(1, min(int(max_results or 4), 8))
    params = {
        "search": q,
        "per_page": max_results,
        "sort": "relevance_score:desc",
        "filter": f"from_publication_date:{min_year}-01-01",
    }
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
    try:
        raw = _http_get(
            url,
            timeout=12.0,
            headers={
                "User-Agent": "HomepageAgent/1.0 (mailto:hongyuding@smail.nju.edu.cn)",
            },
        )
        data = json.loads(raw)
    except Exception:
        return []

    out: List[Dict[str, str]] = []
    for w in data.get("results") or []:
        title = (w.get("title") or "").strip()
        if not title:
            continue
        year = w.get("publication_year") or ""
        if year:
            title = f"[{year}] {title}"
        # reconstruct abstract from inverted index
        abstract = ""
        inv = w.get("abstract_inverted_index") or {}
        if inv:
            pairs: List[Tuple[int, str]] = []
            for word, idxs in inv.items():
                for i in idxs:
                    pairs.append((int(i), word))
            pairs.sort()
            abstract = " ".join(word for _, word in pairs)
        loc = w.get("primary_location") or {}
        landing = loc.get("landing_page_url") or ""
        pdf = (loc.get("pdf_url") or "") if isinstance(loc, dict) else ""
        # prefer DOI / landing; fall back to OpenAlex id
        doi = (w.get("doi") or "").replace("https://doi.org/", "")
        url_out = landing or (f"https://doi.org/{doi}" if doi else "") or (w.get("id") or "")
        if pdf and not landing:
            url_out = pdf
        out.append(
            {
                "title": title,
                "url": url_out,
                "snippet": _clean_snippet(abstract, 420),
                "source": "openalex",
            }
        )
    return out


def multi_search(query: str, max_results: int = 6) -> List[Dict[str, str]]:
    """Merge Wikipedia + arXiv + OpenAlex + DDG; prefer academic quality."""
    q = (query or "").strip()
    if not q:
        return []
    max_results = max(1, min(int(max_results or 6), 10))

    # Parallel fetch for latency
    jobs = {
        "wiki": lambda: wiki_search(q, max_results=2),
        "arxiv": lambda: arxiv_search(q, max_results=4),
        "openalex": lambda: openalex_search(q, max_results=4, min_year=2018),
        "ddg": lambda: ddg_search(q, max_results=4),
    }
    buckets: Dict[str, List[Dict[str, str]]] = {k: [] for k in jobs}
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(fn): name for name, fn in jobs.items()}
        for fut in as_completed(futs):
            name = futs[fut]
            try:
                buckets[name] = fut.result() or []
            except Exception:
                buckets[name] = []

    # Interleave: wiki first (definition), then arxiv, openalex, ddg
    order = ("wiki", "arxiv", "openalex", "ddg")
    seen_urls: set = set()
    seen_titles: set = set()
    merged: List[Dict[str, str]] = []

    # Round-robin so one source cannot dominate
    pointers = {k: 0 for k in order}
    while len(merged) < max_results:
        progressed = False
        for k in order:
            idx = pointers[k]
            bucket = buckets.get(k) or []
            if idx >= len(bucket):
                continue
            hit = bucket[idx]
            pointers[k] = idx + 1
            progressed = True
            url = (hit.get("url") or "").strip()
            title_key = _norm_title(hit.get("title") or "")
            if url and url in seen_urls:
                continue
            if title_key and title_key in seen_titles:
                continue
            if url:
                seen_urls.add(url)
            if title_key:
                seen_titles.add(title_key)
            # skip empty-url non-wiki
            if not url and k != "wiki":
                continue
            merged.append(hit)
            if len(merged) >= max_results:
                break
        if not progressed:
            break

    if not merged:
        return [
            {
                "title": "search_empty",
                "url": "",
                "snippet": "No results. Prefer local knowledge or rephrase the query.",
                "source": "none",
            }
        ]
    return merged


# keep ddg_search as the simple entry; multi_search is preferred
def web_search(query: str, max_results: int = 6) -> List[Dict[str, str]]:
    return multi_search(query, max_results=max_results)


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
            "Multi-source free search (Wikipedia + arXiv + OpenAlex + DuckDuckGo). "
            "Use for public facts, field surveys, academic SOTA. Returns title/url/snippet list."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "max_results": {
                    "type": "integer",
                    "description": "Max results 1-10 (default 6)",
                    "minimum": 1,
                    "maximum": 10,
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
                "serverInfo": {"name": "homepage-multi-websearch", "version": "2.0.0"},
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
            results = multi_search(
                str(args.get("query") or ""), int(args.get("max_results") or 6)
            )
            sources = sorted({r.get("source") or "?" for r in results})
            text = json.dumps(
                {"provider": "multi", "sources": sources, "results": results},
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
