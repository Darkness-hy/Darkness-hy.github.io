"""Verify reproducible local font and image assets used by the homepage."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from bs4 import BeautifulSoup, Tag
from PIL import Image

from scripts import prepare_assets

ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = ROOT / "assets" / "fonts"
IMAGE_DIR = ROOT / "assets" / "images"
PAPER_DIR = IMAGE_DIR / "papers"
INDEX_PATH = ROOT / "index.html"
MANIFEST_PATH = ROOT / "assets" / "ASSET_SOURCES.json"
FONT_LICENSE_ROWS = {
    "newsreader-variable.woff2": (
        "Newsreader",
        "LICENSE-Newsreader.txt",
        "https://github.com/google/fonts/tree/"
        "991ce1de6075188e6b8977a5aa9fcd3610a4e946/ofl/newsreader",
    ),
    "ibm-plex-sans-regular.woff2": (
        "IBM Plex Sans",
        "LICENSE-IBM-Plex.txt",
        "https://github.com/IBM/plex/tree/"
        "c5f949677f6f163e8dfe98ca2c326bd48b42fa1b/packages/plex-sans",
    ),
    "ibm-plex-sans-medium.woff2": (
        "IBM Plex Sans",
        "LICENSE-IBM-Plex.txt",
        "https://github.com/IBM/plex/tree/"
        "c5f949677f6f163e8dfe98ca2c326bd48b42fa1b/packages/plex-sans",
    ),
    "ibm-plex-sans-semibold.woff2": (
        "IBM Plex Sans",
        "LICENSE-IBM-Plex.txt",
        "https://github.com/IBM/plex/tree/"
        "c5f949677f6f163e8dfe98ca2c326bd48b42fa1b/packages/plex-sans",
    ),
}
FONT_LICENSE_NOTICES = {
    "LICENSE-Newsreader.txt": "Copyright 2020 The Newsreader Project Authors",
    "LICENSE-IBM-Plex.txt": "Copyright © 2017 IBM Corp.",
}

EXPECTED_FONT_SOURCES = {
    "ibm-plex-sans-medium.woff2": (
        "https://raw.githubusercontent.com/IBM/plex/"
        "c5f949677f6f163e8dfe98ca2c326bd48b42fa1b/packages/plex-sans/"
        "fonts/complete/ttf/IBMPlexSans-Medium.ttf",
        "331c8639d7598b2cde62a911a71db195e30cb655cd6bdf2e324a7e984955f907",
    ),
    "ibm-plex-sans-regular.woff2": (
        "https://raw.githubusercontent.com/IBM/plex/"
        "c5f949677f6f163e8dfe98ca2c326bd48b42fa1b/packages/plex-sans/"
        "fonts/complete/ttf/IBMPlexSans-Regular.ttf",
        "975dcda37d80f038dcd143c22e33ca2d97a0cc5a929aace1c749153b0fe1afa5",
    ),
    "ibm-plex-sans-semibold.woff2": (
        "https://raw.githubusercontent.com/IBM/plex/"
        "c5f949677f6f163e8dfe98ca2c326bd48b42fa1b/packages/plex-sans/"
        "fonts/complete/ttf/IBMPlexSans-SemiBold.ttf",
        "a20caf8286023a6a7a85e40b1d2a4ae9fc3e3b1f9eda8f4c542dd4986af67bb1",
    ),
    "newsreader-variable.woff2": (
        "https://raw.githubusercontent.com/google/fonts/"
        "991ce1de6075188e6b8977a5aa9fcd3610a4e946/ofl/newsreader/"
        "Newsreader%5Bopsz%2Cwght%5D.ttf",
        "8a08d13f8a6c0d51be379a60af84f945f65369a67e509ee3c3bdcc421254d7c1",
    ),
}
EXPECTED_PAPER_SOURCES = {
    "lavira": (
        "assets/images/papers/lavira.webp",
        "https://raw.githubusercontent.com/robo-lavira/lavira-zs-vln/"
        "6abf36295c1d7c86706e9b842a57f588ccbcebbf/static/images/teaser.png",
        "1a130e41e469ebd6d1bf75ad00d4bcecebc1705e6356b13463a76df3a7dceb10",
    ),
    "uni-lavira": (
        "assets/images/papers/uni-lavira.webp",
        "https://raw.githubusercontent.com/NJU-R-L-Group-Embodied-Lab/"
        "uni-lavira-code/215e7aca072b9b932bcde4d3a28c80434ff39caa/"
        "assets/teaser.png",
        "5de62f792db2571c6b82c757d887884ee165bd0d04340975129aa9630e406a60",
    ),
}
PORTRAIT_SOURCE = "figs/ChatGPT Image 2026年6月29日 16_41_32.png"
PORTRAIT_SOURCE_HASH = (
    "6057a0ee0d6462f099eb9a9be8c5ce17bf3ac04f5154fac8231113e9734b5b0e"
)


def _sha256(path: Path) -> str:
    """Return a file's SHA-256 digest."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _soup() -> BeautifulSoup:
    """Parse the production homepage."""
    return BeautifulSoup(INDEX_PATH.read_text(encoding="utf-8"), "html.parser")


