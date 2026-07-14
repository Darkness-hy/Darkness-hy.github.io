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
