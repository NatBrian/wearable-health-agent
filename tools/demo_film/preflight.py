#!/usr/bin/env python
"""Look at every screen at film resolution BEFORE any filming happens.

    uv run python tools/demo_film/preflight.py

Nothing here is clever. It opens each screen at exactly the resolution the film records
at, waits for it to settle, and saves a full frame. Then a person looks at the frames.

It exists because the cost of finding out that the record screen needs scrolling, or that
body text is unreadable once 1920 wide is played back in a small window, is a whole
re-shoot. Checking first costs two minutes.
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT = REPO_ROOT / "docs" / "demo" / "preflight"
BASE = "http://localhost:8501"

# The film is 1920x1080. It is NOT recorded at a 1920 wide viewport.
#
# Streamlit is responsive, so a 1920 viewport spreads body text into very long lines that
# are small in the frame and hard to read when the video is played in anything less than
# full screen. Recording a narrower viewport and letting the encoder scale it up makes
# every element proportionally larger, which is the standard trick for screen capture.
#
# A device scale factor of 3 renders at 3840x2160 and the encode downsamples to 1920x1080,
# so nothing is soft: the pixels are there, the layout is simply bigger.
WIDTH, HEIGHT = 1280, 720
SCALE = 3

SCREENS = (
    ("home", "/"),
    ("today", "/Today"),
    ("history", "/History"),
    ("record", "/The_record"),
    ("settings", "/Settings"),
)


# The element Streamlit actually scrolls. Its own name gives the game away: with a chat
# input on the page it scrolls itself to the BOTTOM, so every screen was being measured
# and photographed from its last paragraph upwards. Today reported 720px, exactly one
# viewport, which read as "it fits" and meant "we are looking at the end of it". It is
# 1803px, two and a half screens.
#
# Found by asking the page which of its elements actually scrolls, rather than by guessing
# at selector names, which is what produced the three wrong guesses before it.
MAIN_SELECTOR = """
    document.querySelector('[data-testid="stAppScrollToBottomContainer"]')
        || document.querySelector('section.stMain')
        || document.querySelector('[data-testid="stMain"]')
        || document.querySelector('[data-testid="stAppViewContainer"]')
"""

# Hidden for filming only, never in the product: the developer menu, and Streamlit's
# "running" spinner, which flickers in the corner of every take.
FILM_CSS = """
[data-testid="stToolbar"], [data-testid="stStatusWidget"], #MainMenu { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }
"""


def scroll_to_top(page) -> None:
    page.evaluate(
        f"() => {{ const m = {MAIN_SELECTOR}; if (m) m.scrollTop = 0; window.scrollTo(0, 0); }}"
    )


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--force-device-scale-factor=1"])
        context = browser.new_context(
            viewport={"width": WIDTH, "height": HEIGHT},
            device_scale_factor=SCALE,
        )
        page = context.new_page()

        for name, path in SCREENS:
            page.goto(f"{BASE}{path}", wait_until="networkidle")
            page.add_style_tag(content=FILM_CSS)
            # Streamlit paints in stages. Waiting on the spinner leaving is the only
            # reliable signal; a fixed sleep either wastes time or catches a half drawn
            # chart.
            page.wait_for_timeout(2500)
            try:
                page.wait_for_selector(
                    '[data-testid="stStatusWidget"]', state="detached", timeout=8000
                )
            except Exception:  # noqa: BLE001, S110
                pass  # the widget may already be gone, which is the state we wanted
            page.wait_for_timeout(1200)

            # Streamlit's chat input takes focus and drags the page to the bottom, so
            # every screen was being measured and photographed from its last paragraph
            # upwards. The Today screen reported 720px, exactly one viewport, which looked
            # like "it fits" and meant "we are looking at the end of it".
            scroll_to_top(page)
            page.wait_for_timeout(400)

            viewport_shot = OUT / f"{name}-viewport.png"
            page.screenshot(path=str(viewport_shot))

            full_shot = OUT / f"{name}-full.png"
            page.screenshot(path=str(full_shot), full_page=True)

            # NOT document.body.scrollHeight. Streamlit scrolls an inner container, and
            # the body stays exactly viewport height, so the first version of this check
            # reported "fits" for every screen including the record page, which needs
            # three screens of scrolling. A check that always passes is worse than none:
            # it was the reason the pre-flight looked done when it had measured nothing.
            height = page.evaluate(
                f"() => {{ const m = {MAIN_SELECTOR}; "
                "return m ? m.scrollHeight : document.body.scrollHeight; }"
            )
            screens = height / HEIGHT
            verdict = "fits" if height <= HEIGHT + 40 else f"{screens:.1f} screens tall"
            print(f"{name:<10} {height:>6}px  {verdict}")

        browser.close()
    print(f"\nframes in {OUT}")
    print("Now LOOK at them. Cramped layout, unreadable body text and clipped charts are")
    print("all cheaper to fix here than after a take.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