def _publication_card(title_prefix: str) -> Tag:
    """Find one selected-publication card by its title prefix."""
    for card in _soup().select(".publication-card"):
        heading = card.find("h3")
        if isinstance(heading, Tag) and heading.get_text(strip=True).startswith(title_prefix):
            return card
    raise AssertionError(f"Missing publication card: {title_prefix}")


def test_publication_cards_have_exact_approved_media_states() -> None:
    """Keep both approved teasers, MFRS text-only, and Uni featured."""
    expected = {
        "Uni-LaViRA:": ("assets/images/papers/uni-lavira.webp", True, False),
        "LaViRA:": ("assets/images/papers/lavira.webp", False, False),
        "Magnetic Field-Based": (None, False, True),
    }
    for title, (source, featured, text_only) in expected.items():
        card = _publication_card(title)
        classes = set(card.get("class", []))
        media = card.select("figure.publication-card__media")
        assert ("publication-card--featured" in classes) is featured
        assert ("publication-card--text-only" in classes) is text_only
        assert (len(media) == 1) is (not text_only)
        assert (len(media) == 0) is text_only
        if source is not None:
            image = media[0].find("img")
            assert isinstance(image, Tag)
            assert image.get("src") == source

    uni_image = _publication_card("Uni-LaViRA:").find("img")
    assert isinstance(uni_image, Tag)
    assert uni_image.get("alt") == "Uni-LaViRA unified embodied navigation overview."


def test_every_publication_card_has_one_media_or_text_only_state() -> None:
    """Reject cards with both states or neither state."""
    for card in _soup().select(".publication-card"):
        has_media = len(card.select("figure.publication-card__media")) == 1
        is_text_only = "publication-card--text-only" in card.get("class", [])
        assert has_media ^ is_text_only


def test_profile_crop_is_exact() -> None:
    """Require the approved 4:5 portrait export."""
    with Image.open(IMAGE_DIR / "profile-hongyu-ding.webp") as image:
        assert image.format == "WEBP"
        assert image.size == (720, 900)


def test_referenced_paper_media_are_exact_webp_exports() -> None:
    """Require every selected-paper image to be a 960 by 540 WebP."""
    images = _soup().select(".publication-card__media img")
    assert len(images) == 2
    for image_tag in images:
        path = ROOT / str(image_tag["src"])
        with Image.open(path) as image:
            assert image.format == "WEBP"
            assert image.size == (960, 540)


def test_no_orphan_paper_webps_exist() -> None:
    """Keep managed paper exports synchronized with homepage references."""
    referenced = {
        Path(str(tag["src"])).name
        for tag in _soup().select(".publication-card__media img")
    }
    actual = {path.name for path in PAPER_DIR.glob("*.webp")}
    assert actual == referenced


def test_font_license_notices_and_readme_are_complete_offline() -> None:
    """Map every bundled font to its exact pinned OFL notice offline."""
    readme = (FONT_DIR / "README.md").read_text(encoding="utf-8")
    for notice_name, copyright_line in FONT_LICENSE_NOTICES.items():
        notice = (FONT_DIR / notice_name).read_text(encoding="utf-8")
        assert "SIL OPEN FONT LICENSE Version 1.1" in notice
        assert copyright_line in notice

    for binary, (family, notice_name, source_url) in FONT_LICENSE_ROWS.items():
        expected_row = (
            f"| `{binary}` | {family} | `{notice_name}` | {source_url} |"
        )
        assert expected_row in readme


