"""Prepare homepage assets from reviewed, immutable source revisions."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from types import MappingProxyType
from typing import Callable, Final, Mapping, Optional
from urllib.request import Request, urlopen

from fontTools.ttLib import TTFont
from PIL import Image, ImageOps

LOGGER = logging.getLogger(__name__)
ROOT: Final = Path(__file__).resolve().parents[1]
FONT_DIR: Final = ROOT / "assets" / "fonts"
IMAGE_DIR: Final = ROOT / "assets" / "images"
PAPER_DIR: Final = IMAGE_DIR / "papers"
MANIFEST_PATH: Final = ROOT / "assets" / "ASSET_SOURCES.json"
USER_AGENT: Final = "Mozilla/5.0 (compatible; HongyuDingHomepageAssetPrep/1.0)"
PUBLIC_FILE_MODE: Final = 0o644


@dataclass(frozen=True)
class RemoteSource:
    """Describe one immutable remote input and its generated output."""

    source_url: str
    source_sha256: str
    output_filename: str
    approved_output_sha256: Optional[str] = None
    font_modified_timestamp: Optional[int] = None


@dataclass(frozen=True)
class PortraitSource:
    """Describe the approved local portrait source and crop."""

    source_path: Path
    source_sha256: str
    crop_box: tuple[int, int, int, int]
    output_filename: str


@dataclass(frozen=True)
class TextOnlyDecision:
    """Describe a reviewed paper that must not have generated media."""

    managed_output_filename: str
    reason: str


FONT_SOURCES: Final[Mapping[str, RemoteSource]] = MappingProxyType(
    {
        "ibm-plex-sans-medium.woff2": RemoteSource(
            source_url=(
                "https://raw.githubusercontent.com/IBM/plex/"
                "c5f949677f6f163e8dfe98ca2c326bd48b42fa1b/packages/plex-sans/"
                "fonts/complete/woff2/IBMPlexSans-Medium.woff2"
            ),
            source_sha256=(
                "5660f8a658f8bb50dbc005232f885eadffd2bc1c235c4f6fbb63469d1f9cde6d"
            ),
            output_filename="ibm-plex-sans-medium.woff2",
            approved_output_sha256=(
                "5660f8a658f8bb50dbc005232f885eadffd2bc1c235c4f6fbb63469d1f9cde6d"
            ),
        ),
        "ibm-plex-sans-regular.woff2": RemoteSource(
            source_url=(
                "https://raw.githubusercontent.com/IBM/plex/"
                "c5f949677f6f163e8dfe98ca2c326bd48b42fa1b/packages/plex-sans/"
                "fonts/complete/woff2/IBMPlexSans-Regular.woff2"
            ),
            source_sha256=(
                "ba711a3085ff9f27440b6b9c4550cfc47c97bf36591d5da958b975bb3add8c1a"
            ),
            output_filename="ibm-plex-sans-regular.woff2",
            approved_output_sha256=(
                "ba711a3085ff9f27440b6b9c4550cfc47c97bf36591d5da958b975bb3add8c1a"
            ),
        ),
        "ibm-plex-sans-semibold.woff2": RemoteSource(
            source_url=(
                "https://raw.githubusercontent.com/IBM/plex/"
                "c5f949677f6f163e8dfe98ca2c326bd48b42fa1b/packages/plex-sans/"
                "fonts/complete/woff2/IBMPlexSans-SemiBold.woff2"
            ),
            source_sha256=(
                "f78048030eab62e860efa39a0df79e2e5581bf122eb95b9bc42c0b8a4988d205"
            ),
            output_filename="ibm-plex-sans-semibold.woff2",
            approved_output_sha256=(
                "f78048030eab62e860efa39a0df79e2e5581bf122eb95b9bc42c0b8a4988d205"
            ),
        ),
        "newsreader-variable.woff2": RemoteSource(
            source_url=(
                "https://raw.githubusercontent.com/google/fonts/"
                "991ce1de6075188e6b8977a5aa9fcd3610a4e946/ofl/newsreader/"
                "Newsreader%5Bopsz%2Cwght%5D.ttf"
            ),
            source_sha256=(
                "8a08d13f8a6c0d51be379a60af84f945f65369a67e509ee3c3bdcc421254d7c1"
            ),
            output_filename="newsreader-variable.woff2",
            approved_output_sha256=(
                "dd4da31f604cbe8d68e31265eddb0f8fc10a4c75edb98bef53d85514db99150a"
            ),
            font_modified_timestamp=3866864224,
        ),
    }
)

PAPER_SOURCES: Final[Mapping[str, RemoteSource]] = MappingProxyType(
    {
        "uni-lavira": RemoteSource(
            source_url=(
                "https://raw.githubusercontent.com/"
                "NJU-R-L-Group-Embodied-Lab/uni-lavira-code/"
                "215e7aca072b9b932bcde4d3a28c80434ff39caa/assets/teaser.png"
            ),
            source_sha256=(
                "5de62f792db2571c6b82c757d887884ee165bd0d04340975129aa9630e406a60"
            ),
            output_filename="uni-lavira.webp",
        ),
        "lavira": RemoteSource(
            source_url=(
                "https://raw.githubusercontent.com/robo-lavira/lavira-zs-vln/"
                "6abf36295c1d7c86706e9b842a57f588ccbcebbf/"
                "static/images/teaser.png"
            ),
            source_sha256=(
                "1a130e41e469ebd6d1bf75ad00d4bcecebc1705e6356b13463a76df3a7dceb10"
            ),
            output_filename="lavira.webp",
        ),
    }
)

TEXT_ONLY_PAPERS: Final[Mapping[str, TextOnlyDecision]] = MappingProxyType(
    {
        "mfrs": TextOnlyDecision(
            managed_output_filename="mfrs.webp",
            reason=(
                "The Wix image is unsuitable, and repository plots are not documented "
                "as an official teaser."
            ),
        )
    }
)

PORTRAIT: Final = PortraitSource(
    source_path=ROOT / "figs" / "ChatGPT Image 2026年6月29日 16_41_32.png",
    source_sha256=(
        "6057a0ee0d6462f099eb9a9be8c5ce17bf3ac04f5154fac8231113e9734b5b0e"
    ),
    crop_box=(199, 430, 919, 1330),
    output_filename="profile-hongyu-ding.webp",
)

def _sha256_bytes(data: bytes) -> str:
    """Return the SHA-256 digest of in-memory data."""
    return hashlib.sha256(data).hexdigest()

def _sha256_path(path: Path) -> str:
    """Return the SHA-256 digest of a file."""
    return _sha256_bytes(path.read_bytes())

def _download(url: str) -> bytes:
    """Download one immutable public asset."""
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=30) as response:
            return response.read()
    except OSError as exc:
        LOGGER.error("Failed to download %s: %s", url, exc)
        raise

def _verified_download(source: RemoteSource) -> bytes:
    """Download a source and reject content that differs from review."""
    data = _download(source.source_url)
    actual_hash = _sha256_bytes(data)
    if actual_hash != source.source_sha256:
        raise ValueError(
            "SHA-256 mismatch for "
            f"{source.source_url}: expected {source.source_sha256}, got {actual_hash}"
        )
    return data

def _atomic_write(destination: Path, writer: Callable[[Path], None]) -> None:
    """Replace a destination only after its temporary output succeeds."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    replaced = False
    try:
        writer(temporary_path)
        os.chmod(temporary_path, PUBLIC_FILE_MODE)
        os.replace(temporary_path, destination)
        replaced = True
    finally:
        if not replaced:
            temporary_path.unlink(missing_ok=True)

