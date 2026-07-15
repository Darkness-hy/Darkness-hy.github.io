"""Verify homepage structure, public copy, and link targets."""

from __future__ import annotations

import re
from pathlib import Path

from bs4 import BeautifulSoup, Tag

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "index.html"
CSS_PATH = ROOT / "assets" / "css" / "site.css"

EXPECTED_TITLE = "Hongyu Ding — Embodied AI, Robotics, and Reinforcement Learning"
EXPECTED_DESCRIPTION = (
    "Hongyu Ding is a PhD student at Nanjing University working on embodied "
    "intelligence, language–vision–action translation, navigation, and "
    "reinforcement learning."
)
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
EXPECTED_NEWS_RECORDS = (
    (
        "2026-05",
        "May 2026",
        "Released Uni-LaViRA, a training-free framework for unified embodied "
        "navigation, with a paper, project page, and code.",
        (("Uni-LaViRA", "https://xetroubadour.github.io/Uni-LaViRA/"),),
    ),
    (
        "2026-03",
        "March 2026",
        "Updated LaViRA with its ICRA 2026 version for zero-shot vision-language "
        "navigation in continuous environments.",
        (("LaViRA", "https://robo-lavira.github.io/lavira-zs-vln/"),),
    ),
    (
        "2025-10",
        "October 2025",
        "Released LaViRA with its paper, project page, and code.",
        (("LaViRA", "https://arxiv.org/abs/2510.19655"),),
    ),
    (
        "2023-12",
        "December 2023",
        "Magnetic Field-Based Reward Shaping appeared in IEEE/CAA Journal of "
        "Automatica Sinica, volume 10, issue 12.",
        (
            (
                "Magnetic Field-Based Reward Shaping",
                "https://doi.org/10.1109/JAS.2023.123477",
            ),
        ),
    ),
    (
        "2023-07",
        "July 2023",
        "Magnetic Field-Based Reward Shaping became available online with project, "
        "code, and supplementary-video resources.",
        (),
    ),
)
EXPECTED_SELECTED_PUBLICATIONS = (
    (
        "Uni-LaViRA: Language-Vision-Robot Actions Translation for Unified "
        "Embodied Navigation",
        "https://arxiv.org/abs/2605.27582",
        (
            "Hongyu Ding", "Sizhuo Zhang", "Ziming Xu", "Jinwen Guo",
            "Hongxiu Liu", "Xingzhi Cheng", "Zixuan Chen", "Haifei Qi",
            "Duo Wang", "Hao Xu", "Jieqi Shi", "Yifan Zhang", "Jing Huo",
            "Jian Cheng", "Yang Gao", "Jiebo Luo",
        ),
        "Hongyu Ding",
        "arXiv · 2026",
        "Training-free unified embodied navigation through language–vision–robot "
        "action translation.",
        (
            ("Paper", "https://arxiv.org/abs/2605.27582"),
            ("Project", "https://xetroubadour.github.io/Uni-LaViRA/"),
            (
                "Code",
                "https://github.com/NJU-R-L-Group-Embodied-Lab/uni-lavira-code",
            ),
        ),
    ),
    (
        "LaViRA: Language-Vision-Robot Actions Translation for Zero-Shot Vision "
        "Language Navigation in Continuous Environments",
        "https://arxiv.org/abs/2510.19655",
        (
            "Hongyu Ding", "Ziming Xu", "Yudong Fang", "You Wu", "Zixuan Chen",
            "Jieqi Shi", "Jing Huo", "Yifan Zhang", "Yang Gao",
        ),
        "Hongyu Ding",
        "ICRA · 2026",
        "Zero-shot continuous navigation through language–vision–robot action "
        "translation.",
        (
            ("Paper", "https://arxiv.org/abs/2510.19655"),
            ("Project", "https://robo-lavira.github.io/lavira-zs-vln/"),
            ("Code", "https://github.com/NJU-R-L-Group-Embodied-Lab/lavira-code"),
        ),
    ),
    (
        "Magnetic Field-Based Reward Shaping for Goal-Conditioned Reinforcement "
        "Learning",
        "https://doi.org/10.1109/JAS.2023.123477",
        ("Hongyu Ding", "Yuanze Tang", "Qing Wu", "Bo Wang", "Chunlin Chen", "Zhi Wang"),
        "Hongyu Ding",
        "IEEE/CAA JAS · 2023",
        "Magnetic-field-inspired rewards for efficient goal-conditioned "
        "reinforcement learning.",
        (
            ("Paper", "https://doi.org/10.1109/JAS.2023.123477"),
            ("Project", "https://hongyuding.wixsite.com/mfrs"),
            ("Code", "https://github.com/Darkness-hy/mfrs"),
            ("Video", "https://www.bilibili.com/video/BV1784y1z7Bj"),
        ),
    ),
)
EXPECTED_COMPACT_PUBLICATIONS = (
    (
        "2026",
        "Uni-LaViRA: Language-Vision-Robot Actions Translation for Unified "
        "Embodied Navigation",
        "https://arxiv.org/abs/2605.27582",
        "Uni-LaViRA: Language-Vision-Robot Actions Translation for Unified Embodied "
        "Navigation. Hongyu Ding et al. arXiv, 2026.",
    ),
    (
        "2026",
        "LaViRA: Language-Vision-Robot Actions Translation for Zero-Shot Vision "
        "Language Navigation in Continuous Environments",
        "https://arxiv.org/abs/2510.19655",
        "LaViRA: Language-Vision-Robot Actions Translation for Zero-Shot Vision "
        "Language Navigation in Continuous Environments. Hongyu Ding et al. ICRA, "
        "2026.",
    ),
    (
        "2023",
        "Magnetic Field-Based Reward Shaping for Goal-Conditioned Reinforcement "
        "Learning",
        "https://doi.org/10.1109/JAS.2023.123477",
        "Magnetic Field-Based Reward Shaping for Goal-Conditioned Reinforcement "
        "Learning. Hongyu Ding, Yuanze Tang, Qing Wu, Bo Wang, Chunlin Chen, and Zhi "
        "Wang. IEEE/CAA Journal of Automatica Sinica, 10(12):2233–2247, 2023.",
    ),
)


