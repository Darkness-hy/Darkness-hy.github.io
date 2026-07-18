"""Run real-browser responsive, network, print, and accessibility checks."""

from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import Browser, Locator, Page, Request, Route, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SCREENSHOT_DIR = ROOT / "temp" / "homepage-review"
BASE_URL = "http://127.0.0.1:4173"
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
VIEWPORTS = (375, 768, 1280, 1920)
EXPECTED_IMAGES = (
    ("/assets/images/profile-hongyu-ding.webp", 720, 900),
    ("/assets/images/papers/uni-lavira.webp", 960, 540),
    ("/assets/images/papers/lavira.webp", 960, 540),
)
EXPECTED_BODY_STACK = '"IBM Plex Sans", -apple-system, "system-ui", "Segoe UI", sans-serif'
EXPECTED_HEADING_STACK = "Newsreader, Georgia, serif"

def _is_loopback_request(url: str) -> bool:
    """Return whether an HTTP(S) request targets an approved loopback host."""
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and parsed.hostname in LOOPBACK_HOSTS

def _guard_network(page: Page, blocked_local_paths: tuple[str, ...] = ()) -> list[str]:
    """Block and report external requests while retaining local failure checks."""
    errors: list[str] = []

    def route_request(route: Route) -> None:
        """Allow only the exact preview origin and intentional local blocks."""
        request_url = route.request.url
        parsed = urlparse(request_url)
        if parsed.scheme not in {"http", "https"}:
            route.fallback()
        elif not _is_loopback_request(request_url):
            errors.append(f"EXTERNAL {request_url}")
            route.abort()
        elif any(parsed.path.startswith(path) for path in blocked_local_paths):
            route.abort()
        else:
            route.fallback()

    def record_failed_request(request: Request) -> None:
        """Record unexpected loopback request failures."""
        parsed = urlparse(request.url)
        intentionally_blocked = any(parsed.path.startswith(path) for path in blocked_local_paths)
        if _is_loopback_request(request.url) and not intentionally_blocked:
            errors.append(f"FAILED {request.url}: {request.failure or 'unknown error'}")

    page.route("**/*", route_request)
    page.on("response", lambda response: errors.append(
        f"{response.status} {response.url}") if _is_loopback_request(response.url) and response.status >= 400 else None)
    page.on("requestfailed", record_failed_request)
    return errors

def _new_page(browser: Browser, width: int = 1280, blocked_local_paths: tuple[str, ...] = ()) -> tuple[Page, list[str]]:
    """Create a guarded page at a target viewport width."""
    page = browser.new_page(viewport={"width": width, "height": 1000})
    return page, _guard_network(page, blocked_local_paths)

def _assert_no_horizontal_overflow(page: Page, width: int) -> None:
    """Require rendered content to stay within the viewport width."""
    dimensions = page.evaluate("() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]")
    assert dimensions[0] <= dimensions[1], (width, dimensions)

def _grid_columns(page: Page, selector: str) -> int:
    """Return the number of rendered CSS grid columns for an element."""
    template = page.locator(selector).first.evaluate("element => getComputedStyle(element).gridTemplateColumns")
    return 1 if template == "none" else len(template.split())

def _assert_featured_card_alignment(page: Page) -> None:
    """Keep the featured card aligned to the approved page canvas."""
    shell = page.locator(".page-shell").bounding_box()
    featured = page.locator(".publication-card--featured").bounding_box()
    assert shell is not None and featured is not None
    tolerance = 1.0
    shell_right = shell["x"] + shell["width"]
    featured_right = featured["x"] + featured["width"]
    assert featured["x"] >= shell["x"] - tolerance
    assert featured_right <= shell_right + tolerance
    assert abs(featured["x"] - shell["x"]) <= tolerance
    assert abs(featured_right - shell_right) <= tolerance

def _assert_responsive_layout(page: Page, width: int) -> None:
    """Verify the approved layout state at a target width."""
    shell = page.locator(".page-shell").bounding_box()
    assert shell is not None
    assert abs(shell["x"] - ((width - shell["width"]) / 2)) <= 1
    assert _grid_columns(page, ".publication-card--text-only") == 1
    publication_selector = ".publication-card:not(.publication-card--text-only)"
    if width == 375:
        assert _grid_columns(page, ".hero") == 1
        assert _grid_columns(page, ".research-grid") == 1
        assert _grid_columns(page, publication_selector) == 1
    elif width == 768:
        assert _grid_columns(page, ".hero") == 2
        assert _grid_columns(page, publication_selector) == 2
        _assert_featured_card_alignment(page)
    else:
        assert 938 <= shell["width"] <= 942
        assert _grid_columns(page, ".hero") == 2
        assert _grid_columns(page, ".research-grid") == 3
        assert _grid_columns(page, publication_selector) == 2
        _assert_featured_card_alignment(page)

