# Hongyu Ding Academic Homepage

Static academic homepage for [Hongyu Ding](https://darkness-hy.github.io/), served via GitHub Pages.

## Stack

- Semantic HTML (`index.html`)
- One stylesheet (`assets/css/site.css`)
- Small client script for language + theme (`assets/js/site.js`)
- Local fonts and images under `assets/`

## Preview

```bash
python3 -m http.server 4173 --bind 127.0.0.1
```

Open `http://127.0.0.1:4173`. Skills catalog: `http://127.0.0.1:4173/skills/`.

## Editing content

1. Update English structure/copy in `index.html`.
2. Keep bilingual strings in sync in `assets/js/site.js` (`TRANSLATIONS`, keys via `data-i18n`).
3. Place new media under `assets/images/` (or `assets/images/papers/`, `assets/images/logos/`) and reference relative paths only. Served portrait: `assets/images/profile-hongyu-ding.webp`.
4. Homepage AI assistant (茜茜): UI in `assets/{css,js}/tutor.*` + `assets/tutor/`; server + RAG in `agent/` (see `agent/README.md`). Set `window.HOMEPAGE_AGENT_ENDPOINT` / `_HEALTH` to your deployed agent HTTPS URL.
5. Skills page (`/skills/`, also `skills.hongyuding.site`): source of truth is `../assets/skills/<name>/SKILL.md`. After adding or editing a skill, run `python3 skills/sync.py` from this repo to refresh `skills/catalog.json` and `skills/library/`. DNS for the subdomain should CNAME to the host that serves `agent/deploy/Caddyfile.full`.