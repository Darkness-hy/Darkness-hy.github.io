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