def _image_state(image: Locator) -> dict[str, object]:
    """Return source and intrinsic/rendered dimensions after an image loads."""
    image.scroll_into_view_if_needed()
    return image.evaluate(
        """async image => {
            if (!image.complete) {
                await new Promise((resolve, reject) => {
                    image.addEventListener("load", resolve, {once: true});
                    image.addEventListener("error", reject, {once: true});
                });
            }
            const box = image.getBoundingClientRect();
            return {
                source: new URL(image.currentSrc).pathname,
                naturalWidth: image.naturalWidth,
                naturalHeight: image.naturalHeight,
                renderedWidth: box.width,
                renderedHeight: box.height
            };
        }"""
    )

def _assert_runtime_images_and_card_states(page: Page) -> None:
    """Verify exact local images and each selected card's approved media state."""
    cards = page.locator(".publication-card")
    assert cards.count() == 3
    expected_cards = (
        (True, False, "/assets/images/papers/uni-lavira.webp"),
        (False, False, "/assets/images/papers/lavira.webp"),
        (False, True, None),
    )
    for index, (featured, text_only, source) in enumerate(expected_cards):
        card = cards.nth(index)
        classes = set((card.get_attribute("class") or "").split())
        media = card.locator("figure.publication-card__media")
        assert ("publication-card--featured" in classes) is featured
        assert ("publication-card--text-only" in classes) is text_only
        assert media.count() == (0 if text_only else 1)
        if source is not None:
            assert media.locator("img").get_attribute("src") == source.removeprefix("/")
    images = page.locator("img")
    assert images.count() == len(EXPECTED_IMAGES)
    states = [_image_state(images.nth(index)) for index in range(images.count())]
    assert [state["source"] for state in states] == [item[0] for item in EXPECTED_IMAGES]
    for state, (_, natural_width, natural_height) in zip(states, EXPECTED_IMAGES):
        assert state["naturalWidth"] == natural_width
        assert state["naturalHeight"] == natural_height
        assert float(state["renderedWidth"]) > 0
        assert float(state["renderedHeight"]) > 0

def _assert_fonts_loaded_and_applied(page: Page) -> None:
    """Force-load every local face and verify the declared production stacks."""
    font_state = page.evaluate(
        """async () => {
            const requests = ["400 16px 'IBM Plex Sans'", "500 16px 'IBM Plex Sans'",
                "600 16px 'IBM Plex Sans'", "400 32px 'Newsreader'", "600 32px 'Newsreader'"
            ];
            const loadCounts = {};
            for (const request of requests) {
                loadCounts[request] = (await document.fonts.load(request)).length;
            }
            await document.fonts.ready;
            return {
                loadCounts,
                entries: Array.from(document.fonts).map(face => ({
                    family: face.family.replaceAll('"', ""), style: face.style,
                    weight: face.weight, status: face.status
                })),
                bodyStack: getComputedStyle(document.body).fontFamily,
                h1Stack: getComputedStyle(document.querySelector("h1")).fontFamily,
                h2Stacks: Array.from(document.querySelectorAll("h2"), heading => getComputedStyle(heading).fontFamily)
            };
        }"""
    )
    assert all(count > 0 for count in font_state["loadCounts"].values())
    entries = font_state["entries"]
    plex = [entry for entry in entries if entry["family"] == "IBM Plex Sans"]
    newsreader = [entry for entry in entries if entry["family"] == "Newsreader"]
    assert {entry["weight"] for entry in plex} == {"400", "500", "600"}
    assert plex and all(entry["status"] == "loaded" for entry in plex)
    assert newsreader and all(entry["status"] == "loaded" for entry in newsreader)
    assert any(entry["weight"] == "400 600" for entry in newsreader)
    assert font_state["bodyStack"] == EXPECTED_BODY_STACK
    assert font_state["h1Stack"] == EXPECTED_HEADING_STACK
    assert set(font_state["h2Stacks"]) == {EXPECTED_HEADING_STACK}