def _soup() -> BeautifulSoup:
    """Parse the production homepage."""
    return BeautifulSoup(INDEX_PATH.read_text(encoding="utf-8"), "html.parser")


def _normalized_text(tag: Tag) -> str:
    """Return collapsed element text without spaces before punctuation."""
    text = " ".join(tag.stripped_strings)
    return re.sub(r"\s+([,.;:])", r"\1", text)


def _ordered_links(tag: Tag) -> tuple[tuple[str, str], ...]:
    """Return ordered visible labels and destinations within an element."""
    return tuple(
        (_normalized_text(anchor), str(anchor.get("href")))
        for anchor in tag.select("a[href]")
    )


def test_document_metadata() -> None:
    """Require exact page metadata and no fake canonical URL."""
    soup = _soup()
    description = soup.select_one('meta[name="description"]')
    og_title = soup.select_one('meta[property="og:title"]')
    og_description = soup.select_one('meta[property="og:description"]')
    og_image = soup.select_one('meta[property="og:image"]')
    assert soup.title is not None
    assert soup.title.get_text(strip=True) == EXPECTED_TITLE
    assert description is not None and description.get("content") == EXPECTED_DESCRIPTION
    assert og_title is not None and og_title.get("content") == EXPECTED_TITLE
    assert og_description is not None and og_description.get("content") == EXPECTED_DESCRIPTION
    assert og_image is not None and og_image.get("content") == EXPECTED_PROFILE_IMAGE
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
    service = soup.select_one("#academic-service")
    assert service is not None and "Details coming soon." in service.get_text(" ", strip=True)


def test_public_identity_and_scope() -> None:
    """Expose confirmed identity and omit excluded CV content."""
    text = _soup().get_text(" ", strip=True)
    assert "PhD Student at Nanjing University" in text
    assert "I study embodied intelligence" in text
    assert all(term not in text for term in ("CV", "Awards", "Teaching"))


