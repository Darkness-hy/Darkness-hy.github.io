(() => {
  "use strict";

  const ENDPOINT =
    window.HOMEPAGE_AGENT_ENDPOINT ||
    window.TUTOR_ENDPOINT ||
    "https://tutor.hongyuding.site/chat";
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
        "Hi — ask me anything about Hongyu's research, papers, education, or collaboration.",
      placeholder: "Ask me anything…",
      send: "send",
      stop: "stop",
      clear: "clear",
      close: "Close",
      open: "Open AI assistant",
      suggestions: [
        "What does Hongyu work on?",
        "Summarize Uni-LaViRA in one paragraph",
        "How can I contact Hongyu?",
      ],
      busy: "The assistant is busy — try again in a moment.",
      network: "Could not reach the assistant.",
    },
    zh: {
      title: "AI 助理",
      available: "可用",
      unavailable: "暂不可用",
      checking: "检测中…",
      topic: "Ask me anything",
      empty:
        "你好——关于 Hongyu 的研究、论文、教育经历或合作意向，都可以问我。",
      placeholder: "Ask me anything…",
      send: "发送",
      stop: "停止",
      clear: "清空",
      close: "收起",
      open: "打开 AI 助理",
      suggestions: [
        "Hongyu 目前研究什么？",
        "用一段话概括 Uni-LaViRA",
        "如何联系 Hongyu？",
      ],
      busy: "助理正忙，请稍后再试。",
      network: "无法连接助理服务。",
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

  // ── Widget state ────────────────────────────────────────────────────────
  const state = {
    open: false,
    turns: [],
    streamShown: "",
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

    state.turns.forEach((turn) => {
      const row = document.createElement("div");
      row.className = `agent-row agent-row--${turn.role}`;
      const bubble = document.createElement("div");
      bubble.className = `agent-bubble agent-bubble--${turn.role}`;
      if (turn.role === "user") bubble.textContent = turn.content;
      else bubble.innerHTML = simpleMarkdown(turn.content);
      row.appendChild(bubble);
      bodyEl.appendChild(row);
    });

    if (state.busy) {
      const row = document.createElement("div");
      row.className = "agent-row agent-row--assistant";
      const bubble = document.createElement("div");
      bubble.className = "agent-bubble agent-bubble--assistant";
      bubble.innerHTML = state.streamShown
        ? simpleMarkdown(state.streamShown)
        : '<span style="color:var(--color-muted)">…</span>';
      row.appendChild(bubble);
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
    state.turns = [...state.turns, { role: "assistant", content }];
    state.streamShown = "";
    state.busy = false;
    state.justAnswered = true;
    render();
    if (happyTimer) clearTimeout(happyTimer);
    happyTimer = setTimeout(() => {
      state.justAnswered = false;
      render();
    }, 1500);
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
    const history = state.turns.map((x) => ({ role: x.role, content: x.content }));
    state.turns = [...state.turns, { role: "user", content: message }];
    state.busy = true;
    state.streamShown = "";
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
    if (fullText) {
      state.turns = [...state.turns, { role: "assistant", content: fullText }];
    }
    state.streamShown = "";
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
