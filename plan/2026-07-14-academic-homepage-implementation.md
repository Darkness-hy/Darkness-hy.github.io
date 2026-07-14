# Academic Homepage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a dependency-free, responsive academic homepage for Hongyu Ding that implements the approved Evidence-Led Editorial specification and passes content, asset, accessibility, and four-viewport browser checks.

**Architecture:** Use semantic static HTML for all public content and a single CSS file for the complete visual system. Keep JavaScript out of the production page. Use Python only for reproducible asset preparation and verification; all runtime assets are local.

**Tech Stack:** HTML5, CSS3, Python 3 virtual environment, Pillow, Beautiful Soup, Playwright, pytest, FontTools, macOS `tidy`, and the bundled `with_server.py` helper.

## Global Constraints

- Implement the approved specification at `plan/2026-07-14-academic-homepage-design.md`.
- Use the selected `Evidence-Led Editorial` direction.
- Use the source portrait `figs/ChatGPT Image 2026年6月29日 16_41_32.png` without modifying it.
- Public identity: `PhD Student at Nanjing University`.
- Public email: `hongyuding@smail.nju.edu.cn`.
- Scholar: `https://scholar.google.com/citations?user=IvWH8tcAAAAJ`.
- GitHub: `https://github.com/Darkness-hy`.
- Do not include a CV link.
- Show exactly five News entries, three Research themes, three Selected Publications, three compact Publications entries, and the Academic Service line `Details coming soon.`
- Show only verified Paper, Project, Code, and Video links specified in the design document.
- Do not add React, Tailwind, a build system, production JavaScript, analytics, cookies, dark mode, filters, generated robotics imagery, or out-of-scope sections.
- The page must work without JavaScript and without external runtime font or image requests.
- Test 375, 768, 1280, and 1920 px viewport widths with no horizontal overflow.
- Keep source files focused and below 400 lines where practical; no source file may exceed 800 lines.
- The workspace is not a Git repository. Do not initialize Git or create commits unless the user explicitly asks. Replace commit steps with file hashes and exact verification output.
- `uv` and ImageMagick are not available. Use `/usr/bin/python3`, a local `.venv`, Pillow, FontTools, `npx`, `/usr/bin/sips` only for inspection, and `/usr/bin/tidy`.

## File Map

```text
index.html
README.md
requirements-dev.txt
scripts/
└── prepare_assets.py
assets/
├── css/
│   └── site.css
├── fonts/
│   ├── newsreader-variable.woff2
│   ├── ibm-plex-sans-regular.woff2
│   ├── ibm-plex-sans-medium.woff2
│   ├── ibm-plex-sans-semibold.woff2
│   └── SHA256SUMS
└── images/
    ├── profile-hongyu-ding.webp
    └── papers/
        ├── uni-lavira.webp
        ├── lavira.webp
        └── mfrs.webp
tests/
├── test_assets.py
├── test_content.py
└── test_visual.py
temp/
└── homepage-review/            # generated screenshots; not production content
```

---

### Task 1: Establish the semantic content contract

**Files:**
- Create: `requirements-dev.txt`
- Create: `tests/test_content.py`
- Create: `index.html`

**Interfaces:**
- Consumes: Exact identity, copy, publication metadata, and URLs from the approved design specification.
- Produces: Stable DOM hooks used by later styling and browser tests: `.news-item`, `.research-theme`, `.publication-card`, `.publication-entry`, `.resource-links`, and section IDs.

- [ ] **Step 1: Create the reproducible development dependency list**

Create `requirements-dev.txt`:

```text
beautifulsoup4==4.13.4
Brotli==1.1.0
fonttools==4.59.0
Pillow==11.3.0
playwright==1.54.0
pytest==8.4.1
```

- [ ] **Step 2: Create and populate the local virtual environment**

Run:

```bash
cd /Users/dinghongyu/Downloads/hongyuding-home-page
/usr/bin/python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m playwright install chromium
```

Expected:

- `.venv/bin/python` exists.
- All six packages install without dependency errors.
- Playwright reports that Chromium is installed or already available.

- [ ] **Step 3: Write the failing content tests**

Create `tests/test_content.py`:

```python
"""Verify homepage structure, public copy, and link targets."""

from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "index.html"

EXPECTED_LINKS = {
    "mailto:hongyuding@smail.nju.edu.cn",
    "https://scholar.google.com/citations?user=IvWH8tcAAAAJ",
    "https://github.com/Darkness-hy",
    "https://arxiv.org/abs/2605.27582",
    "https://xetroubadour.github.io/Uni-LaViRA/",
    "https://github.com/NJU-R-L-Group-Embodied-Lab/uni-lavira-code",
    "https://arxiv.org/abs/2510.19655",
    "https://robo-lavira.github.io/lavira-zs-vln/",
    "https://github.com/NJU-R-L-Group-Embodied-Lab/lavira-code",
    "https://doi.org/10.1109/JAS.2023.123477",
    "https://hongyuding.wixsite.com/mfrs",
    "https://github.com/Darkness-hy/mfrs",
    "https://www.bilibili.com/video/BV1784y1z7Bj",
}


def _soup() -> BeautifulSoup:
    """Parse the production homepage."""
    return BeautifulSoup(INDEX_PATH.read_text(encoding="utf-8"), "html.parser")


def test_document_metadata() -> None:
    """Require title, description, Open Graph fields, and no fake canonical URL."""
    soup = _soup()
    assert soup.title is not None
    assert soup.title.get_text(strip=True) == (
        "Hongyu Ding — Embodied AI, Robotics, and Reinforcement Learning"
    )
    assert soup.select_one('meta[name="description"]') is not None
    assert soup.select_one('meta[property="og:title"]') is not None
    assert soup.select_one('meta[property="og:description"]') is not None
    assert soup.select_one('meta[property="og:image"]') is not None
    assert soup.select_one('link[rel="canonical"]') is None


def test_heading_and_landmark_structure() -> None:
    """Require semantic landmarks and a single page heading."""
    soup = _soup()
    assert soup.select_one("header") is not None
    assert soup.select_one("main#main") is not None
    assert soup.select_one("footer") is not None
    headings = soup.select("h1")
    assert len(headings) == 1
    assert headings[0].get_text(" ", strip=True) == "Hongyu Ding"
    assert soup.select_one('a.skip-link[href="#main"]') is not None


def test_required_content_counts() -> None:
    """Keep the first release within the approved section scope."""
    soup = _soup()
    assert len(soup.select(".news-item")) == 5
    assert len(soup.select(".research-theme")) == 3
    assert len(soup.select(".publication-card")) == 3
    assert len(soup.select(".publication-entry")) == 3
    assert soup.select_one("#academic-service") is not None
    assert "Details coming soon." in soup.select_one("#academic-service").get_text(
        " ", strip=True
    )


def test_public_identity_and_scope() -> None:
    """Expose confirmed identity and omit excluded CV content."""
    text = _soup().get_text(" ", strip=True)
    assert "PhD Student at Nanjing University" in text
    assert "I study embodied intelligence" in text
    assert "CV" not in text
    assert "Awards" not in text
    assert "Teaching" not in text


def test_verified_link_targets() -> None:
    """Require every approved destination and reject empty links."""
    soup = _soup()
    hrefs = {
        str(anchor.get("href"))
        for anchor in soup.select("a[href]")
        if str(anchor.get("href")).startswith(("http", "mailto:"))
    }
    assert EXPECTED_LINKS <= hrefs
    assert all(href not in {"", "#", "None"} for href in hrefs)
    assert all("TODO" not in href for href in hrefs)


def test_resource_labels_match_available_artifacts() -> None:
    """Do not advertise unverified video or dataset links."""
    soup = _soup()
    cards = soup.select(".publication-card")
    labels = [
        {link.get_text(" ", strip=True) for link in card.select(".resource-links a")}
        for card in cards
    ]
    assert labels[0] == {"Paper", "Project", "Code"}
    assert labels[1] == {"Paper", "Project", "Code"}
    assert labels[2] == {"Paper", "Project", "Code", "Video"}
    assert "Dataset" not in soup.get_text(" ", strip=True)
```

