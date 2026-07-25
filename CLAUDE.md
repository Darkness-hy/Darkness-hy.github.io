# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Static academic homepage for **Hongyu Ding**, served by **GitHub Pages** from the `main` branch of `Darkness-hy/Darkness-hy.github.io`. There is no build step, bundler, or framework: the live site is the checked-in HTML/CSS/JS and local assets.

## Commands

```bash
# Local preview (from repo root)
python3 -m http.server 4173 --bind 127.0.0.1

# Open http://127.0.0.1:4173
```

There is no lint, typecheck, or unit-test suite in this production tree. Validate changes by previewing in a browser (responsive widths, dark mode, Chinese toggle, reduced-motion still images).

## Architecture

Single-page static site:

| Path | Role |
|------|------|
| `index.html` | All page structure and English default copy (semantic sections: hero, news, publications, education, internships) |
| `assets/css/site.css` | Full visual system (layout, type, light/dark theme tokens, print/reduced-motion) |
| `assets/js/site.js` | Language (en/zh) and theme toggles; bilingual strings live in a `TRANSLATIONS` map keyed by `data-i18n` attributes |
| `assets/fonts/` | Self-hosted Newsreader + IBM Plex Sans (woff2) and licenses |
| `assets/images/` | Portrait (`profile-hongyu-ding.webp`), site icon, institution logos, paper teasers (webp; some animated, with `prefers-reduced-motion` posters) |
| `assets/tutor/` + `assets/css/tutor.css` + `assets/js/tutor.js` | Homepage AI assistant UI (茜茜): chat FAB/panel, status light, avatar modes |
| `agent/` | Optional server: Claude Code harness + local RAG (`knowledge/`) for the assistant — not served by GitHub Pages |
| `.nojekyll` | Disables Jekyll so `assets/` is served as-is on GitHub Pages |

### Homepage AI agent

- Frontend is static and talks to a remote `/chat` (SSE) + `/health` service configured via `window.HOMEPAGE_AGENT_*` in `index.html`.
- Server lives in `agent/`: headless `claude -p` with a minimal `--system-prompt` (no Claude Code default boilerplate), model **DeepSeek v4 Flash** via `ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic`.
- Local RAG sources: `agent/knowledge/profile.md`, `taste.md`, and arXiv TeX under `agent/knowledge/papers/<id>/` (see `INDEX.md` per paper).
- Run locally: `cd agent && cp .env.example .env && ./run.sh` (port 8788 by default).
- Persona name is 茜茜 / Cici; do not volunteer the name unless the visitor asks.

### Content model

- **Identity and structure** are authored in `index.html`.
- **Chinese strings and control chrome** are authored in `assets/js/site.js` (`TRANSLATIONS` + theme/language toggle wiring). When changing public copy, update both the HTML default and the matching `en`/`zh` entries in JS, including any nested HTML (links, emphasis).
- Interactive elements: `#language-toggle`, `#theme-toggle`; preferences are stored in `localStorage`.
- Prefer local media under `assets/`. Do not introduce runtime CDN CSS/fonts/scripts for core styling; external `https://` links are fine for papers, Scholar, project pages, etc.

### Design constraints (from the shipped site)

- Evidence-led editorial layout: warm paper/ink palette, restrained accent, no large top nav.
- Publication cards: teaser → title → authors (bold self) → venue/status → short summary → resource links.
- Animated paper media use `<picture>` with a static poster under `prefers-reduced-motion: reduce`.
- Keep the page self-contained for offline-friendly fonts and images.

## Deploy

Push to `origin/main`. GitHub Pages serves the repository root. No CI pipeline is defined in-repo.
