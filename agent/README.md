# Homepage AI agent (茜茜)

Claude Code headless harness (`claude -p --system-prompt …`, no default Claude Code system boilerplate) targeting **DeepSeek v4 Flash**, plus local RAG over paper TeX + profile + taste notes.

`AGENT_HARNESS=auto` (default): try Claude Code first; if it times out/errors (DeepSeek Anthropic-compat can 502), fall back to direct DeepSeek OpenAI-compatible HTTP streaming with the **same model and prompt**.

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