def test_font_checksums_are_exact_and_current() -> None:
    """Require exactly four verified font outputs in SHA256SUMS."""
    lines = (FONT_DIR / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    entries = {filename: digest for digest, filename in (line.split() for line in lines)}
    assert set(entries) == set(EXPECTED_FONT_SOURCES)
    assert len(lines) == len(EXPECTED_FONT_SOURCES)
    for filename, digest in entries.items():
        path = FONT_DIR / filename
        assert path.stat().st_size > 10_000
        assert digest == _sha256(path)


def test_asset_manifest_records_approved_sources_and_outputs() -> None:
    """Pin source provenance and match every generated output hash."""
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 1

    portrait = manifest["portrait"]
    assert portrait["source_path"] == PORTRAIT_SOURCE
    assert portrait["source_sha256"] == PORTRAIT_SOURCE_HASH
    assert portrait["crop_box"] == [199, 430, 919, 1330]
    assert portrait["output_filename"] == "assets/images/profile-hongyu-ding.webp"
    assert portrait["output_sha256"] == _sha256(ROOT / portrait["output_filename"])

    assert set(manifest["fonts"]) == set(EXPECTED_FONT_SOURCES)
    for filename, (url, source_hash) in EXPECTED_FONT_SOURCES.items():
        record = manifest["fonts"][filename]
        assert record["source_url"] == url
        assert record["source_sha256"] == source_hash
        assert record["output_filename"] == f"assets/fonts/{filename}"
        assert record["output_sha256"] == _sha256(ROOT / record["output_filename"])

    assert set(manifest["papers"]) == {"uni-lavira", "lavira", "mfrs"}
    for name, (output, url, source_hash) in EXPECTED_PAPER_SOURCES.items():
        record = manifest["papers"][name]
        assert record["decision"] == "accepted"
        assert record["source_url"] == url
        assert record["source_sha256"] == source_hash
        assert record["output_filename"] == output
        assert record["output_sha256"] == _sha256(ROOT / output)

    mfrs = manifest["papers"]["mfrs"]
    assert mfrs["decision"] == "text-only"
    assert mfrs["managed_output_filename"] == "assets/images/papers/mfrs.webp"
    assert mfrs["reason"] == (
        "The Wix image is unsuitable, and repository plots are not documented "
        "as an official teaser."
    )
    assert not (ROOT / mfrs["managed_output_filename"]).exists()


def test_all_runtime_image_sources_are_local() -> None:
    """Prevent runtime dependencies on remote image hosts."""
    soup = _soup()
    sources = [str(tag["src"]) for tag in soup.select("img[src]")]
    sources.extend(
        str(tag["content"])
        for tag in soup.select('meta[property="og:image"][content]')
    )
    assert sources
    for source in sources:
        assert source.startswith("assets/images/")
        assert "://" not in source
        assert (ROOT / source).exists()


def test_text_only_decision_removes_only_stale_mfrs_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Delete stale managed MFRS media without discovery or directory purges."""
    paper_dir = tmp_path / "papers"
    paper_dir.mkdir()
    stale = paper_dir / "mfrs.webp"
    sibling = paper_dir / "keep.webp"
    stale.write_bytes(b"stale")
    sibling.write_bytes(b"keep")
    monkeypatch.setattr(prepare_assets, "PAPER_DIR", paper_dir)
    monkeypatch.setattr(
        prepare_assets,
        "_download",
        lambda _url: pytest.fail("text-only cleanup must stay offline"),
    )

    prepare_assets._prepare_text_only_media()

    assert not stale.exists()
    assert sibling.read_bytes() == b"keep"


def test_verified_hash_mismatch_preserves_existing_paper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Do not replace an accepted export when source verification fails."""
    destination = tmp_path / "uni-lavira.webp"
    destination.write_bytes(b"accepted-existing-output")
    monkeypatch.setattr(prepare_assets, "_download", lambda _url: b"wrong source")

    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        prepare_assets._prepare_paper(
            prepare_assets.PAPER_SOURCES["uni-lavira"], destination
        )

    assert destination.read_bytes() == b"accepted-existing-output"
