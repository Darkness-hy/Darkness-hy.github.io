# Homepage AI agent (茜茜)

Claude Code headless harness (`claude -p --system-prompt …`, no default Claude Code system boilerplate) targeting **DeepSeek v4 Flash**, plus local RAG over paper TeX + profile + taste notes.

`AGENT_HARNESS=claude-code` (current prod): headless Claude Code against DeepSeek Anthropic-compat, with tools:

- **Read / Glob / Grep** — local `knowledge/` (profile, taste, paper TeX) and optional `AGENT_CC_ADD_DIRS`
- **web_search (MCP)** — multi-source free search via `mcp_websearch.py` (Wikipedia + arXiv + OpenAlex + DuckDuckGo; no API key)
- **WebSearch / WebFetch** — Claude-native tools when the model backend supports them  
- **No Bash/Edit** on the public homepage agent  

Frontend: each tool call / tool result is a **separate chat bubble**; final answer is another bubble.

Uses an **isolated settings file** so global `~/.claude/settings.json` (e.g. local cli-proxy on `:8317`) cannot hijack the request. Do **not** use `--bare` if you need WebSearch (it strips those tools).

`http`: direct DeepSeek OpenAI-compatible streaming (fallback if Claude Code fails).

`auto`: Claude Code first, then HTTP. Intermediate `status` / `thinking` / `tool` SSE events stream to the frontend when present (thinking only if `AGENT_THINKING` enabled).

## Run

```bash
cd agent
cp .env.example .env   # set DEEPSEEK_API_KEY
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

Deploy this `agent/` service behind HTTPS and point the homepage at it. Do not reuse the course tutor system prompt on the same process without separating configs.

## Knowledge (RAG)

- `knowledge/profile.md` — bio, education, paper list, contact
- `knowledge/taste.md` — Hongyu insight/taste skill
- `knowledge/papers/<arxiv-id>/` — original TeX (+ `INDEX.md` extract)

## Notes

- System prompt is minimal; name「茜茜」/ Cici is only revealed when asked.
- Collapsed FAB uses the **greeting** avatar (not sleeping).
- Status light: green online / red offline / amber checking.
- Empty-state and placeholder copy: **Ask me anything**.