- [ ] **Step 4: Run the content tests and verify the expected failure**

Run:

```bash
.venv/bin/python -m pytest tests/test_content.py -q
```

Expected: FAIL because `index.html` does not exist.

- [ ] **Step 5: Implement the semantic homepage**

Create `index.html`:

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Hongyu Ding — Embodied AI, Robotics, and Reinforcement Learning</title>
  <meta name="description" content="Hongyu Ding is a PhD student at Nanjing University working on embodied intelligence, language–vision–action translation, navigation, and reinforcement learning.">
  <meta property="og:type" content="website">
  <meta property="og:title" content="Hongyu Ding — Embodied AI, Robotics, and Reinforcement Learning">
  <meta property="og:description" content="Research on embodied intelligence, language–vision–action translation, navigation, and reinforcement learning.">
  <meta property="og:image" content="assets/images/profile-hongyu-ding.webp">
  <link rel="stylesheet" href="assets/css/site.css">
</head>
<body>
  <a class="skip-link" href="#main">Skip to content</a>

  <div class="page-shell">
    <header class="site-header" aria-labelledby="page-title">
      <div class="hero">
        <div class="hero__copy">
          <p class="eyebrow">Embodied AI · Robotics · Reinforcement Learning</p>
          <h1 id="page-title">Hongyu Ding</h1>
          <p class="role">PhD Student at Nanjing University</p>
          <p class="thesis">I study embodied intelligence, focusing on how language, vision, and robot actions can be translated into unified navigation and decision-making systems.</p>
          <p class="bio">I am a PhD student at Nanjing University. My research lies at the intersection of embodied AI, robotics, and reinforcement learning. I study how language, vision, and robot actions can be translated into unified navigation and decision-making systems, with a focus on training-free adaptation, zero-shot generalization, and structured learning signals for agents operating in continuous environments.</p>
          <nav class="contact-links" aria-label="Profile links">
            <a href="mailto:hongyuding@smail.nju.edu.cn">Email</a>
            <a href="https://scholar.google.com/citations?user=IvWH8tcAAAAJ">Scholar</a>
            <a href="https://github.com/Darkness-hy">GitHub</a>
          </nav>
        </div>
        <figure class="hero__portrait">
          <img src="assets/images/profile-hongyu-ding.webp" width="720" height="900" alt="Portrait of Hongyu Ding." fetchpriority="high">
        </figure>
      </div>
    </header>

    <main id="main">
      <section class="section" id="news" aria-labelledby="news-title">
        <div class="section-heading">
          <span class="section-number" aria-hidden="true">01</span>
          <h2 id="news-title">News</h2>
        </div>
        <ol class="news-list">
          <li class="news-item">
            <time datetime="2026-05">May 2026</time>
            <p>Released <a href="https://xetroubadour.github.io/Uni-LaViRA/">Uni-LaViRA</a>, a training-free framework for unified embodied navigation, with a paper, project page, and code.</p>
          </li>
          <li class="news-item">
            <time datetime="2026-03">March 2026</time>
            <p>Updated <a href="https://robo-lavira.github.io/lavira-zs-vln/">LaViRA</a> with its ICRA 2026 version for zero-shot vision-language navigation in continuous environments.</p>
          </li>
          <li class="news-item">
            <time datetime="2025-10">October 2025</time>
            <p>Released <a href="https://arxiv.org/abs/2510.19655">LaViRA</a> with its paper, project page, and code.</p>
          </li>
          <li class="news-item">
            <time datetime="2023-12">December 2023</time>
            <p><a href="https://doi.org/10.1109/JAS.2023.123477">Magnetic Field-Based Reward Shaping</a> appeared in IEEE/CAA Journal of Automatica Sinica, volume 10, issue 12.</p>
          </li>
          <li class="news-item">
            <time datetime="2023-07">July 2023</time>
            <p>Magnetic Field-Based Reward Shaping became available online with project, code, and supplementary-video resources.</p>
          </li>
        </ol>
      </section>

      <section class="section" id="research" aria-labelledby="research-title">
        <div class="section-heading">
          <span class="section-number" aria-hidden="true">02</span>
          <h2 id="research-title">Research</h2>
        </div>
        <div class="research-grid">
          <article class="research-theme">
            <p class="theme-number">01</p>
            <h3>Language–Vision–Action Translation</h3>
            <p>Translating knowledge expressed through language and visual representations into robot actions without retraining a separate policy for every task.</p>
          </article>
          <article class="research-theme">
            <p class="theme-number">02</p>
            <h3>Unified Embodied Navigation</h3>
            <p>Building interfaces that let embodied agents address multiple navigation settings and continuous environments through a shared action-translation perspective.</p>
          </article>
          <article class="research-theme">
            <p class="theme-number">03</p>
            <h3>Goal-Conditioned Reinforcement Learning</h3>
            <p>Designing structured learning signals that improve exploration and decision-making when rewards are sparse and goals vary across episodes.</p>
          </article>
        </div>
      </section>

      <section class="section" id="selected-publications" aria-labelledby="selected-title">
        <div class="section-heading">
          <span class="section-number" aria-hidden="true">03</span>
          <h2 id="selected-title">Selected Publications</h2>
        </div>

        <div class="publication-cards">
          <article class="publication-card publication-card--featured">
            <figure class="publication-card__media">
              <img src="assets/images/papers/uni-lavira.webp" width="960" height="540" loading="lazy" alt="Uni-LaViRA unified embodied navigation overview.">
            </figure>
            <div class="publication-card__body">
              <p class="publication-status">arXiv · 2026</p>
              <h3><a href="https://arxiv.org/abs/2605.27582">Uni-LaViRA: Language-Vision-Robot Actions Translation for Unified Embodied Navigation</a></h3>
              <p class="authors"><strong>Hongyu Ding</strong>, Sizhuo Zhang, Ziming Xu, Jinwen Guo, Hongxiu Liu, Xingzhi Cheng, Zixuan Chen, Haifei Qi, Duo Wang, Hao Xu, Jieqi Shi, Yifan Zhang, Jing Huo, Jian Cheng, Yang Gao, Jiebo Luo</p>
              <p class="publication-summary">Training-free unified embodied navigation through language–vision–robot action translation.</p>
              <p class="resource-links"><a href="https://arxiv.org/abs/2605.27582">Paper</a><a href="https://xetroubadour.github.io/Uni-LaViRA/">Project</a><a href="https://github.com/NJU-R-L-Group-Embodied-Lab/uni-lavira-code">Code</a></p>
            </div>
          </article>

          <article class="publication-card">
            <figure class="publication-card__media">
              <img src="assets/images/papers/lavira.webp" width="960" height="540" loading="lazy" alt="LaViRA zero-shot continuous navigation overview.">
            </figure>
            <div class="publication-card__body">
              <p class="publication-status">ICRA · 2026</p>
              <h3><a href="https://arxiv.org/abs/2510.19655">LaViRA: Language-Vision-Robot Actions Translation for Zero-Shot Vision Language Navigation in Continuous Environments</a></h3>
              <p class="authors"><strong>Hongyu Ding</strong>, Ziming Xu, Yudong Fang, You Wu, Zixuan Chen, Jieqi Shi, Jing Huo, Yifan Zhang, Yang Gao</p>
              <p class="publication-summary">Zero-shot continuous navigation through language–vision–robot action translation.</p>
              <p class="resource-links"><a href="https://arxiv.org/abs/2510.19655">Paper</a><a href="https://robo-lavira.github.io/lavira-zs-vln/">Project</a><a href="https://github.com/NJU-R-L-Group-Embodied-Lab/lavira-code">Code</a></p>
            </div>
          </article>

          <article class="publication-card">
            <figure class="publication-card__media">
              <img src="assets/images/papers/mfrs.webp" width="960" height="540" loading="lazy" alt="Magnetic field-based reward shaping method overview.">
            </figure>
            <div class="publication-card__body">
              <p class="publication-status">IEEE/CAA JAS · 2023</p>
              <h3><a href="https://doi.org/10.1109/JAS.2023.123477">Magnetic Field-Based Reward Shaping for Goal-Conditioned Reinforcement Learning</a></h3>
              <p class="authors"><strong>Hongyu Ding</strong>, Yuanze Tang, Qing Wu, Bo Wang, Chunlin Chen, Zhi Wang</p>
              <p class="publication-summary">Magnetic-field-inspired rewards for efficient goal-conditioned reinforcement learning.</p>
              <p class="resource-links"><a href="https://doi.org/10.1109/JAS.2023.123477">Paper</a><a href="https://hongyuding.wixsite.com/mfrs">Project</a><a href="https://github.com/Darkness-hy/mfrs">Code</a><a href="https://www.bilibili.com/video/BV1784y1z7Bj">Video</a></p>
            </div>
          </article>
        </div>
      </section>

      <section class="section" id="publications" aria-labelledby="publications-title">
        <div class="section-heading">
          <span class="section-number" aria-hidden="true">04</span>
          <h2 id="publications-title">Publications</h2>
        </div>
        <div class="publication-year">
          <h3>2026</h3>
          <ul class="publication-list">
            <li class="publication-entry"><a href="https://arxiv.org/abs/2605.27582">Uni-LaViRA: Language-Vision-Robot Actions Translation for Unified Embodied Navigation</a>. Hongyu Ding et al. arXiv, 2026.</li>
            <li class="publication-entry"><a href="https://arxiv.org/abs/2510.19655">LaViRA: Language-Vision-Robot Actions Translation for Zero-Shot Vision Language Navigation in Continuous Environments</a>. Hongyu Ding et al. ICRA, 2026.</li>
          </ul>
        </div>
        <div class="publication-year">
          <h3>2023</h3>
          <ul class="publication-list">
            <li class="publication-entry"><a href="https://doi.org/10.1109/JAS.2023.123477">Magnetic Field-Based Reward Shaping for Goal-Conditioned Reinforcement Learning</a>. Hongyu Ding, Yuanze Tang, Qing Wu, Bo Wang, Chunlin Chen, and Zhi Wang. IEEE/CAA Journal of Automatica Sinica, 10(12):2233–2247, 2023.</li>
          </ul>
        </div>
      </section>

      <section class="section" id="academic-service" aria-labelledby="service-title">
        <div class="section-heading">
          <span class="section-number" aria-hidden="true">05</span>
          <h2 id="service-title">Academic Service</h2>
        </div>
        <p class="service-note">Details coming soon.</p>
      </section>
    </main>

    <footer class="site-footer">
      <p>© 2026 Hongyu Ding</p>
      <p>Last updated July 2026</p>
    </footer>
  </div>
