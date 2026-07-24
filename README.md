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

Open `http://127.0.0.1:4173`.

## Editing content

1. Update English structure/copy in `index.html`.
2. Keep bilingual strings in sync in `assets/js/site.js` (`TRANSLATIONS`, keys via `data-i18n`).
3. Place new media under `assets/images/` (or `assets/images/papers/`, `assets/images/logos/`) and reference relative paths only. Served portrait: `assets/images/profile-hongyu-ding.webp`.
