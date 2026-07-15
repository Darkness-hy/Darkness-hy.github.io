"""Run real-browser responsive and accessibility smoke checks."""

from pathlib import Path

from playwright.sync_api import Browser, Page, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SCREENSHOT_DIR = ROOT / "temp" / "homepage-review"
BASE_URL = "http://127.0.0.1:4173"
VIEWPORTS = (375, 768, 1280, 1920)


def _grid_columns(page: Page, selector: str) -> int:
    """Return the number of rendered CSS grid columns for an element."""
    template = page.locator(selector).first.evaluate(
        "element => getComputedStyle(element).gridTemplateColumns"
    )
    return 1 if template == "none" else len(template.split())


def _assert_responsive_layout(page: Page, width: int) -> None:
    """Verify the approved layout state at a target width."""
    shell = page.locator(".page-shell").bounding_box()
    assert shell is not None
    assert abs(shell["x"] - ((width - shell["width"]) / 2)) <= 1
    assert _grid_columns(page, ".publication-card--text-only") == 1

    if width == 375:
        assert _grid_columns(page, ".hero") == 1
        assert _grid_columns(page, ".research-grid") == 1
        assert _grid_columns(page, ".publication-card:not(.publication-card--text-only)") == 1
    elif width == 768:
        assert _grid_columns(page, ".hero") == 2
        assert _grid_columns(page, ".publication-card:not(.publication-card--text-only)") == 2
    else:
        assert 938 <= shell["width"] <= 942
        assert _grid_columns(page, ".hero") == 2
        assert _grid_columns(page, ".research-grid") == 3
        assert _grid_columns(page, ".publication-card:not(.publication-card--text-only)") == 2


def _assert_page(browser: Browser, width: int) -> None:
    """Verify one rendered viewport and save screenshot evidence."""
    page = browser.new_page(viewport={"width": width, "height": 1000})
    console_errors: list[str] = []
    asset_errors: list[str] = []
    page.on(
        "console",
        lambda message: console_errors.append(message.text)
        if message.type == "error"
        else None,
    )
    page.on(
        "response",
        lambda response: asset_errors.append(f"{response.status} {response.url}")
        if response.url.startswith(BASE_URL) and response.status >= 400
        else None,
    )
    page.on(
        "requestfailed",
        lambda request: asset_errors.append(
            f"FAILED {request.url}: {request.failure or 'unknown error'}"
        )
        if request.url.startswith(BASE_URL)
        else None,
    )

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
    assert not asset_errors, asset_errors
    _assert_responsive_layout(page, width)

    page.keyboard.press("Tab")
    focus_style = page.evaluate(
        """() => {
            const style = getComputedStyle(document.activeElement);
            return {
                outlineStyle: style.outlineStyle,
                outlineWidth: style.outlineWidth
            };
        }"""
    )
    assert focus_style["outlineStyle"] != "none"
    assert focus_style["outlineWidth"] != "0px"
    page.evaluate("document.activeElement.blur()")

    page.screenshot(
        path=str(SCREENSHOT_DIR / f"homepage-{width}.png"),
        full_page=True,
    )
    page.close()


def _assert_reduced_motion(browser: Browser) -> None:
    """Verify the page defines no required motion in reduced-motion mode."""
    context = browser.new_context(reduced_motion="reduce")
    page = context.new_page()
    page.goto(BASE_URL, wait_until="networkidle")
    assert page.evaluate("document.getAnimations().length") == 0
    context.close()


def main() -> int:
    """Run all browser checks and save viewport evidence."""
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        for width in VIEWPORTS:
            _assert_page(browser, width)
        _assert_reduced_motion(browser)
        browser.close()

    screenshots = list(SCREENSHOT_DIR.glob("homepage-*.png"))
    assert len(screenshots) == len(VIEWPORTS)
    assert {path.name for path in screenshots} == {
        f"homepage-{width}.png" for width in VIEWPORTS
    }
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