def _write_binary(source_data: bytes, destination: Path) -> None:
    """Write verified upstream binary bytes without transformation."""

    def write_bytes(temporary_path: Path) -> None:
        """Write the approved bytes to an atomic temporary path."""
        temporary_path.write_bytes(source_data)

    _atomic_write(destination, write_bytes)

def _convert_font(source_data: bytes, source: RemoteSource, destination: Path) -> None:
    """Convert the hash-verified Newsreader TTF to deterministic WOFF2."""

    def write_font(temporary_path: Path) -> None:
        font = TTFont(BytesIO(source_data), recalcTimestamp=False)
        try:
            if source.font_modified_timestamp is None:
                raise ValueError(f"Missing approved font timestamp: {source.output_filename}")
            font["head"].modified = source.font_modified_timestamp
            font.flavor = "woff2"
            font.save(temporary_path)
        finally:
            font.close()

    _atomic_write(destination, write_font)

def _prepare_fonts() -> None:
    """Verify all font sources and preserve reviewed matching outputs."""
    for filename, source in FONT_SOURCES.items():
        LOGGER.info("Preparing font %s", filename)
        source_data = _verified_download(source)
        destination = FONT_DIR / filename
        if (
            destination.exists()
            and source.approved_output_sha256 is not None
            and _sha256_path(destination) == source.approved_output_sha256
        ):
            LOGGER.info("Keeping approved font output %s", filename)
            destination.chmod(PUBLIC_FILE_MODE)
            continue
        if source.font_modified_timestamp is None:
            _write_binary(source_data, destination)
        else:
            _convert_font(source_data, source, destination)

