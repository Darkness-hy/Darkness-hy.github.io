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
      available: "online",
      unavailable: "offline",
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
        "What is Hongyu's research taste / beliefs?",
        "Summarize Uni-LaViRA in one paragraph.",
        "Leave a message for Hongyu.",
      ],
      busy: "The assistant is busy — try again in a moment.",
      rateLimit: "Usage limit reached — please try again later.",
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
      available: "online",
      unavailable: "offline",
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
        "Hongyu 的 research taste / 信念是什么？",
        "用一段话概括 Uni-LaViRA。",
        "给我留言。",
      ],
      busy: "助理正忙，请稍后再试。",
      rateLimit: "使用次数已达上限，请稍后再试。",
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
    // Strip trailing newlines that would pad bubble height
    const raw = String(text || "").replace(/^\s+|\s+$/g, "");
    const hasMd =
      /\*\*|__|\*[^*]+\*|_[^_]+_|`|\[.+\]\(https?:|^\s*[-*•]\s|^\s*\d+\.\s/m.test(
        raw
      );
    // One-liners without markdown: raw text only (no <p> → no 2-line chrome)
    const isPlainOneLine =
      raw.length > 0 &&
      raw.length < 120 &&
      !/\n/.test(raw) &&
      !hasMd;
    if (isPlainOneLine) {
      return esc(raw);
    }
    let html = esc(raw);
    html = html.replace(/```([\s\S]*?)```/g, (_, code) => `<pre><code>${code}</code></pre>`);
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
    // Bold before italic so **x** is not partially eaten by *...*
    html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/__([^_]+)__/g, "<strong>$1</strong>");
    html = html.replace(/\*([^*\n]+)\*/g, "<em>$1</em>");
    html = html.replace(/_([^_\n]+)_/g, "<em>$1</em>");
    html = html.replace(/\[([^\]]+)\]\((https?:[^)]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer">$1</a>');

    // Turn consecutive - / * / 1. lines into <ul>/<ol>
    const formatBlock = (block) => {
      const lines = block.split("\n");
      const out = [];
      let listType = null; // "ul" | "ol"
      let listItems = [];
      const flushList = () => {
        if (!listType || !listItems.length) return;
        out.push(
          `<${listType}>${listItems.map((li) => `<li>${li}</li>`).join("")}</${listType}>`
        );
        listType = null;
        listItems = [];
      };
      for (const line of lines) {
        const ul = line.match(/^\s*[-*•]\s+(.+)$/);
        const ol = line.match(/^\s*\d+\.\s+(.+)$/);
        if (ul) {
          if (listType && listType !== "ul") flushList();
          listType = "ul";
          listItems.push(ul[1]);
        } else if (ol) {
          if (listType && listType !== "ol") flushList();
          listType = "ol";
          listItems.push(ol[1]);
        } else {
          flushList();
          out.push(line);
        }
      }
      flushList();
      // Join non-list leftovers with <br>
      return out
        .map((part) =>
          part.startsWith("<ul>") || part.startsWith("<ol>")
            ? part
            : part.replace(/\n/g, "<br>")
        )
        .join("<br>");
    };

    // Prefer <br> over multi-<p> for soft newlines; only double-newline → paragraph
    const blocks = html.split(/\n{2,}/).filter((b) => b.length);
    if (blocks.length <= 1) {
      return blocks[0] ? formatBlock(blocks[0]) : "";
    }
    return blocks
      .map((p) => {
        const inner = formatBlock(p);
        // Lists already block-level; wrap plain text in <p>
        if (inner.startsWith("<ul>") || inner.startsWith("<ol>")) return inner;
        return `<p>${inner}</p>`;
      })
      .join("");
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
        // mousedown + preventDefault: avoid input blur → render() destroying
        // this button before click fires (needed two clicks otherwise).
        b.addEventListener("mousedown", (e) => {
          e.preventDefault();
        });
        b.addEventListener("click", (e) => {
          e.preventDefault();
          send(s);
        });
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
        // Only show tool *calls* (WebSearch / Read / WebFetch). Hide result dumps.
        if (role === "tool_result") return;
        const raw = turn.content || "";
        const line = /^(🌐|📄|📁|🔎|🛠️)\s/.test(raw)
          ? raw
          : formatToolCallLine(turn.name || "", raw);
        if (!line) return;
        const bubble = document.createElement("div");
        bubble.className = "agent-bubble agent-bubble--tool agent-bubble--tool_call";
        bubble.textContent = line;
        col.appendChild(bubble);
      } else {
        const bubble = document.createElement("div");
        bubble.className = `agent-bubble agent-bubble--${role}`;
        if (role === "user") {
          // plain text — keep single-line height for short messages
          bubble.textContent = turn.content;
        } else {
          bubble.innerHTML = simpleMarkdown(turn.content || "");
        }
        col.appendChild(bubble);
      }
      row.appendChild(col);
      bodyEl.appendChild(row);
    }

    state.turns.forEach((turn) => appendTurn(turn));

    if (state.busy) {
      // Current in-progress assistant text (may be intermediate, then tools, then more text)
      if (state.streamShown) {
        const row = document.createElement("div");
        row.className = "agent-row agent-row--assistant";
        const col = document.createElement("div");
        col.className = "agent-col";
        const bubble = document.createElement("div");
        bubble.className = "agent-bubble agent-bubble--assistant agent-bubble--streaming";
        bubble.innerHTML = simpleMarkdown(state.streamShown);
        col.appendChild(bubble);
        row.appendChild(col);
        bodyEl.appendChild(row);
      } else {
        // Waiting for next text / tools
        const row = document.createElement("div");
        row.className = "agent-row agent-row--assistant";
        const col = document.createElement("div");
        col.className = "agent-col";
        const bubble = document.createElement("div");
        bubble.className = "agent-bubble agent-bubble--assistant";
        bubble.innerHTML =
          '<span class="agent-typing" style="color:var(--color-muted)">…</span>';
        col.appendChild(bubble);
        row.appendChild(col);
        bodyEl.appendChild(row);
      }
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

  // Adaptive typewriter: speed up when buffer lags, but NEVER dump all remaining text.
  // Base ~40 cps; ramps toward ~90 cps when lag is large; max 4 chars/frame.
  const TYPE_CPS_MIN = 36;
  const TYPE_CPS_MAX = 90;
  const TYPE_STEP_MAX = 4; // hard cap per animation frame — forbids "instant dump"
  let drainRaf = 0;
  let typeCarry = 0;
  let typeLastTs = 0;

  function stopDrain() {
    if (drainTimer) {
      clearInterval(drainTimer);
      drainTimer = null;
    }
    if (drainRaf) {
      cancelAnimationFrame(drainRaf);
      drainRaf = 0;
    }
    typeCarry = 0;
    typeLastTs = 0;
  }

  function adaptiveCps(lag) {
    // lag 0→MIN, lag 80+ → MAX (smooth, no dump)
    if (lag <= 8) return TYPE_CPS_MIN;
    if (lag >= 120) return TYPE_CPS_MAX;
    const t = (lag - 8) / (120 - 8);
    return TYPE_CPS_MIN + t * (TYPE_CPS_MAX - TYPE_CPS_MIN);
  }

  function startDrain() {
    if (drainRaf) return;
    typeLastTs = 0;
    const tick = (ts) => {
      if (!typeLastTs) typeLastTs = ts;
      // Clamp dt so a backgrounded tab doesn't dump a huge step later
      const dt = Math.min(0.032, Math.max(0, (ts - typeLastTs) / 1000));
      typeLastTs = ts;
      if (shownLen < fullText.length) {
        const lag = fullText.length - shownLen;
        typeCarry += adaptiveCps(lag) * dt;
        let n = Math.floor(typeCarry);
        if (n > 0) {
          typeCarry -= n;
          const step = Math.min(n, TYPE_STEP_MAX, lag);
          typeCarry += Math.max(0, n - step);
          shownLen += step;
          state.streamShown = fullText.slice(0, shownLen);
          render();
        }
        drainRaf = requestAnimationFrame(tick);
      } else if (streamDone) {
        drainRaf = 0;
        finishStream();
      } else {
        drainRaf = requestAnimationFrame(tick);
      }
    };
    drainRaf = requestAnimationFrame(tick);
  }

  /** Resolve when typewriter has revealed all buffered text (no snap-dump). */
  function waitTypewriterCaughtUp() {
    if (shownLen >= fullText.length) return Promise.resolve();
    if (!drainRaf) startDrain();
    return new Promise((resolve) => {
      const t0 = performance.now();
      const poll = (ts) => {
        // Cap wait so tools aren't blocked forever, but still type out (no jump)
        if (shownLen >= fullText.length || ts - t0 > 20000) {
          resolve();
          return;
        }
        requestAnimationFrame(poll);
      };
      requestAnimationFrame(poll);
    });
  }

  /** Commit current streamed assistant text as its own bubble (between tools / at end). */
  function flushAssistantText() {
    stopDrain();
    const content = fullText.trim();
    fullText = "";
    shownLen = 0;
    state.streamShown = "";
    if (!content) return;
    const last = state.turns[state.turns.length - 1];
    // avoid duplicate identical consecutive assistant lines
    if (last && last.role === "assistant" && last.content === content) return;
    state.turns = [...state.turns, { role: "assistant", content }];
  }

  function finishStream() {
    // Final text segment after last tool (if any)
    flushAssistantText();
    // Any tool calls still buffered in liveToolTurns (legacy path)
    if (state.liveToolTurns.length) {
      state.turns = [...state.turns, ...state.liveToolTurns];
    }
    const process = state.processLog.slice();
    // Attach process log to last assistant turn if present
    if (process.length) {
      const turns = state.turns.slice();
      for (let i = turns.length - 1; i >= 0; i--) {
        if (turns[i].role === "assistant") {
          turns[i] = { ...turns[i], process };
          break;
        }
      }
      state.turns = turns;
    }
    if (
      state.turns.length === 0 ||
      (state.turns[state.turns.length - 1].role === "user" && !state.liveToolTurns.length)
    ) {
      // no output at all
      if (!state.turns.some((t) => t.role === "assistant" || t.role === "tool_call")) {
        state.turns = [
          ...state.turns,
          { role: "assistant", content: "_(no text reply)_", process },
        ];
      }
    }
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
    // Hide tool results entirely (no "⎿ 3 results · …" / PDF dumps)
    if (role === "tool_result") return;
    // Flush any intermediate model text BEFORE the tool bubble
    flushAssistantText();
    const content = String(text || "").slice(0, 500);
    const line = formatToolCallLine(name || "tool", content);
    if (!line) return;
    const last = state.turns[state.turns.length - 1];
    if (last && last.role === "tool_call" && last.content === line) return;
    state.turns = [
      ...state.turns,
      { role: "tool_call", name: name || "tool", content: line },
    ];
  }

  /** One-line bubble: "🌐 WebSearch https://momastage.github.io/" — never double-prefix. */
  function formatToolCallLine(name, content) {
    let text = String(content || "").trim();
    if (!text) text = "";
    // Already a display line (emoji prefix) — use as-is (fix double prefix)
    if (/^(🌐|📄|📁|🔎|🛠️)\s/.test(text)) {
      text = text.replace(
        /^(🌐|📄|📁|🔎|🛠️)\s+(WebSearch|Read|Glob|Grep|Tool)\s+\1\s+\2\s+/,
        "$1 $2 "
      );
      // also "🌐 WebSearch 🌐 WebSearch foo"
      text = text.replace(
        /^(🌐|📄|📁|🔎|🛠️)\s+(WebSearch|Read|Glob|Grep|Tool)\s+(🌐|📄|📁|🔎|🛠️)\s+(WebSearch|Read|Glob|Grep|Tool)\s+/,
        "$1 $2 "
      );
      return text;
    }
    if (text.startsWith("⎿")) return "";

    const raw = String(name || "tool");
    let short = raw.includes("__") ? raw.split("__").pop() : raw;

    let arg = "";
    // WebSearch(query) / Read(path)
    const m = text.match(/^([A-Za-z_][\w]*)\(([\s\S]*)\)$/);
    if (m) {
      short = m[1];
      arg = m[2].replace(/^['"]|['"]$/g, "").trim();
    } else if (text) {
      // "WebSearch query" or bare query/path
      const m2 = text.match(/^(WebSearch|WebFetch|Read|Glob|Grep)\s+(.+)$/i);
      if (m2) {
        short = m2[1];
        arg = m2[2].trim();
      } else {
        arg = text.replace(/^['"]|['"]$/g, "").trim();
      }
    }

    const lower = String(short || "").toLowerCase();
    let emoji = "🛠️";
    let label = short || "Tool";

    if (/websearch|web_search/i.test(lower)) {
      emoji = "🌐";
      label = "WebSearch";
    } else if (/webfetch|web_fetch|url_prefetch/i.test(lower)) {
      emoji = "🌐";
      label = "WebFetch";
    } else if (/^read$/i.test(lower)) {
      emoji = "📄";
      label = "Read";
    } else if (/^glob$/i.test(lower)) {
      emoji = "📁";
      label = "Glob";
    } else if (/^grep$/i.test(lower)) {
      emoji = "🔎";
      label = "Grep";
    }

    const urlMatch = arg.match(/https?:\/\/[^\s)'"]+/i);
    if (urlMatch) {
      arg = urlMatch[0];
    } else if (arg && arg.length > 64) {
      // Search queries / long titles — not file paths (avoid "…/last word" bug)
      arg = arg.slice(0, 48).trim() + "…";
    }

    return arg ? `${emoji} ${label} ${arg}` : `${emoji} ${label}`;
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
    if (res.status === 429 || res.status === 503) {
      let detail = "";
      try {
        const body = await res.json();
        detail = (body && (body.detail || body.message)) || "";
        if (Array.isArray(detail)) {
          detail = detail.map((d) => d.msg || d).join(" ");
        }
      } catch {
        /* ignore non-json */
      }
      const reason = res.headers.get("X-RateLimit-Reason") || "";
      if (reason === "busy" || res.status === 503) {
        throw new Error(detail || t().busy);
      }
      throw new Error(detail || t().rateLimit);
    }
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
          // Buffer only — typewriter drain reveals at constant speed
          fullText += ev.text;
          if (!drainTimer) startDrain();
        } else if (ev.type === "text_break") {
          // Wait until typewriter catches up, then commit segment
          await waitTypewriterCaughtUp();
          flushAssistantText();
          render();
        } else if (ev.type === "tool_call" || ev.type === "tool_result") {
          await waitTypewriterCaughtUp();
          pushToolTurn(
            ev.type,
            ev.name || "tool",
            typeof ev.text === "string" ? ev.text : ""
          );
          render();
        } else if (ev.type === "thinking") {
          const th = typeof ev.text === "string" ? ev.text : "";
          if (th.trim()) {
            await waitTypewriterCaughtUp();
            flushAssistantText();
            state.turns = [
              ...state.turns,
              {
                role: "assistant",
                content: th.trim(),
                kind: "thinking",
              },
            ];
            render();
          }
        } else if (ev.type === "tool" || ev.type === "status") {
          // ignore noisy process lines (tools already have bubbles)
        } else if (ev.type === "error") {
          throw new Error(ev.message || t().network);
        } else if (ev.type === "done") {
          streamDone = true;
          if (ev.truncated) fullText += "\n\n_(回答可能被中断,请重试)_";
          // Do not finish immediately — let typewriter finish remaining buffer
          if (!drainTimer) startDrain();
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
    flushAssistantText();
    if (state.liveToolTurns.length) {
      state.turns = [...state.turns, ...state.liveToolTurns];
    }
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

  /** Update avatar/mode chrome only — never rebuild message body (preserves clicks). */
  function paintMode() {
    const mode = currentMode();
    fabAvatar.setMode(mode);
    headerAvatar.setMode(mode);
    if (mode === "idle" || mode === "listening") headerAvatar.startBlink();
    else headerAvatar.stopBlink();
    sendBtn.disabled = state.busy ? false : !state.input.trim();
  }

  inputEl.addEventListener("input", () => {
    state.input = inputEl.value;
    inputEl.style.height = "auto";
    inputEl.style.height = `${Math.min(inputEl.scrollHeight, 112)}px`;
    // Do not full-render on every keystroke — keeps suggestion buttons stable
    // and avoids wiping the transcript for mode/send-button updates only.
    paintMode();
  });
  inputEl.addEventListener("focus", () => {
    state.inputFocused = true;
    paintMode();
  });
  inputEl.addEventListener("blur", () => {
    state.inputFocused = false;
    // Defer so a click on a suggestion can fire before any potential re-render
    requestAnimationFrame(() => paintMode());
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
