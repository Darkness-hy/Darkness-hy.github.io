(() => {
  "use strict";

  const ENDPOINT =
    window.HOMEPAGE_AGENT_ENDPOINT ||
    window.TUTOR_ENDPOINT ||
    "https://agent.hongyuding.site/chat";
  const HEALTH_ENDPOINT =
    window.HOMEPAGE_AGENT_HEALTH ||
    window.TUTOR_HEALTH ||
    deriveHealth(ENDPOINT);
  const TOKEN = window.HOMEPAGE_AGENT_TOKEN || window.TUTOR_TOKEN || "";
  const AVATAR_BASE = "assets/tutor";

  const MODE_TEX = {
    sleeping: "sleeping",
    greeting: "greeting",
    listening: "neutral",
    thinking: "thinking",
    talking: "talking",
    happy: "happy",
    confused: "confused",
    idle: "neutral",
  };

  const COPY = {
    en: {
      title: "AI Assistant",
      available: "Available",
      unavailable: "Unavailable",
      checking: "Checking…",
      topic: "Ask me anything",
      empty:
        "Hi, I'm the AI assistant on Hongyu Ding's homepage. Ask about research, papers, or his taste and beliefs.",
      placeholder: "Ask me anything…",
      send: "send",
      stop: "stop",
      clear: "clear",
      close: "Close",
      open: "Open AI assistant",
      suggestions: [
        "What does Hongyu work on?",
        "What is Hongyu's research taste / beliefs?",
        "Summarize Uni-LaViRA in one paragraph",
      ],
      busy: "The assistant is busy — try again in a moment.",
      network: "Could not reach the assistant.",
      process: "Process",
      thinking: "Thinking",
      tool: "Tool",
      status: "Status",
      toolCall: "Tool call",
      toolResult: "Tool result",
    },
    zh: {
      title: "AI 助理",
      available: "可用",
      unavailable: "暂不可用",
      checking: "检测中…",
      topic: "Ask me anything",
      empty:
        "你好，我是 Hongyu Ding 个人主页上的 AI 助理。研究、论文，或 taste 与信念，都可以问我。",
      placeholder: "Ask me anything…",
      send: "发送",
      stop: "停止",
      clear: "清空",
      close: "收起",
      open: "打开 AI 助理",
      suggestions: [
        "Hongyu 目前研究什么？",
        "Hongyu 的 research taste / 信念是什么？",
        "用一段话概括 Uni-LaViRA",
      ],
      busy: "助理正忙，请稍后再试。",
      network: "无法连接助理服务。",
      process: "过程",
      thinking: "思考",
      tool: "工具",
      status: "状态",
      toolCall: "工具调用",
      toolResult: "工具返回",
    },
  };
  function deriveHealth(chatUrl) {
    try {
      const url = new URL(chatUrl, window.location.href);
      if (!/\/chat\/?$/.test(url.pathname)) return null;
      url.pathname = url.pathname.replace(/\/chat\/?$/, "/health");
      return url.toString();
    } catch {
      return null;
    }
  }

  function lang() {
    return document.documentElement.dataset.language === "zh" ? "zh" : "en";
  }

  function t() {
    return COPY[lang()] || COPY.en;
  }

  function avatarUrl(name) {
    return `${AVATAR_BASE}/avatar-${name}.png`;
  }

  function prefersReducedMotion() {
    return window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  }

  // Preload textures
  ["neutral", "blink", "greeting", "thinking", "talking", "happy", "confused", "sleeping"].forEach((n) => {
    const im = new Image();
    im.src = avatarUrl(n);
  });

  function createAvatar(size) {
    const wrap = document.createElement("div");
    wrap.className = "tav-wrap";
    wrap.style.width = `${size}px`;
    wrap.style.height = `${size}px`;
    wrap.setAttribute("aria-hidden", "true");

    const ring = document.createElement("span");
    ring.className = "tav-ring";
    ring.hidden = true;

    const frame = document.createElement("div");
    frame.className = "tav-frame";
    const img = document.createElement("img");
    img.className = "tav-img tav-greeting";
    img.alt = "";
    img.draggable = false;
    img.src = avatarUrl("greeting");
    frame.appendChild(img);

    const status = document.createElement("span");
    status.className = "tav-status tav-status--checking";
    const statusSize = Math.max(8, Math.round(size * 0.22));
    status.style.width = `${statusSize}px`;
    status.style.height = `${statusSize}px`;
    status.style.right = `${Math.max(0, Math.round(size * 0.02))}px`;
    status.style.bottom = `${Math.max(0, Math.round(size * 0.02))}px`;

    const overlay = document.createElement("div");

    wrap.append(ring, frame, status, overlay);

    let blinkTimer = null;
    let mode = "greeting";

    function setAvailability(a) {
      status.className = `tav-status tav-status--${a || "unknown"}`;
    }

    function setMode(next) {
      mode = next;
      const reduced = prefersReducedMotion();
      const baseTex = MODE_TEX[next] || "neutral";
      img.src = avatarUrl(baseTex);
      img.className = `tav-img${reduced ? "" : ` tav-${next}`}`;
      ring.hidden = !(next === "listening" || next === "talking");
      if (!ring.hidden) {
        ring.style.animation = reduced ? "none" : "tav-ring 1.4s ease-in-out infinite";
      }

      overlay.innerHTML = "";
      if (next === "thinking" && !reduced) {
        const dots = document.createElement("span");
        dots.className = "tav-overlay-dots";
        for (let i = 0; i < 3; i++) {
          const d = document.createElement("span");
          d.style.animation = `tav-ring 1s ease-in-out ${i * 0.18}s infinite`;
          dots.appendChild(d);
        }
        overlay.appendChild(dots);
      }
    }

    function startBlink() {
      stopBlink();
      if (prefersReducedMotion()) return;
      const loop = (delay) => {
        blinkTimer = setTimeout(() => {
          if (mode !== "idle" && mode !== "listening") {
            loop(2600);
            return;
          }
          const prev = img.src;
          img.src = avatarUrl("blink");
          blinkTimer = setTimeout(() => {
            img.src = prev;
            loop(2600 + (delay % 1800));
          }, 150);
        }, delay);
      };
      loop(1600);
    }

    function stopBlink() {
      if (blinkTimer) clearTimeout(blinkTimer);
      blinkTimer = null;
    }

    return { el: wrap, setMode, setAvailability, startBlink, stopBlink };
  }

  function simpleMarkdown(text) {
    const esc = (s) =>
      s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    let html = esc(text);
    html = html.replace(/```([\s\S]*?)```/g, (_, code) => `<pre><code>${code}</code></pre>`);
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
    html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/\[([^\]]+)\]\((https?:[^)]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer">$1</a>');
    html = html
      .split(/\n{2,}/)
      .map((p) => `<p>${p.replace(/\n/g, "<br>")}</p>`)
      .join("");
    return html;
  }

  function processLabel(kind) {
    const c = t();
    if (kind === "thinking") return c.thinking;
    if (kind === "tool") return c.tool;
    if (kind === "status") return c.status;
    return kind;
  }

  function renderProcessBlock(entries, { open = false, live = false } = {}) {
    if (!entries || !entries.length) return null;
    const c = t();
    const details = document.createElement("details");
    details.className = "agent-process" + (live ? " agent-process--live" : "");
    details.open = open || live;
    const summary = document.createElement("summary");
    summary.textContent = `${c.process} · ${entries.length}`;
    details.appendChild(summary);
    const list = document.createElement("div");
    list.className = "agent-process__list";
    entries.forEach((e) => {
      const row = document.createElement("div");
      row.className = `agent-process__item agent-process__item--${e.kind || "status"}`;
      const tag = document.createElement("span");
      tag.className = "agent-process__tag";
      tag.textContent = processLabel(e.kind || "status");
      const body = document.createElement("pre");
      body.className = "agent-process__text";
      body.textContent = e.text || "";
      row.append(tag, body);
      list.appendChild(row);
    });
    details.appendChild(list);
    return details;
  }

  function pushProcess(kind, text) {
    if (!text) return;
    // Drop noisy statuses — tool bubbles already show the useful bits
    if (kind === "status") {
      const t0 = String(text).trim();
      if (
        !t0 ||
        /^requesting$/i.test(t0) ||
        /^Claude Code/i.test(t0) ||
        /^DeepSeek/i.test(t0) ||
        /^tools=/i.test(t0)
      ) {
        return;
      }
    }
    const log = state.processLog;
    const last = log[log.length - 1];
    // Merge consecutive same-kind deltas (thinking only; tools are separate bubbles)
    if (last && last.kind === kind && kind === "thinking") {
      last.text = (last.text || "") + text;
      if (last.text.length > 2000) last.text = last.text.slice(0, 2000) + "…";
    } else if (kind === "thinking") {
      log.push({ kind, text: String(text).slice(0, 2000) });
      if (log.length > 20) log.splice(0, log.length - 20);
    }
    // tool/status intermediate process lines are suppressed (shown as tool bubbles)
  }
  // ── Widget state ────────────────────────────────────────────────────────
  const state = {
    open: false,
    turns: [],
    streamShown: "",
    // Intermediate harness process: status / thinking / tool (streamed live)
    processLog: [],
    // Live tool bubbles during streaming (flushed into turns on finish)
    liveToolTurns: [],
    input: "",
    busy: false,
    error: null,
    inputFocused: false,
    justAnswered: false,
    availability: "checking",
  };
  const fabAvatar = createAvatar(52);
  const headerAvatar = createAvatar(38);

  const fab = document.createElement("button");
  fab.type = "button";
  fab.className = "agent-fab";
  fab.appendChild(fabAvatar.el);
  // Default: greeting (not sleeping)
  fabAvatar.setMode("greeting");

  const panel = document.createElement("div");
  panel.className = "agent-panel";
  panel.hidden = true;

  panel.innerHTML = `
    <header class="agent-header">
      <div class="agent-header__meta">
        <div data-avatar-slot></div>
        <div class="agent-header__text">
          <div class="agent-header__title" data-title></div>
          <div class="agent-header__sub" data-sub></div>
        </div>
      </div>
      <div class="agent-header__actions">
        <button type="button" data-clear hidden></button>
        <button type="button" data-close aria-label="Close">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18" /></svg>
        </button>
      </div>
    </header>
    <div class="agent-body" data-body></div>
    <form class="agent-form" data-form>
      <div class="agent-form__row">
        <textarea rows="1" data-input></textarea>
        <button type="submit" data-send></button>
      </div>
    </form>
  `;

  panel.querySelector("[data-avatar-slot]").appendChild(headerAvatar.el);
  document.body.append(fab, panel);

  const bodyEl = panel.querySelector("[data-body]");
  const inputEl = panel.querySelector("[data-input]");
  const sendBtn = panel.querySelector("[data-send]");
  const clearBtn = panel.querySelector("[data-clear]");
  const closeBtn = panel.querySelector("[data-close]");
  const titleEl = panel.querySelector("[data-title]");
  const subEl = panel.querySelector("[data-sub]");
  const formEl = panel.querySelector("[data-form]");

  let abortCtrl = null;
  let healthCtrl = null;
  let happyTimer = null;
  let drainTimer = null;
  let fullText = "";
  let shownLen = 0;
  let streamDone = false;
  let atBottom = true;

  function availabilityText() {
    const c = t();
    if (state.availability === "online") return c.available;
    if (state.availability === "offline") return c.unavailable;
    return c.checking;
  }

  function currentMode() {
    if (!state.open) return "greeting"; // collapsed uses greeting
    if (state.error) return "confused";
    if (state.busy && state.streamShown) return "talking";
    if (state.busy) return "thinking";
    if (state.justAnswered) return "happy";
    if (state.inputFocused || state.input.trim()) return "listening";
    if (state.turns.length === 0) return "greeting";
    return "idle";
  }

  function render() {
    const c = t();
    const mode = currentMode();
    fab.hidden = state.open;
    panel.hidden = !state.open;
    fabAvatar.setMode(mode);
    fabAvatar.setAvailability(state.availability);
    headerAvatar.setMode(mode);
    headerAvatar.setAvailability(state.availability);
    if (mode === "idle" || mode === "listening") headerAvatar.startBlink();
    else headerAvatar.stopBlink();

    fab.setAttribute("aria-label", `${c.open} · ${availabilityText()}`);
    fab.title = availabilityText();
    titleEl.textContent = c.title;
    subEl.textContent = `${c.topic} · ${availabilityText()}`;
    clearBtn.textContent = c.clear;
    clearBtn.hidden = state.turns.length === 0;
    closeBtn.setAttribute("aria-label", c.close);
    inputEl.placeholder = c.placeholder;
    sendBtn.textContent = state.busy ? c.stop : c.send;
    sendBtn.type = state.busy ? "button" : "submit";
    sendBtn.disabled = state.busy ? false : !state.input.trim();
    sendBtn.classList.toggle("agent-stop", state.busy);

    const stick = atBottom;
    bodyEl.innerHTML = "";

    if (state.turns.length === 0 && !state.busy) {
      const empty = document.createElement("div");
      empty.className = "agent-empty";
      empty.innerHTML = `<p>${c.empty}</p>`;
      c.suggestions.forEach((s) => {
        const b = document.createElement("button");
        b.type = "button";
        b.className = "agent-suggestion";
        b.textContent = s;
        b.addEventListener("click", () => send(s));
        empty.appendChild(b);
      });
      bodyEl.appendChild(empty);
    }

    function appendTurn(turn, { live = false } = {}) {
      const role = turn.role || "assistant";
      const row = document.createElement("div");
      row.className = `agent-row agent-row--${role}`;
      const col = document.createElement("div");
      col.className = "agent-col";

      if (role === "assistant" && turn.process && turn.process.length) {
        const proc = renderProcessBlock(turn.process, { open: false, live: false });
        if (proc) col.appendChild(proc);
      }

      if (role === "tool_call" || role === "tool_result") {
        // Only show compact call bubbles: "🌐 WebFetch https://…"
        // Skip result bubbles (content is for the model, not the visitor).
        if (role === "tool_result") {
          return;
        }
        const line = formatToolCallLine(turn.name || "", turn.content || "");
        if (!line) return;
        const bubble = document.createElement("div");
        bubble.className = "agent-bubble agent-bubble--tool agent-bubble--tool_call";
        bubble.textContent = line;
        col.appendChild(bubble);
      } else {
        const bubble = document.createElement("div");
        bubble.className = `agent-bubble agent-bubble--${role}`;
        if (role === "user") bubble.textContent = turn.content;
        else bubble.innerHTML = simpleMarkdown(turn.content || "");
        col.appendChild(bubble);
      }
      row.appendChild(col);
      bodyEl.appendChild(row);
    }

    state.turns.forEach((turn) => appendTurn(turn));

    if (state.busy) {
      // Tool calls/results appear as their own rows while streaming
      state.liveToolTurns.forEach((turn) => appendTurn(turn, { live: true }));

      const row = document.createElement("div");
      row.className = "agent-row agent-row--assistant";
      const col = document.createElement("div");
      col.className = "agent-col";
      // Process panel only for non-status noise (thinking); skip "requesting" spam
      const usefulProc = state.processLog.filter(
        (e) =>
          e.kind === "thinking" ||
          (e.kind === "tool" && e.text) ||
          (e.kind === "status" &&
            e.text &&
            !/^requesting$/i.test(e.text) &&
            !/^Claude Code/i.test(e.text) &&
            !/^DeepSeek/i.test(e.text))
      );
      if (usefulProc.length) {
        const proc = renderProcessBlock(usefulProc, { open: false, live: true });
        if (proc) col.appendChild(proc);
      }
      const bubble = document.createElement("div");
      bubble.className = "agent-bubble agent-bubble--assistant";
      bubble.innerHTML = state.streamShown
        ? simpleMarkdown(state.streamShown)
        : '<span class="agent-typing" style="color:var(--color-muted)">…</span>';
      col.appendChild(bubble);
      row.appendChild(col);
      bodyEl.appendChild(row);
    }
    if (state.error) {
      const err = document.createElement("div");
      err.className = "agent-error";
      err.textContent = state.error;
      bodyEl.appendChild(err);
    }

    if (stick) bodyEl.scrollTop = bodyEl.scrollHeight;
  }

  bodyEl.addEventListener("scroll", () => {
    atBottom = bodyEl.scrollHeight - bodyEl.scrollTop - bodyEl.clientHeight < 48;
  });

  async function checkHealth(quiet = false) {
    if (!HEALTH_ENDPOINT) {
      state.availability = "offline";
      render();
      return;
    }
    healthCtrl?.abort();
    const ac = new AbortController();
    healthCtrl = ac;
    if (!quiet) state.availability = "checking";
    render();
    const timer = setTimeout(() => ac.abort(), 4500);
    try {
      const res = await fetch(HEALTH_ENDPOINT, { cache: "no-store", signal: ac.signal });
      if (!res.ok) throw new Error("bad");
      const data = await res.json();
      const ready = data.ready ?? data.ok;
      state.availability = data.ok && ready ? "online" : "offline";
    } catch (err) {
      if (!(err instanceof DOMException && err.name === "AbortError")) {
        state.availability = "offline";
      }
    } finally {
      clearTimeout(timer);
      if (healthCtrl === ac) healthCtrl = null;
      render();
    }
  }

  function stopDrain() {
    if (drainTimer) clearInterval(drainTimer);
    drainTimer = null;
  }

  function startDrain() {
    stopDrain();
    drainTimer = setInterval(() => {
      if (shownLen < fullText.length) {
        const step = Math.min(3, fullText.length - shownLen);
        shownLen += step;
        state.streamShown = fullText.slice(0, shownLen);
        render();
      } else if (streamDone) {
        stopDrain();
        finishStream();
      }
    }, 30);
  }

  function finishStream() {
    const content = fullText;
    const process = state.processLog.slice();
    const tools = state.liveToolTurns.slice();
    // Commit tool turns first (each is its own message), then final assistant answer
    const next = [...state.turns, ...tools];
    if (content && content.trim()) {
      next.push({ role: "assistant", content, process });
    } else if (process.length && !tools.length) {
      next.push({ role: "assistant", content: "_(no text reply)_", process });
    }
    state.turns = next;
    state.streamShown = "";
    state.processLog = [];
    state.liveToolTurns = [];
    state.busy = false;
    state.justAnswered = true;
    render();
    if (happyTimer) clearTimeout(happyTimer);
    happyTimer = setTimeout(() => {
      state.justAnswered = false;
      render();
    }, 1500);
  }

  function pushToolTurn(role, name, text) {
    state.liveToolTurns = [
      ...state.liveToolTurns,
      {
        role, // tool_call | tool_result
        name: name || "tool",
        content: String(text || "").slice(0, 12000),
      },
    ];
  }


  function toolBubbleMeta(name, role, content) {
    const raw = String(name || "tool");
    const short = raw.includes("__") ? raw.split("__").pop() : raw;
    const lower = (short || "").toLowerCase();
    const text = String(content || "");

    // Parse Tool(arg) from server one-liners
    let arg = "";
    const m = text.match(/^[A-Za-z_][A-Za-z0-9_]*\(([\s\S]*)\)$/);
    if (m) {
      arg = m[1].replace(/^['"]|['"]$/g, "").trim();
    } else if (text.startsWith("⎿")) {
      arg = text.replace(/^⎿\s*/, "").trim();
    } else if (text && !/^webfetch|websearch|read|glob|grep/i.test(text)) {
      arg = text;
    }

    let kind = "generic";
    let emoji = "🛠️";
    let title = short || "Tool";

    if (/websearch|web_search/i.test(lower) || /websearch/i.test(text)) {
      kind = "search";
      emoji = role === "tool_result" ? "✅" : "🔍";
      title = role === "tool_result" ? "Web search done" : "Web search";
    } else if (/webfetch|web_fetch|url_prefetch/i.test(lower) || /webfetch/i.test(text)) {
      kind = "fetch";
      emoji = role === "tool_result" ? "✅" : "🌐";
      title = role === "tool_result" ? "Page fetched" : "Fetching page";
    } else if (/^read$/i.test(lower) || /^read\(/i.test(text)) {
      kind = "read";
      emoji = role === "tool_result" ? "✅" : "📄";
      title = role === "tool_result" ? "File read" : "Reading file";
    } else if (/^glob$/i.test(lower)) {
      kind = "glob";
      emoji = "📁";
      title = role === "tool_result" ? "Files found" : "Finding files";
    } else if (/^grep$/i.test(lower)) {
      kind = "grep";
      emoji = "🔎";
      title = role === "tool_result" ? "Search done" : "Searching files";
    } else if (role === "tool_result") {
      emoji = "✅";
      title = `${short} done`;
    }

    // bilingual title when UI is zh
    if (lang() === "zh") {
      const zhMap = {
        "Web search": "正在联网搜索",
        "Web search done": "搜索完成",
        "Fetching page": "正在打开网页",
        "Page fetched": "网页已获取",
        "Reading file": "正在读取文件",
        "File read": "文件已读取",
        "Finding files": "正在查找文件",
        "Files found": "文件查找完成",
        "Searching files": "正在检索文件",
        "Search done": "检索完成",
      };
      if (zhMap[title]) title = zhMap[title];
      else if (role === "tool_result") title = `${short} 完成`;
      else title = `调用 ${short}`;
    }

    // shorten long URLs / paths for detail line
    let detail = arg;
    if (detail.length > 96) {
      if (/^https?:\/\//i.test(detail)) {
        try {
          const u = new URL(detail);
          detail = u.host + (u.pathname.length > 40 ? u.pathname.slice(0, 40) + "…" : u.pathname);
        } catch {
          detail = detail.slice(0, 93) + "…";
        }
      } else {
        detail = "…" + detail.slice(-90);
      }
    }

    return { kind, emoji, title, detail };
  }
  async function ask(message, history) {
    const headers = { "Content-Type": "application/json", Accept: "text/event-stream" };
    if (TOKEN) headers.Authorization = `Bearer ${TOKEN}`;
    const res = await fetch(ENDPOINT, {
      method: "POST",
      headers,
      signal: abortCtrl.signal,
      body: JSON.stringify({
        message,
        history,
        context: null,
        lang: lang(),
        stream: true,
      }),
    });
    if (res.status === 429 || res.status === 503) throw new Error(t().busy);
    if (!res.ok || !res.body) throw new Error(`${t().network} (${res.status})`);

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const frames = buf.split("\n\n");
      buf = frames.pop() ?? "";
      for (const frame of frames) {
        const dataLine = frame.split("\n").find((l) => l.startsWith("data:"));
        if (!dataLine) continue;
        const json = dataLine.slice(5).trim();
        if (!json) continue;
        let ev;
        try {
          ev = JSON.parse(json);
        } catch {
          continue;
        }
        if (ev.type === "delta" && typeof ev.text === "string") {
          fullText += ev.text;
          if (!drainTimer) startDrain();
        } else if (ev.type === "tool_call" || ev.type === "tool_result") {
          pushToolTurn(
            ev.type,
            ev.name || "tool",
            typeof ev.text === "string" ? ev.text : ""
          );
          render();
        } else if (ev.type === "thinking" || ev.type === "tool" || ev.type === "status") {
          const text = typeof ev.text === "string" ? ev.text : ev.message || "";
          pushProcess(ev.type, text);
          render();
        } else if (ev.type === "error") {
          throw new Error(ev.message || t().network);
        } else if (ev.type === "done") {
          streamDone = true;
          if (ev.truncated) fullText += "\n\n_(回答可能被中断,请重试)_";
          if (shownLen >= fullText.length) {
            stopDrain();
            finishStream();
          }
        }
      }
    }
    streamDone = true;
    if (!state.busy) return;
    if (shownLen >= fullText.length) {
      stopDrain();
      if (fullText) finishStream();
      else {
        state.busy = false;
        state.error = t().network;
        render();
      }
    }
  }

  async function send(raw) {
    const message = (raw || "").trim();
    if (!message || state.busy) return;
    state.error = null;
    state.input = "";
    inputEl.value = "";
    // Only user/assistant text goes back as chat history (skip tool bubbles)
    const history = state.turns
      .filter((x) => x.role === "user" || x.role === "assistant")
      .map((x) => ({ role: x.role, content: x.content }));
    state.turns = [...state.turns, { role: "user", content: message }];
    state.busy = true;
    state.streamShown = "";
    state.processLog = [];
    state.liveToolTurns = [];
    fullText = "";
    shownLen = 0;
    streamDone = false;
    abortCtrl?.abort();
    abortCtrl = new AbortController();
    render();
    try {
      await ask(message, history);
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        state.busy = false;
        if (fullText) {
          state.turns = [...state.turns, { role: "assistant", content: fullText }];
        }
        state.streamShown = "";
        render();
        return;
      }
      state.busy = false;
      state.streamShown = "";
      state.error = err?.message || t().network;
      state.availability = "offline";
      render();
    }
  }

  function stop() {
    abortCtrl?.abort();
    stopDrain();
    state.busy = false;
    const tools = state.liveToolTurns.slice();
    const next = [...state.turns, ...tools];
    if (fullText) {
      next.push({
        role: "assistant",
        content: fullText,
        process: state.processLog.slice(),
      });
    }
    state.turns = next;
    state.streamShown = "";
    state.processLog = [];
    state.liveToolTurns = [];
    render();
  }
  fab.addEventListener("click", () => {
    state.open = true;
    render();
    checkHealth(true);
    inputEl.focus();
  });

  closeBtn.addEventListener("click", () => {
    abortCtrl?.abort();
    state.open = false;
    render();
  });

  clearBtn.addEventListener("click", () => {
    state.turns = [];
    state.error = null;
    render();
  });

  formEl.addEventListener("submit", (e) => {
    e.preventDefault();
    if (state.busy) return;
    send(inputEl.value);
  });

  sendBtn.addEventListener("click", (e) => {
    if (state.busy) {
      e.preventDefault();
      stop();
    }
  });

  inputEl.addEventListener("input", () => {
    state.input = inputEl.value;
    inputEl.style.height = "auto";
    inputEl.style.height = `${Math.min(inputEl.scrollHeight, 112)}px`;
    render();
  });
  inputEl.addEventListener("focus", () => {
    state.inputFocused = true;
    render();
  });
  inputEl.addEventListener("blur", () => {
    state.inputFocused = false;
    render();
  });
  inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!state.busy) send(inputEl.value);
    }
  });

  // Follow site language toggle
  const mo = new MutationObserver(() => render());
  mo.observe(document.documentElement, { attributes: true, attributeFilter: ["data-language"] });

  setTimeout(() => checkHealth(true), 0);
  setInterval(() => {
    if (document.visibilityState === "visible") checkHealth(true);
  }, 60000);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") checkHealth(true);
  });

  render();
})();