def _assert_mobile_link_targets(page: Page) -> None:
    """Require every discrete mobile contact/resource target to be 44 by 44."""
    boxes = page.locator(".contact-links a, .resource-links a").evaluate_all(
        """links => links.map(link => {
            const box = link.getBoundingClientRect();
            return {text: link.textContent.trim(), width: box.width, height: box.height};
        })"""
    )
    assert boxes
    for box in boxes:
        assert box["width"] >= 44, box
        assert box["height"] >= 44, box

def _focus_state(page: Page) -> dict[str, object]:
    """Return active-element identity, viewport bounds, and focus outline."""
    return page.evaluate(
        """() => {
            const element = document.activeElement;
            const style = getComputedStyle(element);
            const box = element.getBoundingClientRect();
            return {
                isSkip: element.matches(".skip-link"),
                isContact: element.matches(".contact-links a"),
                isResource: element.matches(".resource-links a"),
                box: {left: box.left, top: box.top, right: box.right, bottom: box.bottom},
                viewport: {width: innerWidth, height: innerHeight},
                outlineStyle: style.outlineStyle,
                outlineWidth: parseFloat(style.outlineWidth),
                outlineColor: style.outlineColor,
                outlineOffset: parseFloat(style.outlineOffset)
            };
        }"""
    )

def _assert_production_focus(state: dict[str, object]) -> None:
    """Require the explicit production focus treatment."""
    assert state["outlineStyle"] == "solid"
    assert float(state["outlineWidth"]) >= 3
    assert state["outlineColor"] == "rgb(45, 95, 133)"
    assert float(state["outlineOffset"]) >= 4

def _assert_keyboard_focus(page: Page) -> None:
    """Traverse from the skip link to contact and publication resources."""
    page.keyboard.press("Tab")
    skip_state = _focus_state(page)
    assert skip_state["isSkip"] is True
    box, viewport = skip_state["box"], skip_state["viewport"]
    assert float(box["left"]) >= 0 and float(box["top"]) >= 0
    assert float(box["right"]) <= float(viewport["width"])
    assert float(box["bottom"]) <= float(viewport["height"])
    _assert_production_focus(skip_state)
    focused_contact = focused_resource = False
    for _ in range(80):
        page.keyboard.press("Tab")
        state = _focus_state(page)
        if state["isContact"] or state["isResource"]:
            _assert_production_focus(state)
        focused_contact = focused_contact or bool(state["isContact"])
        focused_resource = focused_resource or bool(state["isResource"])
        if focused_contact and focused_resource:
            break
    assert focused_contact and focused_resource

def _assert_keyboard_navigation(browser: Browser) -> None:
    """Run keyboard focus checks on an isolated mobile page."""
    page, network_errors = _new_page(browser, 375)
    page.goto(BASE_URL, wait_until="networkidle")
    _assert_keyboard_focus(page)
    assert not network_errors, network_errors
    page.close()

def _assert_mobile_touch_targets(browser: Browser) -> None:
    """Keep 44px targets through the full single-column breakpoint."""
    page, network_errors = _new_page(browser, 640)
    page.goto(BASE_URL, wait_until="networkidle")
    _assert_mobile_link_targets(page)
    assert not network_errors, network_errors
    page.close()

def _assert_print_destinations(browser: Browser) -> None:
    """Expose destinations without overflowing narrow printed pages."""
    page, network_errors = _new_page(browser, 375)
    page.emulate_media(media="print")
    page.goto(BASE_URL, wait_until="networkidle")
    _assert_no_horizontal_overflow(page, 375)
    destinations = page.locator(".contact-links a[href], .resource-links a[href]").evaluate_all(
        """links => links.map(link => ({href: link.getAttribute("href"),
        content: getComputedStyle(link, "::after").content,
        overflowWrap: getComputedStyle(link, "::after").overflowWrap}))""")
    assert destinations
    for destination in destinations:
        assert destination["content"] == f'" ({destination["href"]})"'
        assert destination["overflowWrap"] == "anywhere"
    other_content = page.locator(
        "a[href]:not(.contact-links a):not(.resource-links a)"
    ).evaluate_all('links => links.map(link => getComputedStyle(link, "::after").content)')
    assert other_content and set(other_content) == {"none"}
    pagination_styles = page.locator(
        "#selected-publications .section-heading, #publications .section-heading, "
        "#publications .publication-year h3"
    ).evaluate_all("""elements => elements.map(element => {
        const style = getComputedStyle(element);
        return [style.breakAfter, style.pageBreakAfter];
    })""")
    assert pagination_styles == [["avoid", "avoid"]] * 4, pagination_styles
    assert not network_errors, network_errors
    page.close()