def _prepare_portrait() -> None:
    """Verify and export the approved portrait crop atomically."""
    actual_hash = _sha256_path(PORTRAIT.source_path)
    if actual_hash != PORTRAIT.source_sha256:
        raise ValueError(
            "SHA-256 mismatch for "
            f"{PORTRAIT.source_path}: expected {PORTRAIT.source_sha256}, "
            f"got {actual_hash}"
        )
    with Image.open(PORTRAIT.source_path) as source_image:
        crop = source_image.convert("RGB").crop(PORTRAIT.crop_box)
    if crop.size != (720, 900):
        raise ValueError(f"Unexpected portrait crop size: {crop.size}")

    def write_portrait(temporary_path: Path) -> None:
        crop.save(temporary_path, "WEBP", quality=90, method=6)

    _atomic_write(IMAGE_DIR / PORTRAIT.output_filename, write_portrait)

def _prepare_paper(source: RemoteSource, destination: Path) -> None:
    """Create one reviewed 16:9 paper image without risking prior output."""
    source_data = _verified_download(source)
    with Image.open(BytesIO(source_data)) as source_image:
        if source_image.mode == "P" and "transparency" in source_image.info:
            rgb_image = source_image.convert("RGBA").convert("RGB")
        else:
            rgb_image = source_image.convert("RGB")
        fitted = ImageOps.fit(
            rgb_image,
            (960, 540),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        )

    def write_paper(temporary_path: Path) -> None:
        fitted.save(temporary_path, "WEBP", quality=88, method=6)

    _atomic_write(destination, write_paper)

def _prepare_paper_media() -> None:
    """Generate only the two reviewed official paper teasers."""
    for name, source in PAPER_SOURCES.items():
        LOGGER.info("Preparing approved paper media for %s", name)
        _prepare_paper(source, PAPER_DIR / source.output_filename)

def _prepare_text_only_media() -> None:
    """Remove stale managed outputs for conclusive text-only decisions."""
    for name, decision in TEXT_ONLY_PAPERS.items():
        destination = PAPER_DIR / decision.managed_output_filename
        LOGGER.info("Enforcing text-only media state for %s", name)
        destination.unlink(missing_ok=True)

def _write_font_checksums() -> None:
    """Write exactly the four current font output hashes."""
    lines = [
        f"{_sha256_path(FONT_DIR / filename)}  {filename}\n"
        for filename in sorted(FONT_SOURCES)
    ]
    _atomic_write(
        FONT_DIR / "SHA256SUMS",
        lambda temporary_path: temporary_path.write_text("".join(lines), encoding="utf-8"),
    )

def _build_manifest() -> dict[str, object]:
    """Build provenance records from immutable descriptors and outputs."""
    fonts = {
        filename: {
            "source_url": source.source_url,
            "source_sha256": source.source_sha256,
            "output_filename": f"assets/fonts/{filename}",
            "output_sha256": _sha256_path(FONT_DIR / filename),
        }
        for filename, source in FONT_SOURCES.items()
    }
    papers: dict[str, object] = {
        name: {
            "decision": "accepted",
            "source_url": source.source_url,
            "source_sha256": source.source_sha256,
            "output_filename": f"assets/images/papers/{source.output_filename}",
            "output_sha256": _sha256_path(PAPER_DIR / source.output_filename),
        }
        for name, source in PAPER_SOURCES.items()
    }
    papers.update(
        {
            name: {
                "decision": "text-only",
                "managed_output_filename": (
                    f"assets/images/papers/{decision.managed_output_filename}"
                ),
                "reason": decision.reason,
            }
            for name, decision in TEXT_ONLY_PAPERS.items()
        }
    )
    return {
        "schema_version": 1,
        "portrait": {
            "source_path": PORTRAIT.source_path.relative_to(ROOT).as_posix(),
            "source_sha256": PORTRAIT.source_sha256,
            "crop_box": list(PORTRAIT.crop_box),
            "output_filename": f"assets/images/{PORTRAIT.output_filename}",
            "output_sha256": _sha256_path(IMAGE_DIR / PORTRAIT.output_filename),
        },
        "fonts": fonts,
        "papers": papers,
    }

def _write_manifest() -> None:
    """Write the generated provenance manifest atomically."""
    content = json.dumps(_build_manifest(), indent=2, sort_keys=True) + "\n"
    _atomic_write(
        MANIFEST_PATH,
        lambda temporary_path: temporary_path.write_text(content, encoding="utf-8"),
    )

def main() -> int:
    """Generate all approved assets and their provenance records."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    _prepare_fonts()
    _prepare_portrait()
    _prepare_paper_media()
    _prepare_text_only_media()
    _write_font_checksums()
    _write_manifest()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
