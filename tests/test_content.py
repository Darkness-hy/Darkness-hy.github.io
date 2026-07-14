"""Verify homepage structure, public copy, and link targets."""

from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "index.html"

EXPECTED_TITLE = "Hongyu Ding — Embodied AI, Robotics, and Reinforcement Learning"
EXPECTED_DESCRIPTION = (
    "Hongyu Ding is a PhD student at Nanjing University working on embodied "
    "intelligence, language–vision–action translation, navigation, and "
    "reinforcement learning."
)
EXPECTED_OPEN_GRAPH_DESCRIPTION = EXPECTED_DESCRIPTION
EXPECTED_PROFILE_IMAGE = "assets/images/profile-hongyu-ding.webp"

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
EXPECTED_PUBLICATION_RESOURCES = (
    {
        "Paper": "https://arxiv.org/abs/2605.27582",
        "Project": "https://xetroubadour.github.io/Uni-LaViRA/",
        "Code": "https://github.com/NJU-R-L-Group-Embodied-Lab/uni-lavira-code",
    },
    {
        "Paper": "https://arxiv.org/abs/2510.19655",
        "Project": "https://robo-lavira.github.io/lavira-zs-vln/",
        "Code": "https://github.com/NJU-R-L-Group-Embodied-Lab/lavira-code",
    },
    {
        "Paper": "https://doi.org/10.1109/JAS.2023.123477",
        "Project": "https://hongyuding.wixsite.com/mfrs",
        "Code": "https://github.com/Darkness-hy/mfrs",
        "Video": "https://www.bilibili.com/video/BV1784y1z7Bj",
    },
)


def _soup() -> BeautifulSoup:
    """Parse the production homepage."""
    return BeautifulSoup(INDEX_PATH.read_text(encoding="utf-8"), "html.parser")


def test_document_metadata() -> None:
    """Require exact page metadata and no fake canonical URL."""
    soup = _soup()
    description = soup.select_one('meta[name="description"]')
    open_graph_title = soup.select_one('meta[property="og:title"]')
    open_graph_description = soup.select_one('meta[property="og:description"]')
    open_graph_image = soup.select_one('meta[property="og:image"]')

    assert soup.title is not None
    assert soup.title.get_text(strip=True) == EXPECTED_TITLE
    assert description is not None
    assert description.get("content") == EXPECTED_DESCRIPTION
    assert open_graph_title is not None
    assert open_graph_title.get("content") == EXPECTED_TITLE
    assert open_graph_description is not None
    assert open_graph_description.get("content") == EXPECTED_OPEN_GRAPH_DESCRIPTION
    assert open_graph_image is not None
    assert open_graph_image.get("content") == EXPECTED_PROFILE_IMAGE
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
    """Validate every anchor before requiring the exact approved link set."""
    soup = _soup()
    external_hrefs = set()

    for anchor in soup.select("a"):
        href = anchor.get("href")
        assert isinstance(href, str)
        assert href.strip()
        assert href != "#"
        assert "TODO" not in href
        if href == "#main":
            assert "skip-link" in anchor.get("class", [])
            continue
        assert href.startswith(("http", "mailto:"))
        external_hrefs.add(href)

    assert external_hrefs == EXPECTED_LINKS


def test_resource_labels_match_available_artifacts() -> None:
    """Require exact resource labels and targets for each publication card."""
    soup = _soup()
    resource_maps = []
    for card in soup.select(".publication-card"):
        resource_links = card.select(".resource-links a")
        resource_map = {
            link.get_text(" ", strip=True): link.get("href") for link in resource_links
        }
        assert len(resource_map) == len(resource_links)
        resource_maps.append(resource_map)

    assert resource_maps == list(EXPECTED_PUBLICATION_RESOURCES)
    assert "Dataset" not in soup.get_text(" ", strip=True)