def _assert_page(browser: Browser, width: int) -> None:
    """Verify one rendered viewport and save screenshot evidence."""
    page, network_errors = _new_page(browser, width)
    console_errors: list[str] = []
    page.on(
        "console", lambda message: console_errors.append(message.text)
        if message.type == "error" else None)
    page.goto(BASE_URL, wait_until="networkidle")
    _assert_no_horizontal_overflow(page, width)
    assert page.locator("h1").inner_text() == "Hongyu Ding"
    assert page.locator(".news-item").count() == 5
    assert page.locator(".research-theme").count() == 3
    assert page.locator(".publication-entry").count() == 3
    _assert_runtime_images_and_card_states(page)
    _assert_fonts_loaded_and_applied(page)
    _assert_responsive_layout(page, width)
    if width == 375:
        _assert_mobile_link_targets(page)
    assert not console_errors, console_errors
    assert not network_errors, network_errors
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_function("window.scrollY === 0")
    page.screenshot(path=str(SCREENSHOT_DIR / f"homepage-{width}.png"), full_page=True)
    page.close()

def _assert_font_fallback_layout(browser: Browser) -> None:
    """Keep content readable when only local font requests are blocked."""
    for width in (375, 1280):
        page, network_errors = _new_page(browser, width, ("/assets/fonts/",))
        page.goto(BASE_URL, wait_until="networkidle")
        body, heading = page.locator("body"), page.locator("h1")
        assert body.is_visible() and heading.is_visible()
        assert body.inner_text().strip() and heading.inner_text().strip() == "Hongyu Ding"
        _assert_no_horizontal_overflow(page, width)
        assert not network_errors, network_errors
        page.close()

def _assert_external_successes_are_rejected(browser: Browser) -> None:
    """Block synthetic external HTTP(S) responses before fulfillment."""
    urls = ("http://external.invalid/ok", "https://external.invalid/ok")
    context = browser.new_context()
    reached: list[str] = []
    def synthetic_success(route: Route) -> None:
        """Fulfill an external request only if the page guard misses it."""
        if route.request.url in urls:
            reached.append(route.request.url)
            route.fulfill(status=200, headers={"access-control-allow-origin": "*"})
        else:
            route.fallback()
    context.route("**/*", synthetic_success)
    page = context.new_page()
    network_errors = _guard_network(page)
    page.goto(BASE_URL, wait_until="networkidle")
    outcomes = [page.evaluate(
        'url => fetch(url).then(() => "resolved", () => "rejected")', url
    ) for url in urls]
    assert outcomes == ["rejected", "rejected"]
    assert network_errors == [f"EXTERNAL {url}" for url in urls]
    assert not reached, reached
    context.close()

def _assert_motion_preferences(browser: Browser) -> None:
    """Verify smooth default scrolling and the reduced-motion override."""
    cases = (("no-preference", False, "smooth"), ("reduce", True, "auto"))
    for preference, reduced, scrolling in cases:
        context = browser.new_context(reduced_motion=preference)
        page = context.new_page()
        network_errors = _guard_network(page)
        page.goto(BASE_URL, wait_until="networkidle")
        assert page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches") is reduced
        assert page.evaluate(
            "getComputedStyle(document.documentElement).scrollBehavior"
        ) == scrolling
        if reduced:
            assert page.evaluate("document.getAnimations().length") == 0
        assert not network_errors, network_errors
        context.close()

def main() -> int:
    """Run all browser checks and save viewport evidence."""
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        for width in VIEWPORTS:
            _assert_page(browser, width)
        _assert_keyboard_navigation(browser)
        _assert_mobile_touch_targets(browser)
        _assert_font_fallback_layout(browser)
        _assert_motion_preferences(browser)
        _assert_external_successes_are_rejected(browser)
        _assert_print_destinations(browser)
        browser.close()
    screenshots = list(SCREENSHOT_DIR.glob("homepage-*.png"))
    assert len(screenshots) == len(VIEWPORTS)
    assert {path.name for path in screenshots} == {f"homepage-{width}.png" for width in VIEWPORTS}
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
