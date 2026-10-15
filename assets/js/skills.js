(() => {
  "use strict";

  const CATALOG_URL = "catalog.json";
  const app = document.querySelector("#skills-app");
  if (!app) {
    return;
  }

  const COPY = {
    count: {
      en: (n) => (n === 1 ? "1 skill" : `${n} skills`),
      zh: (n) => `${n} 个技能`,
    },
    searchLabel: { en: "Filter", zh: "筛选" },
    searchPlaceholder: { en: "Name, keyword, or description", zh: "名称、关键词或简介" },
    empty: { en: "No skills match that filter.", zh: "没有符合筛选条件的技能。" },
    error: { en: "Could not load the skills catalog.", zh: "无法加载技能目录。" },
    missing: { en: "This skill is not in the catalog.", zh: "目录中没有这项技能。" },
    back: { en: "All skills", zh: "全部技能" },
    copy: { en: "Copy SKILL.md", zh: "复制 SKILL.md" },
    copied: { en: "Copied", zh: "已复制" },
    raw: { en: "Raw", zh: "原文" },
    loading: { en: "Loading skills…", zh: "正在加载技能…" },
  };

  let catalog = [];
  let query = "";
  let rawCache = new Map();
  let copyTimer = 0;
  let lastHash = null;
  let loaded = false;

  function language() {
    return document.documentElement.dataset.language === "zh" ? "zh" : "en";
  }

  function t(key) {
    const entry = COPY[key];
    if (!entry) {
      return key;
    }
    const value = entry[language()];
    return typeof value === "function" ? value : value;
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function displayDescription(text) {
    const trimmed = String(text || "").split(/Trigger on/i)[0].trim();
    return trimmed.replace(/[。.\s]+$/, "") + (trimmed ? "." : "");
  }

  function skillIdFromHash() {
    const hash = window.location.hash.replace(/^#/, "").trim();
    return decodeURIComponent(hash.replace(/^\/+/, ""));
  }

  function setHash(id) {
    const next = id ? `#${id}` : "";
    if (window.location.hash !== next) {
      const url = `${window.location.pathname}${window.location.search}${next}`;
      window.history.pushState(null, "", url);
    }
  }

  function inlineMarkdown(text) {
    const slots = [];
    let source = String(text).replace(/`([^`]+)`/g, (_, code) => {
      slots.push(`<code>${escapeHtml(code)}</code>`);
      return `\u0000${slots.length - 1}\u0000`;
    });
    source = escapeHtml(source);
    source = source.replace(
      /\[([^\]]+)\]\((https?:[^)\s]+)\)/g,
      '<a href="$2" rel="noopener noreferrer">$1</a>',
    );
    source = source.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    source = source.replace(/(^|[^*])\*([^*]+)\*/g, "$1<em>$2</em>");
    source = source.replace(/\u0000(\d+)\u0000/g, (_, index) => slots[Number(index)]);
    return source;
  }

  function isFence(line) {
    return line.startsWith("```");
  }

  function isTableSeparator(line) {
    return /^\s*\|?[\s:|-]+\s*$/.test(line) && line.includes("-");
  }

  function splitRow(line) {
    const trimmed = line.trim().replace(/^\|/, "").replace(/\|$/, "");
    return trimmed.split("|").map((cell) => cell.trim());
  }

  function renderMarkdown(markdown) {
    const lines = String(markdown).replace(/\r\n/g, "\n").split("\n");
    const html = [];
    let index = 0;

    const isList = (line) => /^\s*[-*]\s+/.test(line) || /^\s*\d+\.\s+/.test(line);
    const isHeading = (line) => /^#{1,6}\s+/.test(line);
    const isQuote = (line) => line.startsWith("> ");
    const isHr = (line) => /^---+$/.test(line.trim());
    const isTableStart = (i) =>
      lines[i].includes("|") && i + 1 < lines.length && isTableSeparator(lines[i + 1]);

    while (index < lines.length) {
      const line = lines[index];

      if (isFence(line)) {
        const lang = escapeHtml(line.slice(3).trim());
        const body = [];
        index += 1;
        while (index < lines.length && !isFence(lines[index])) {
          body.push(lines[index]);
          index += 1;
        }
        if (index < lines.length) {
          index += 1;
        }
        html.push(
          `<pre><code${lang ? ` class="language-${lang}"` : ""}>${escapeHtml(body.join("\n"))}</code></pre>`,
        );
        continue;
      }

      if (isHr(line)) {
        html.push("<hr>");
        index += 1;
        continue;
      }

      if (isHeading(line)) {
        const match = line.match(/^(#{1,6})\s+(.*)$/);
        const level = match[1].length;
        html.push(`<h${level}>${inlineMarkdown(match[2])}</h${level}>`);
        index += 1;
        continue;
      }

      if (isQuote(line)) {
        const quoted = [];
        while (index < lines.length && lines[index].startsWith(">")) {
          quoted.push(lines[index].replace(/^>\s?/, ""));
          index += 1;
        }
        html.push(`<blockquote>${renderMarkdown(quoted.join("\n"))}</blockquote>`);
        continue;
      }

      if (isTableStart(index)) {
        const headers = splitRow(line);
        index += 2;
        const rows = [];
        while (index < lines.length && lines[index].includes("|") && !isHr(lines[index])) {
          rows.push(splitRow(lines[index]));
          index += 1;
        }
        const head = headers.map((cell) => `<th>${inlineMarkdown(cell)}</th>`).join("");
        const body = rows
          .map((row) => `<tr>${row.map((cell) => `<td>${inlineMarkdown(cell)}</td>`).join("")}</tr>`)
          .join("");
        html.push(`<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`);
        continue;
      }

      if (isList(line)) {
        const ordered = /^\s*\d+\.\s+/.test(line);
        const tag = ordered ? "ol" : "ul";
        const items = [];
        while (index < lines.length && isList(lines[index])) {
          items.push(lines[index].replace(/^\s*(?:[-*]|\d+\.)\s+/, ""));
          index += 1;
        }
        html.push(
          `<${tag}>${items.map((item) => `<li>${inlineMarkdown(item)}</li>`).join("")}</${tag}>`,
        );
        continue;
      }

      if (!line.trim()) {
        index += 1;
        continue;
      }

      const paragraph = [];
      while (
        index < lines.length &&
        lines[index].trim() &&
        !isFence(lines[index]) &&
        !isHeading(lines[index]) &&
        !isHr(lines[index]) &&
        !isQuote(lines[index]) &&
        !isList(lines[index]) &&
        !isTableStart(index)
      ) {
        paragraph.push(lines[index]);
        index += 1;
      }
      html.push(`<p>${inlineMarkdown(paragraph.join(" "))}</p>`);
    }

    return html.join("\n");
  }

  function parseSkillMarkdown(text) {
    if (!text.startsWith("---")) {
      return { meta: {}, body: text };
    }
    const match = text.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/);
    if (!match) {
      return { meta: {}, body: text };
    }
    return { meta: {}, body: match[2].replace(/^\n/, "") };
  }

  function chips(keywords) {
    if (!keywords.length) {
      return "";
    }
    return `<ul class="skill-chips">${keywords
      .map((keyword) => `<li>${escapeHtml(keyword)}</li>`)
      .join("")}</ul>`;
  }

  function filteredSkills() {
    const needle = query.trim().toLowerCase();
    if (!needle) {
      return catalog;
    }
    return catalog.filter((skill) => {
      const haystack = [
        skill.id,
        skill.name,
        skill.title,
        skill.description,
        skill.packageType,
        ...(skill.keywords || []),
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(needle);
    });
  }

  function skillCardsHtml(skills) {
    if (!skills.length) {
      return `<p class="skills-empty">${escapeHtml(t("empty"))}</p>`;
    }
    return `<ul class="skill-grid">${skills
      .map(
        (skill) => `
      <li>
        <a class="skill-card" href="#${encodeURIComponent(skill.id)}">
          <p class="skill-card__kicker">${escapeHtml(skill.packageType)} · v${escapeHtml(skill.version)}</p>
          <h2 class="skill-card__name">${escapeHtml(skill.name)}</h2>
          <p class="skill-card__summary">${escapeHtml(displayDescription(skill.description))}</p>
          ${chips(skill.keywords || [])}
        </a>
      </li>`,
      )
      .join("")}</ul>`;
  }

  function renderList(options = {}) {
    const rebuild = options.rebuild !== false || !app.querySelector("#skill-filter");
    const skills = filteredSkills();
    const lang = language();
    if (rebuild) {
      app.innerHTML = `
        <div class="skills-toolbar">
          <p class="skills-count">${escapeHtml(COPY.count[lang](skills.length))}</p>
          <div class="skills-search">
            <label for="skill-filter">${escapeHtml(t("searchLabel"))}</label>
            <input id="skill-filter" type="search" value="${escapeHtml(query)}" placeholder="${escapeHtml(t("searchPlaceholder"))}" autocomplete="off">
          </div>
        </div>
        <div data-skill-results>${skillCardsHtml(skills)}</div>
      `;
      const input = app.querySelector("#skill-filter");
      input.addEventListener("input", (event) => {
        query = event.target.value;
        renderList({ rebuild: false });
      });
      return;
    }
    const count = app.querySelector(".skills-count");
    const results = app.querySelector("[data-skill-results]");
    if (count) {
      count.textContent = COPY.count[lang](skills.length);
    }
    if (results) {
      results.innerHTML = skillCardsHtml(skills);
    }
  }

  async function loadRaw(skill) {
    if (rawCache.has(skill.id)) {
      return rawCache.get(skill.id);
    }
    const response = await fetch(skill.href);
    if (!response.ok) {
      throw new Error(String(response.status));
    }
    const text = await response.text();
    rawCache.set(skill.id, text);
    return text;
  }

  async function renderReader(id) {
    const skill = catalog.find((entry) => entry.id === id);
    if (!skill) {
      app.innerHTML = `
        <div class="skill-reader">
          <p class="skills-status">${escapeHtml(t("missing"))}</p>
          <p><a class="skill-reader__back" href="#">${escapeHtml(t("back"))}</a></p>
        </div>`;
      return;
    }

    app.innerHTML = `<p class="skills-status">${escapeHtml(t("loading"))}</p>`;
    try {
      const raw = await loadRaw(skill);
      if (skillIdFromHash() !== id) {
        return;
      }
      const parsed = parseSkillMarkdown(raw);
      app.innerHTML = `
        <article class="skill-reader">
          <div class="skill-reader__nav">
            <a class="skill-reader__back" href="#">${escapeHtml(t("back"))}</a>
            <div class="skill-reader__actions">
              <button type="button" data-copy="true">${escapeHtml(t("copy"))}</button>
              <a href="${escapeHtml(skill.href)}" rel="noopener">${escapeHtml(t("raw"))}</a>
            </div>
          </div>
          <p class="skill-reader__kicker">${escapeHtml(skill.packageType)} · v${escapeHtml(skill.version)}</p>
          <h1>${escapeHtml(skill.name)}</h1>
          <p class="skill-reader__description">${escapeHtml(displayDescription(skill.description))}</p>
          ${chips(skill.keywords || [])}
          <div class="skill-prose">${renderMarkdown(parsed.body)}</div>
        </article>
      `;
      const copyButton = app.querySelector("[data-copy]");
      copyButton.addEventListener("click", async () => {
        try {
          await navigator.clipboard.writeText(raw);
          copyButton.textContent = t("copied");
          window.clearTimeout(copyTimer);
          copyTimer = window.setTimeout(() => {
            copyButton.textContent = t("copy");
          }, 1600);
        } catch {
          copyButton.textContent = t("copy");
        }
      });
    } catch {
      app.innerHTML = `
        <div class="skill-reader">
          <p class="skills-status">${escapeHtml(t("error"))}</p>
          <p><a class="skill-reader__back" href="#">${escapeHtml(t("back"))}</a></p>
        </div>`;
    }
  }

  function render() {
    if (!loaded) {
      return;
    }
    const id = skillIdFromHash();
    const hash = window.location.hash;
    if (id) {
      renderReader(id);
    } else {
      renderList({ rebuild: true });
    }
    if (hash !== lastHash) {
      window.scrollTo(0, 0);
      lastHash = hash;
    }
  }

  app.addEventListener("click", (event) => {
    const link = event.target.closest("a[href^='#']");
    if (!link) {
      return;
    }
    const href = link.getAttribute("href");
    if (href === "#") {
      event.preventDefault();
      setHash("");
      renderList();
      window.scrollTo(0, 0);
    }
  });

  window.addEventListener("hashchange", render);
  window.addEventListener("popstate", render);
  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && skillIdFromHash()) {
      setHash("");
      renderList();
    }
  });

  new MutationObserver(render).observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["data-language"],
  });

  app.textContent = t("loading");

  fetch(CATALOG_URL)
    .then((response) => {
      if (!response.ok) {
        throw new Error(String(response.status));
      }
      return response.json();
    })
    .then((data) => {
      catalog = Array.isArray(data.skills) ? data.skills : [];
      loaded = true;
      render();
    })
    .catch(() => {
      app.innerHTML = `<p class="skills-status">${escapeHtml(t("error"))}</p>`;
    });
})();
