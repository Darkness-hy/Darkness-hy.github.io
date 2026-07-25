# Homepage AI agent (茜茜)

Claude Code headless harness (`claude -p --system-prompt …`) targeting **DeepSeek v4 Flash**, with server-side RAG over profile / taste / paper indexes.

## Tools (aligned with free Claude Code multi-call use)

| Tool | How | Notes |
|------|-----|--------|
| **web_search** (MCP) | Model may call **many times** | Wikipedia + arXiv + OpenAlex + Crossref; optional Brave / Serper / SearXNG via env |
| **web_fetch** (MCP) | Model may call **many times** | Public URL → text |
| Server survey prefetch | Automatic for field surveys | Same multi-source stack; UI shows `WebSearch(...)` |
| Server paper / taste inject | Automatic | UI shows `Read(knowledge/…)` when relevant |
| **No** Bash / Edit / Write | Denied | |
| **No** Glob / Grep / model Read | Default | Local FS not exposed to the model |

Native Claude `WebSearch` / `WebFetch` are **disabled** (unreliable on DeepSeek Anthropic gateway).

Tool descriptions in MCP match CC-style “use freely / multiple times” guidance; the system prompt does **not** impose a tool-call budget.

## Search backends

Default (no API key):

1. Wikipedia  
2. arXiv  
3. OpenAlex  
4. Crossref  

Optional env: `BRAVE_API_KEY`, `SERPER_API_KEY`, `SEARXNG_URL`.

DuckDuckGo was removed (low quality for this use case).

## Isolation user `xixi`

Production should run as system user **xixi** with:

- Readonly knowledge at `/var/lib/xixi/knowledge`
- Secrets in `/etc/homepage-agent/env` (mode `0640` root:xixi) — **not** under knowledge or git
- Logs at `/var/lib/xixi/logs` (metadata-only unless `AGENT_LOG_FULL=1`)
- `AGENT_CC_TOOLS=` and `AGENT_CC_ADD_DIR=0`

```bash
sudo bash agent/deploy/setup_xixi.sh
sudo systemctl enable --now homepage-agent
sudo systemctl status homepage-agent
```

## Run (dev)

```bash
cd agent
cp .env.example .env   # set DEEPSEEK_API_KEY; chmod 600 .env
./run.sh
```

Health: `GET http://127.0.0.1:8788/health`  
Chat (SSE): `POST http://127.0.0.1:8788/chat`

## Frontend

Static site loads `assets/js/tutor.js`. Override endpoints before the script:

```html
<script>
  window.HOMEPAGE_AGENT_ENDPOINT = 'https://your-host/chat';
  window.HOMEPAGE_AGENT_HEALTH = 'https://your-host/health';
</script>
```

## Knowledge

- `knowledge/profile.md` — bio / paper list (system inject)
- `knowledge/taste.summary.md` — short taste (system inject)
- `knowledge/taste.md` — full skill (server Read bubble on research-taste questions)
- `knowledge/papers/<arxiv-id>/INDEX.md` — paper extracts (server Read bubble)

## Notes

- System prompt is minimal; name「茜茜」/ Cici is only revealed when asked.
- Isolated Claude settings dir so `~/.claude` proxy cannot hijack the model.
- Default logs: metadata only (`msg_chars`, `reply_chars`, status, timing) — no full prompts/tools/secrets.