def test_verified_link_targets() -> None:
    """Validate every anchor before requiring the exact approved link set."""
    external_hrefs = set()
    for anchor in _soup().select("a"):
        href = anchor.get("href")
        assert isinstance(href, str) and href.strip() and href != "#" and "TODO" not in href
        if href == "#main":
            assert "skip-link" in anchor.get("class", [])
            continue
        assert href.startswith(("http", "mailto:"))
        external_hrefs.add(href)
    assert external_hrefs == EXPECTED_LINKS


def test_static_runtime_architecture_is_local_html_and_one_css() -> None:
    """Require one local stylesheet, no scripts/imports, and local runtime media."""
    soup = _soup()
    stylesheets = soup.select('link[rel~="stylesheet"]')
    assert [tag.get("href") for tag in stylesheets] == ["assets/css/site.css"]
    assert not soup.select("style, script")

    css = re.sub(r"/\*.*?\*/", "", CSS_PATH.read_text(encoding="utf-8"), flags=re.S)
    assert "@import" not in css.casefold()
    css_urls = [match.strip(" \t\n\r\"'") for match in re.findall(r"url\(([^)]+)\)", css)]
    for source in css_urls:
        assert not source.startswith(("http://", "https://", "//", "data:"))
        assert (CSS_PATH.parent / source).resolve().is_file()

    runtime_images = [str(tag.get("src")) for tag in soup.select("img[src], source[src]")]
    runtime_images.extend(
        str(tag.get("content")) for tag in soup.select('meta[property="og:image"][content]')
    )
    for source in runtime_images:
        assert not source.startswith(("http://", "https://", "//", "data:"))
        assert (ROOT / source).is_file()


def test_news_records_are_exact_and_ordered() -> None:
    """Pin each News date, complete text, and ordered linked-label association."""
    actual = []
    for item in _soup().select(".news-item"):
        time = item.find("time")
        paragraph = item.find("p")
        assert isinstance(time, Tag) and isinstance(paragraph, Tag)
        actual.append(
            (str(time.get("datetime")), _normalized_text(time), _normalized_text(paragraph), _ordered_links(paragraph))
        )
    assert tuple(actual) == EXPECTED_NEWS_RECORDS


def test_selected_publication_records_are_exact_and_ordered() -> None:
    """Pin selected titles, authorship, status, summaries, and ordered resources."""
    actual = []
    for card in _soup().select(".publication-card"):
        title_link = card.select_one("h3 a[href]")
        authors = card.select_one(".authors")
        status = card.select_one(".publication-status")
        summary = card.select_one(".publication-summary")
        resources = card.select_one(".resource-links")
        assert all(isinstance(tag, Tag) for tag in (title_link, authors, status, summary, resources))
        assert isinstance(title_link, Tag) and isinstance(authors, Tag)
        emphasized = authors.select("strong")
        actual.append(
            (
                _normalized_text(title_link), str(title_link.get("href")),
                tuple(part.strip() for part in _normalized_text(authors).split(",")),
                _normalized_text(emphasized[0]) if len(emphasized) == 1 else "",
                _normalized_text(status), _normalized_text(summary), _ordered_links(resources),
            )
        )
    assert tuple(actual) == EXPECTED_SELECTED_PUBLICATIONS


def test_compact_publication_records_are_exact_and_ordered() -> None:
    """Bind each compact title and citation to its ordered year group."""
    actual = []
    for group in _soup().select(".publication-year"):
        year = group.find("h3")
        assert isinstance(year, Tag)
        for entry in group.select(".publication-entry"):
            title_link = entry.select_one("a[href]")
            assert isinstance(title_link, Tag)
            actual.append(
                (_normalized_text(year), _normalized_text(title_link), str(title_link.get("href")), _normalized_text(entry))
            )
    assert tuple(actual) == EXPECTED_COMPACT_PUBLICATIONS


def test_resource_labels_match_available_artifacts() -> None:
    """Require exact resource labels and targets for each publication card."""
    actual = tuple(
        _ordered_links(card.select_one(".resource-links"))
        for card in _soup().select(".publication-card")
        if isinstance(card.select_one(".resource-links"), Tag)
    )
    assert actual == tuple(record[-1] for record in EXPECTED_SELECTED_PUBLICATIONS)
    assert "Dataset" not in _soup().get_text(" ", strip=True)
