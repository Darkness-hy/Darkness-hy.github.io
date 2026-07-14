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
