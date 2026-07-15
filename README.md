# Hongyu Ding Academic Homepage

Static academic homepage implementing the Evidence-Led Editorial design in `plan/2026-07-14-academic-homepage-design.md`. Production uses semantic HTML, one CSS file, local fonts and images, and no JavaScript.

## Preview

```bash
python3 -m http.server 4173 --bind 127.0.0.1 --directory /Users/dinghongyu/Downloads/hongyuding-home-page
```

Open `http://127.0.0.1:4173`.

## Prepare assets

```bash
.venv/bin/python scripts/prepare_assets.py
```

Asset preparation downloads hash-pinned font and paper sources, then regenerates reviewed local outputs. It verifies but never modifies the source portrait at `figs/ChatGPT Image 2026年6月29日 16_41_32.png`.

If an author-controlled project page does not provide a suitable official teaser, keep that publication text-only. Do not substitute an unrelated figure or a third-party image.

## Run content and asset tests

```bash
.venv/bin/python -m pytest tests/test_content.py tests/test_assets.py -q
```

## Run responsive browser tests

```bash
python3 "/Users/dinghongyu/.claude/skills/webapp-testing/scripts/with_server.py" \
  --server "python3 -m http.server 4173 --bind 127.0.0.1 --directory /Users/dinghongyu/Downloads/hongyuding-home-page" \
  --port 4173 \
  -- .venv/bin/python tests/test_visual.py
```

The Playwright gate checks responsive layout, local assets and fonts, keyboard focus, touch targets, reduced motion, narrow-print destinations, overflow, and rejection of external HTTP(S) requests. It writes four screenshots to `temp/homepage-review/`:

- `homepage-375.png`
- `homepage-768.png`
- `homepage-1280.png`
- `homepage-1920.png`