</body>
</html>
```

- [ ] **Step 6: Run the content tests and verify they pass**

Run:

```bash
.venv/bin/python -m pytest tests/test_content.py -q
```

Expected: `6 passed`.

- [ ] **Step 7: Record a non-Git checkpoint**

Run:

```bash
shasum -a 256 index.html requirements-dev.txt tests/test_content.py
```

Expected: three SHA-256 lines. Copy them into the task log if execution is interrupted.

---

### Task 2: Prepare local fonts, portrait, and official paper media

**Files:**
- Create: `scripts/prepare_assets.py`
- Create: `tests/test_assets.py`
- Create: `assets/fonts/*.woff2`
- Create: `assets/fonts/SHA256SUMS`
- Create: `assets/images/profile-hongyu-ding.webp`
- Create when an official image is found: `assets/images/papers/*.webp`
- Modify conditionally: `index.html` only when an official paper image cannot be retrieved

**Interfaces:**
- Consumes: Portrait source path and three official project-page URLs.
- Produces: Local WOFF2 fonts, a 720×900 portrait, and up to three 960×540 real paper images. `site.css` consumes the font filenames; `index.html` consumes the image filenames.

- [ ] **Step 1: Write the failing asset tests**

Create `tests/test_assets.py`:

```python
"""Verify local font and image assets referenced by the homepage."""

from pathlib import Path

from bs4 import BeautifulSoup
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = ROOT / "assets" / "fonts"
IMAGE_DIR = ROOT / "assets" / "images"
INDEX_PATH = ROOT / "index.html"

EXPECTED_FONTS = {
    "newsreader-variable.woff2",
    "ibm-plex-sans-regular.woff2",
    "ibm-plex-sans-medium.woff2",
    "ibm-plex-sans-semibold.woff2",
}


def test_font_files_exist_and_are_nonempty() -> None:
    """Require every self-hosted production font."""
    for filename in EXPECTED_FONTS:
        path = FONT_DIR / filename
        assert path.exists(), filename
        assert path.stat().st_size > 10_000, filename


def test_profile_crop_is_exact() -> None:
    """Require the approved 4:5 portrait export."""
    path = IMAGE_DIR / "profile-hongyu-ding.webp"
    assert path.exists()
    with Image.open(path) as image:
        assert image.format == "WEBP"
        assert image.size == (720, 900)


def test_every_referenced_local_image_loads() -> None:
    """Allow text-only papers, but reject broken local image references."""
    soup = BeautifulSoup(INDEX_PATH.read_text(encoding="utf-8"), "html.parser")
    sources = [
        str(image["src"])
        for image in soup.select('img[src^="assets/images/"]')
    ]
    assert "assets/images/profile-hongyu-ding.webp" in sources
    for source in sources:
        path = ROOT / source
        assert path.exists(), source
        with Image.open(path) as image:
            assert image.width > 0
            assert image.height > 0


def test_paper_media_are_realistic_web_images() -> None:
    """Keep referenced paper images large enough for publication cards."""
    soup = BeautifulSoup(INDEX_PATH.read_text(encoding="utf-8"), "html.parser")
    for image_tag in soup.select(".publication-card__media img"):
        path = ROOT / str(image_tag["src"])
        with Image.open(path) as image:
            assert image.format == "WEBP"
            assert image.width >= 900
            assert image.height >= 500
```

- [ ] **Step 2: Run the asset tests and verify the expected failure**

Run:

```bash
.venv/bin/python -m pytest tests/test_assets.py -q
```

Expected: FAIL because the production font and image files do not exist.

- [ ] **Step 3: Implement the reproducible asset-preparation script**

Create `scripts/prepare_assets.py`:

```python
"""Prepare local homepage fonts and images from approved public sources."""

from __future__ import annotations

import logging
from io import BytesIO
from pathlib import Path
from typing import Final
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup
from fontTools.ttLib import TTFont
from PIL import Image, ImageOps

LOGGER = logging.getLogger(__name__)
ROOT: Final = Path(__file__).resolve().parents[1]
FONT_DIR: Final = ROOT / "assets" / "fonts"
IMAGE_DIR: Final = ROOT / "assets" / "images"
PAPER_DIR: Final = IMAGE_DIR / "papers"
PORTRAIT_SOURCE: Final = ROOT / "figs" / "ChatGPT Image 2026年6月29日 16_41_32.png"
USER_AGENT: Final = "Mozilla/5.0 (compatible; HongyuDingHomepageAssetPrep/1.0)"

FONT_SOURCES: Final = {
    "newsreader-variable.woff2": (
        "https://raw.githubusercontent.com/google/fonts/main/ofl/newsreader/"
        "Newsreader%5Bopsz%2Cwght%5D.ttf"
    ),
    "ibm-plex-sans-regular.woff2": (
        "https://raw.githubusercontent.com/IBM/plex/master/packages/plex-sans/"
        "fonts/complete/ttf/IBMPlexSans-Regular.ttf"
    ),
    "ibm-plex-sans-medium.woff2": (
        "https://raw.githubusercontent.com/IBM/plex/master/packages/plex-sans/"
        "fonts/complete/ttf/IBMPlexSans-Medium.ttf"
    ),
    "ibm-plex-sans-semibold.woff2": (
        "https://raw.githubusercontent.com/IBM/plex/master/packages/plex-sans/"
        "fonts/complete/ttf/IBMPlexSans-SemiBold.ttf"
    ),
}

PROJECT_PAGES: Final = {
    "uni-lavira.webp": "https://xetroubadour.github.io/Uni-LaViRA/",
    "lavira.webp": "https://robo-lavira.github.io/lavira-zs-vln/",
    "mfrs.webp": "https://hongyuding.wixsite.com/mfrs",
}


def _download(url: str) -> bytes:
    """Download a public asset with a browser-like user agent."""
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=30) as response:
            return response.read()
    except OSError as exc:
        LOGGER.error("Failed to download %s: %s", url, exc)
        raise


def _convert_font(url: str, destination: Path) -> None:
    """Convert an official TTF font source to browser-ready WOFF2."""
    font = TTFont(BytesIO(_download(url)))
    font.flavor = "woff2"
    font.save(destination)


def _prepare_fonts() -> None:
    """Create every self-hosted font required by the stylesheet."""
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    for filename, url in FONT_SOURCES.items():
        destination = FONT_DIR / filename
        LOGGER.info("Preparing font %s", destination.name)
        _convert_font(url, destination)


def _prepare_portrait() -> None:
    """Export the approved crop without changing the original portrait."""
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    with Image.open(PORTRAIT_SOURCE) as source:
        rgb = source.convert("RGB")
        crop = rgb.crop((199, 430, 919, 1330))
        if crop.size != (720, 900):
            raise ValueError(f"Unexpected portrait crop size: {crop.size}")
        crop.save(
            IMAGE_DIR / "profile-hongyu-ding.webp",
            "WEBP",
            quality=90,
            method=6,
        )


def _candidate_image_urls(page_url: str) -> list[str]:
    """Collect author-controlled image candidates from a project page."""
    html = _download(page_url).decode("utf-8", errors="replace")
    soup = BeautifulSoup(html, "html.parser")
    candidates: list[str] = []
    for selector, attribute in (
        ('meta[property="og:image"]', "content"),
        ('meta[name="twitter:image"]', "content"),
    ):
        tag = soup.select_one(selector)
        if tag and tag.get(attribute):
            candidates.append(urljoin(page_url, str(tag[attribute])))
    for image in soup.select("img[src]"):
        source = urljoin(page_url, str(image["src"]))
        if source.startswith("http"):
            candidates.append(source)
    return list(dict.fromkeys(candidates))


def _select_teaser(page_url: str) -> Image.Image | None:
    """Choose the largest plausible editorial teaser from a project page."""
    best_image: Image.Image | None = None
    best_area = 0
    for url in _candidate_image_urls(page_url)[:24]:
        try:
            with Image.open(BytesIO(_download(url))) as candidate:
                image = candidate.convert("RGB")
        except (OSError, ValueError):
            continue
        width, height = image.size
        ratio = width / height if height else 0.0
        area = width * height
        if width < 600 or height < 300 or not 1.2 <= ratio <= 2.6:
            continue
        if area > best_area:
            best_image = image.copy()
            best_area = area
    return best_image


def _prepare_paper_media() -> list[str]:
    """Export real project imagery and report pages that need text-only rows."""
    PAPER_DIR.mkdir(parents=True, exist_ok=True)
    missing: list[str] = []
    for filename, page_url in PROJECT_PAGES.items():
        LOGGER.info("Inspecting project media for %s", page_url)
        teaser = _select_teaser(page_url)
        if teaser is None:
            LOGGER.warning("No suitable teaser found for %s", page_url)
            missing.append(filename)
            continue
        fitted = ImageOps.fit(
            teaser,
            (960, 540),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        )
        fitted.save(PAPER_DIR / filename, "WEBP", quality=88, method=6)
    return missing


def main() -> int:
    """Prepare all local assets and print deterministic fallback actions."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    _prepare_fonts()
    _prepare_portrait()
    missing = _prepare_paper_media()
    if missing:
        LOGGER.warning(
            "Use text-only publication markup for missing files: %s",
            ", ".join(missing),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Generate the local assets**

Run:

```bash
.venv/bin/python scripts/prepare_assets.py
```

Expected:

- Four WOFF2 files exist under `assets/fonts/`.
- `assets/images/profile-hongyu-ding.webp` is 720×900.
- Each project page that exposes a suitable official image produces a 960×540 WebP.
- Any missing paper image is named explicitly in a warning.

- [ ] **Step 5: Apply the exact text-only fallback for any named missing paper image**

For each filename reported missing, remove only that card’s `<figure class="publication-card__media">…</figure>` block and change:

```html
<article class="publication-card">
```

or:

```html
<article class="publication-card publication-card--featured">
```

to include `publication-card--text-only`, for example:

```html
<article class="publication-card publication-card--text-only">
```

For the featured Uni-LaViRA card, preserve both modifiers:

```html
<article class="publication-card publication-card--featured publication-card--text-only">
```

Do not create a generic illustration, title card, gradient placeholder, or stock robot image.

- [ ] **Step 6: Create font checksums**

Run:

```bash
cd assets/fonts
shasum -a 256 *.woff2 > SHA256SUMS
cd ../..
```

Expected: `assets/fonts/SHA256SUMS` contains four lines.

- [ ] **Step 7: Run the asset tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_assets.py -q
```

Expected: `4 passed`.

- [ ] **Step 8: Visually inspect the prepared images before styling**

Open the generated portrait and every existing paper WebP with the file viewer. Confirm:

- Portrait does not crop hair, glasses, ears, chin, or shoulders.
- Paper images are real project-page media and not logos, navigation graphics, or unrelated site decoration.
- Cropping preserves the main robot/task/result content.

If a selected image is wrong, delete only that paper WebP and apply the text-only fallback from Step 5.

---

### Task 3: Implement the complete Evidence-Led Editorial stylesheet

**Files:**
- Create: `tests/test_visual.py`
- Create: `assets/css/site.css`
- Create at runtime: `temp/homepage-review/*.png`

**Interfaces:**
- Consumes: DOM hooks from Task 1 and local assets from Task 2.
- Produces: Responsive visual behavior at four target widths, visible focus states, font loading, print rules, and screenshot evidence.

- [ ] **Step 1: Write the failing browser verification script**

Create `tests/test_visual.py`:

```python
"""Run real-browser responsive and accessibility smoke checks."""

from pathlib import Path

from playwright.sync_api import Browser, Page, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SCREENSHOT_DIR = ROOT / "temp" / "homepage-review"
BASE_URL = "http://127.0.0.1:4173"
VIEWPORTS = (375, 768, 1280, 1920)


def _assert_page(page: Page, width: int) -> None:
    """Verify one rendered viewport."""
    console_errors: list[str] = []
    page.on(
        "console",
        lambda message: console_errors.append(message.text)
        if message.type == "error"
        else None,
    )
    page.set_viewport_size({"width": width, "height": 1000})
    page.goto(BASE_URL, wait_until="networkidle")
    page.evaluate("document.fonts.ready")

    dimensions = page.evaluate(
        """() => ({
            scrollWidth: document.documentElement.scrollWidth,
            clientWidth: document.documentElement.clientWidth
        })"""
    )
    assert dimensions["scrollWidth"] <= dimensions["clientWidth"], (
        width,
        dimensions,
    )
    assert page.locator("h1").inner_text() == "Hongyu Ding"
    assert page.locator(".news-item").count() == 5
    assert page.locator(".research-theme").count() == 3
    assert page.locator(".publication-card").count() == 3
    assert page.locator(".publication-entry").count() == 3
    assert page.locator("img").evaluate_all(
        "images => images.every(image => image.complete && image.naturalWidth > 0)"
    )
    assert page.evaluate("document.fonts.check(\"16px 'IBM Plex Sans'\")")
    assert page.evaluate("document.fonts.check(\"32px 'Newsreader'\")")
    assert not console_errors, console_errors

    page.keyboard.press("Tab")
    focus_style = page.evaluate(
        """() => {
            const style = getComputedStyle(document.activeElement);
            return {outlineStyle: style.outlineStyle, outlineWidth: style.outlineWidth};
        }"""
    )
    assert focus_style["outlineStyle"] != "none"
    assert focus_style["outlineWidth"] != "0px"

    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    page.screenshot(
        path=str(SCREENSHOT_DIR / f"homepage-{width}.png"),
        full_page=True,
    )


def _assert_reduced_motion(browser: Browser) -> None:
    """Verify the page defines no required motion in reduced-motion mode."""
    context = browser.new_context(reduced_motion="reduce")
    page = context.new_page()
    page.goto(BASE_URL, wait_until="networkidle")
    assert page.evaluate("document.getAnimations().length") == 0
    context.close()


def main() -> int:
    """Run all browser checks and save viewport evidence."""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        for width in VIEWPORTS:
            _assert_page(page, width)
        _assert_reduced_motion(browser)
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run the browser check and verify the expected failure**

Run:

```bash
python3 "/Users/dinghongyu/.claude/skills/webapp-testing/scripts/with_server.py" \
  --server "python3 -m http.server 4173 --directory /Users/dinghongyu/Downloads/hongyuding-home-page" \
  --port 4173 \
  -- .venv/bin/python tests/test_visual.py
```

Expected: FAIL because `assets/css/site.css` does not exist and the page is not styled to the approved layout.

- [ ] **Step 3: Implement the production stylesheet**

Create `assets/css/site.css`:

```css
@font-face {
  font-family: "Newsreader";
  src: url("../fonts/newsreader-variable.woff2") format("woff2");
  font-style: normal;
  font-weight: 400 600;
  font-display: swap;
}

@font-face {
  font-family: "IBM Plex Sans";
  src: url("../fonts/ibm-plex-sans-regular.woff2") format("woff2");
  font-style: normal;
  font-weight: 400;
  font-display: swap;
}

@font-face {
  font-family: "IBM Plex Sans";
  src: url("../fonts/ibm-plex-sans-medium.woff2") format("woff2");
  font-style: normal;
  font-weight: 500;
  font-display: swap;
}

@font-face {
  font-family: "IBM Plex Sans";
  src: url("../fonts/ibm-plex-sans-semibold.woff2") format("woff2");
  font-style: normal;
  font-weight: 600;
  font-display: swap;
}

:root {
  --color-paper: #f6f2e9;
  --color-surface: #fbf9f4;
  --color-ink: #202522;
  --color-muted: #5f6863;
  --color-accent: #8f4636;
  --color-line: #d8d1c5;
  --color-highlight: #eee3d8;
  --color-focus: #2d5f85;
  --font-display: "Newsreader", Georgia, serif;
  --font-body: "IBM Plex Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  --page-width: 940px;
  --radius-image: 14px;
}

*,
*::before,
*::after {
  box-sizing: border-box;
}

html {
  color-scheme: light;
  scroll-behavior: smooth;
}

body {
  margin: 0;
  background: var(--color-paper);
  color: var(--color-ink);
  font-family: var(--font-body);
  font-size: 1.025rem;
  line-height: 1.65;
  text-rendering: optimizeLegibility;
}

img {
  display: block;
  max-width: 100%;
  height: auto;
}

p,
h1,
h2,
h3,
figure,
ol,
ul {
  margin-top: 0;
}

a {
  color: var(--color-accent);
  text-decoration-color: color-mix(in srgb, var(--color-accent), transparent 45%);
  text-decoration-thickness: 0.08em;
  text-underline-offset: 0.2em;
}

a:hover {
  text-decoration-color: currentColor;
}

a:focus-visible {
  outline: 3px solid var(--color-focus);
  outline-offset: 4px;
  border-radius: 2px;
}

.skip-link {
  position: fixed;
  z-index: 10;
  top: 1rem;
  left: 1rem;
  padding: 0.7rem 1rem;
  transform: translateY(-160%);
  background: var(--color-ink);
  color: var(--color-surface);
}

.skip-link:focus {
  transform: translateY(0);
}

.page-shell {
  width: min(calc(100% - 48px), var(--page-width));
  margin-inline: auto;
}

.site-header {
  padding: 5.5rem 0 4.5rem;
}

.hero {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(240px, 1fr);
  gap: clamp(2.5rem, 6vw, 5rem);
  align-items: center;
}

.eyebrow,
.role,
.publication-status,
.theme-number,
.section-number,
time {
  color: var(--color-muted);
  font-size: 0.84rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.eyebrow {
  margin-bottom: 1.1rem;
}

h1,
h2 {
  font-family: var(--font-display);
  font-weight: 500;
  letter-spacing: -0.035em;
}

h1 {
  max-width: 10ch;
  margin-bottom: 0.6rem;
  font-size: clamp(3.5rem, 8vw, 5.5rem);
  line-height: 0.94;
}

.role {
  margin-bottom: 1.7rem;
  color: var(--color-accent);
}

.thesis {
  max-width: 34ch;
  margin-bottom: 1.4rem;
  font-family: var(--font-display);
  font-size: clamp(1.35rem, 2.4vw, 1.75rem);
  line-height: 1.35;
}

.bio {
  max-width: 63ch;
  color: var(--color-muted);
}

.contact-links,
.resource-links {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem 1.15rem;
}

.contact-links {
  margin-top: 1.8rem;
}

.contact-links a,
.resource-links a {
  font-weight: 600;
}

.hero__portrait {
  margin: 0;
}

.hero__portrait img {
  width: 100%;
  aspect-ratio: 4 / 5;
  object-fit: cover;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-image);
}

.section {
  padding: 4.5rem 0;
  border-top: 1px solid var(--color-line);
}

.section-heading {
  display: grid;
  grid-template-columns: 48px 1fr;
  gap: 1rem;
  align-items: baseline;
  margin-bottom: 2.5rem;
}

.section-heading h2 {
  margin-bottom: 0;
  font-size: clamp(2rem, 4vw, 2.7rem);
  line-height: 1.05;
}

.news-list,
.publication-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.news-item {
  display: grid;
  grid-template-columns: 130px 1fr;
  gap: 1.5rem;
  padding: 1rem 0;
  border-top: 1px solid color-mix(in srgb, var(--color-line), transparent 35%);
}

.news-item:first-child {
  border-top: 0;
}

.news-item p {
  margin-bottom: 0;
}

.research-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0;
}

.research-theme {
  padding: 0 1.5rem;
  border-left: 1px solid var(--color-line);
}

.research-theme:first-child {
  padding-left: 0;
  border-left: 0;
}

.research-theme:last-child {
  padding-right: 0;
}

.research-theme h3 {
  margin-bottom: 0.8rem;
  font-size: 1.15rem;
  line-height: 1.35;
}

.research-theme p:last-child {
  margin-bottom: 0;
  color: var(--color-muted);
}

.publication-cards {
  display: grid;
  gap: 0;
}

.publication-card {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  gap: clamp(1.5rem, 4vw, 2.5rem);
  padding: 2rem 0;
  border-top: 1px solid var(--color-line);
}

.publication-card:first-child {
  border-top: 0;
}

.publication-card--featured {
  margin-inline: -1rem;
  padding-inline: 1rem;
  background: var(--color-highlight);
  border-radius: 12px;
}

.publication-card--text-only {
  grid-template-columns: 1fr;
}

.publication-card__media {
  margin: 0;
}

.publication-card__media img {
  width: 100%;
  aspect-ratio: 16 / 9;
  object-fit: cover;
  border: 1px solid var(--color-line);
  border-radius: 10px;
}

.publication-card h3 {
  margin-bottom: 0.55rem;
  font-size: clamp(1.15rem, 2vw, 1.32rem);
  line-height: 1.35;
}

.publication-card h3 a {
  color: var(--color-ink);
  text-decoration-color: color-mix(in srgb, var(--color-accent), transparent 55%);
}

.authors,
.publication-summary,
.publication-status {
  margin-bottom: 0.75rem;
}

.authors {
  color: var(--color-muted);
  font-size: 0.93rem;
  line-height: 1.55;
}

.authors strong {
  color: var(--color-ink);
}

.publication-summary {
  max-width: 58ch;
}

.resource-links {
  margin-bottom: 0;
  font-size: 0.92rem;
}

.publication-year + .publication-year {
  margin-top: 2.3rem;
}

.publication-year h3 {
  margin-bottom: 0.8rem;
  color: var(--color-accent);
  font-size: 1rem;
}

.publication-entry {
  padding: 0.75rem 0;
  border-top: 1px solid color-mix(in srgb, var(--color-line), transparent 35%);
}

.publication-entry:first-child {
  border-top: 0;
}

.service-note {
  margin-bottom: 0;
  color: var(--color-muted);
  font-style: italic;
}

.site-footer {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  padding: 2rem 0 3rem;
  border-top: 1px solid var(--color-line);
  color: var(--color-muted);
  font-size: 0.86rem;
}

.site-footer p {
  margin-bottom: 0;
}

@media (max-width: 900px) {
  .site-header {
    padding-top: 4rem;
  }

  .hero {
    grid-template-columns: minmax(0, 1.8fr) minmax(210px, 1fr);
    gap: 2.5rem;
  }

  .publication-card {
    grid-template-columns: 190px minmax(0, 1fr);
  }
}

@media (max-width: 700px) {
  .page-shell {
    width: min(calc(100% - 36px), var(--page-width));
  }

  .site-header {
    padding: 3rem 0 3.5rem;
  }

  .hero,
  .publication-card,
  .publication-card--text-only {
    grid-template-columns: 1fr;
  }

  .hero__portrait {
    max-width: 420px;
  }

  .section {
    padding: 3.5rem 0;
  }

  .research-grid {
    grid-template-columns: 1fr;
  }

  .research-theme,
  .research-theme:first-child,
  .research-theme:last-child {
    padding: 1.4rem 0;
    border-top: 1px solid var(--color-line);
    border-left: 0;
  }

  .research-theme:first-child {
    padding-top: 0;
    border-top: 0;
  }

  .publication-card {
    gap: 1.25rem;
  }

  .publication-card--featured {
    margin-inline: 0;
  }
}

@media (max-width: 520px) {
  body {
    font-size: 1rem;
  }

  .section-heading {
    grid-template-columns: 36px 1fr;
  }

  .news-item {
    grid-template-columns: 1fr;
    gap: 0.3rem;
  }

  .contact-links a,
  .resource-links a {
    display: inline-flex;
    min-height: 44px;
    align-items: center;
  }

  .site-footer {
    flex-direction: column;
  }
}

@media (prefers-reduced-motion: reduce) {
  html {
    scroll-behavior: auto;
  }

  *,
  *::before,
  *::after {
    scroll-behavior: auto !important;
    transition-duration: 0.01ms !important;
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
  }
}

@media print {
  :root {
    --color-paper: #ffffff;
    --color-surface: #ffffff;
    --color-ink: #000000;
    --color-muted: #333333;
    --color-line: #b8b8b8;
    --color-highlight: #f2f2f2;
  }

  body {
    font-size: 10.5pt;
  }

  .page-shell {
    width: 100%;
  }

  .site-header,
  .section {
    padding: 1.5rem 0;
  }

  .skip-link,
  .hero__portrait,
  .publication-card__media {
    display: none;
  }

  a {
    color: inherit;
    text-decoration: underline;
  }

  .publication-card,
  .research-grid {
    display: block;
  }

  .research-theme,
  .publication-card {
    break-inside: avoid;
    padding: 0.8rem 0;
  }
}
```

- [ ] **Step 4: Run the browser verification**

Run:

```bash
python3 "/Users/dinghongyu/.claude/skills/webapp-testing/scripts/with_server.py" \
  --server "python3 -m http.server 4173 --directory /Users/dinghongyu/Downloads/hongyuding-home-page" \
  --port 4173 \
  -- .venv/bin/python tests/test_visual.py
```

Expected:

- Exit code 0.
- Four screenshots exist under `temp/homepage-review/`.
- No horizontal overflow, broken images, font failures, or console errors.

- [ ] **Step 5: Open all four screenshots and inspect the real rendered page**

Check:

- 375 px: single-column hero and paper rows; links wrap; no clipped title or author text.
- 768 px: balanced tablet spacing; portrait remains visible; paper rows do not feel cramped.
- 1280 px: 940 px centered editorial canvas; three-column Research grid; publication imagery does not dominate.
- 1920 px: content remains centered and readable; negative space is intentional rather than empty-looking.
- All viewports: the warm paper/ink/brick palette matches the approved direction and the selected portrait does not look circular or overprocessed.

- [ ] **Step 6: Record a non-Git checkpoint**

Run:

```bash
shasum -a 256 assets/css/site.css tests/test_visual.py
```

Expected: two SHA-256 lines.

---

### Task 4: Add operational documentation and run the full verification gate

**Files:**
- Create: `README.md`
- Verify: all production, script, and test files

**Interfaces:**
- Consumes: Completed static site and verification scripts.
- Produces: Repeatable preview/test instructions and final evidence suitable for delivery.

- [ ] **Step 1: Write the local preview and verification guide**

Create `README.md`:

````markdown
# Hongyu Ding Academic Homepage

Static academic homepage implementing the Evidence-Led Editorial design in `plan/2026-07-14-academic-homepage-design.md`.

## Preview

```bash
python3 -m http.server 4173 --directory /Users/dinghongyu/Downloads/hongyuding-home-page
```

Open `http://127.0.0.1:4173`.

## Prepare assets

```bash
.venv/bin/python scripts/prepare_assets.py
```

The source portrait under `figs/` is never modified. If an official project page does not expose a suitable teaser, keep that publication text-only.

## Run content and asset tests

```bash
.venv/bin/python -m pytest tests/test_content.py tests/test_assets.py -q
```

## Run responsive browser checks

```bash
python3 "/Users/dinghongyu/.claude/skills/webapp-testing/scripts/with_server.py" \
  --server "python3 -m http.server 4173 --directory /Users/dinghongyu/Downloads/hongyuding-home-page" \
  --port 4173 \
  -- .venv/bin/python tests/test_visual.py
```

Screenshots are written to `temp/homepage-review/`.
````

- [ ] **Step 2: Run all Python checks together**

Run:

```bash
.venv/bin/python -m pytest tests/test_content.py tests/test_assets.py -q
```

Expected: `10 passed`.

- [ ] **Step 3: Validate HTML syntax locally**

Run:

```bash
/usr/bin/tidy -quiet -errors index.html
```

Expected: no HTML errors. Review warnings rather than suppressing them; accepted warnings must not concern missing alt text, malformed nesting, duplicate IDs, or invalid links.

- [ ] **Step 4: Run a second HTML validator**

Run:

```bash
npx --yes html-validate index.html
```

Expected: zero errors.

- [ ] **Step 5: Run the responsive browser gate again**

Run:

```bash
python3 "/Users/dinghongyu/.claude/skills/webapp-testing/scripts/with_server.py" \
  --server "python3 -m http.server 4173 --directory /Users/dinghongyu/Downloads/hongyuding-home-page" \
  --port 4173 \
  -- .venv/bin/python tests/test_visual.py
```

Expected: exit code 0 and refreshed screenshots for all four widths.

- [ ] **Step 6: Run the mandatory code review**

Invoke the `code-reviewer` agent on:

- `index.html`
- `assets/css/site.css`
- `scripts/prepare_assets.py`
- `tests/test_content.py`
- `tests/test_assets.py`
- `tests/test_visual.py`
- `README.md`

Require review across correctness, accessibility, security, maintainability, and scope adherence. Apply only confirmed findings, then rerun Steps 2–5.

- [ ] **Step 7: Run the visual design review**

Serve the page and inspect the four saved screenshots using the `web-design-reviewer` workflow. Prioritize:

1. Horizontal overflow or clipping
2. Weak hierarchy in the hero
3. Portrait crop balance
4. Paper-image crop correctness
5. Mobile link target size
6. Contrast and focus visibility
7. Unnecessary decoration or template-like styling

Apply only observed fixes and rerun the browser gate after every CSS or HTML change.

- [ ] **Step 8: Record the final file manifest and checksums**

Run:

```bash
find index.html README.md requirements-dev.txt scripts assets tests plan -type f -print | sort
shasum -a 256 index.html README.md assets/css/site.css scripts/prepare_assets.py tests/*.py
```

Expected:

- Manifest contains only intended source, asset, test, and planning files.
- Checksums are available for the final closeout report.
- The original portrait and all unrelated files under `figs/` remain untouched.

## Plan Self-Review Checklist

- [ ] Every approved section has an implementation task.
- [ ] Identity, contact, News, Research, publication metadata, links, and Academic Service match the design specification.
- [ ] CV and excluded sections remain absent.
- [ ] Production output is static HTML/CSS with no JavaScript dependency.
- [ ] Portrait preparation is reproducible and does not mutate the source.
- [ ] Paper-media extraction uses only author-controlled project pages and has an exact text-only fallback.
- [ ] Fonts are local WOFF2 files with checksums.
- [ ] Content, assets, browser behavior, HTML syntax, keyboard focus, font loading, images, reduced motion, and responsive overflow are tested.
- [ ] The four target screenshots are produced.
- [ ] Mandatory code review and visual review occur after implementation.
- [ ] No Git initialization or commit is performed without user instruction.
