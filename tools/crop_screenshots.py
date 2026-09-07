#!/usr/bin/env python
"""Trim a dashboard screenshot down to the dashboard.

    uv run python tools/crop_screenshots.py            # crop docs/screenshots in place
    uv run python tools/crop_screenshots.py --check    # report only, change nothing
    uv run python tools/crop_screenshots.py path/*.png # crop something else

TWO THINGS ARE WRONG WITH A RAW CAPTURE, and both are invisible until somebody opens
the file at full size.

**Three quarters of the frame is nothing.** The screenshots committed on 6 September 2026
are 5120x2340 and the page occupies the top left 2531x1171 of that. The browser painted a
2560x1170 viewport into a canvas twice that size in each direction, so the rest is white.
On a README it renders as a small dashboard adrift in an ocean, because markdown scales
the whole file to the column width and most of the file is empty.

**The Streamlit developer toolbar is in shot.** "Stop", "Deploy" and the hamburger sit in
the top right of every capture. Deploy publishes the app to Streamlit Cloud, which on a
health dashboard is an invitation to put your own medical data on the public internet, and
it has no business appearing in a guide written for the person whose health it is.
`.streamlit/config.toml` sets `toolbarMode = "viewer"` to suppress it, which arrived after
these were taken.

The toolbar is the only thing in the top band of the page, and it hugs the right edge, so
cutting the band above the first full width element removes it and nothing else. That is
safer than painting over it: if a future capture ever has real content up there, the band
will not be blank and this refuses to guess.

IDEMPOTENT. An already cropped file has no margin left to remove and is reported as
"already tight", so this can be re-run after every new capture without damaging anything.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = REPO_ROOT / "docs" / "screenshots"

# How far down a toolbar can start before we stop believing it is a toolbar. The captures
# put it at y=18 to y=43; anything lower is page content and must not be cut.
TOOLBAR_MAX_BOTTOM = 80

# A toolbar sits in the right hand end of its band. If something in that band starts
# further left than this fraction of the width, it is content, not chrome.
TOOLBAR_MIN_LEFT_FRACTION = 0.85

# White space to keep above the first real element, so the crop does not look shaved.
TOP_MARGIN_PX = 16

# A browser scrollbar is a thin inked strip pinned to the right edge with a wide blank
# gutter between it and the page. Narrower than this, and separated by more than the
# gutter below, it is chrome and goes. Real page content is hundreds of pixels wide.
SCROLLBAR_MAX_WIDTH_PX = 40
SCROLLBAR_MIN_GUTTER_PX = 24

# How far a pixel must sit from the sidebar's own colour to count as something drawn on
# it. Summed across the three channels, so a label or a highlight box clears it easily
# and the block's own faint gradient does not.
SIDEBAR_INK_DELTA = 30


def _content_mask(image: Image.Image) -> np.ndarray:
    """True wherever a pixel is not pure white.

    The sidebar is light grey rather than white, so it counts as content and the left
    edge of the crop stays at the sidebar's own edge. That is what we want: padding to
    the left of it would read as a misaligned page.
    """
    return (np.asarray(image.convert("RGB")) != 255).any(axis=2)


def _toolbar_band(mask: np.ndarray, sidebar_end: int) -> int:
    """The first row BELOW the developer toolbar, or 0 if there is no toolbar to cut.

    Returns 0 rather than guessing whenever the band does not look like a toolbar: when
    the first thing on the page is full width, when it starts too far down, or when the
    band never ends.
    """
    main = mask[:, sidebar_end + 1 :]
    if not main.any():
        return 0
    rows = main.any(axis=1)

    first = int(np.argmax(rows))
    blank = None
    for y in range(first, min(TOOLBAR_MAX_BOTTOM, len(rows))):
        if not rows[y]:
            blank = y
            break
    if blank is None:
        return 0  # nothing separates the top band from the page. Cut nothing.

    columns = np.where(main[first:blank].any(axis=0))[0]
    if len(columns) == 0:
        return 0
    if columns[0] < main.shape[1] * TOOLBAR_MIN_LEFT_FRACTION:
        return 0  # reaches into the page. This is content, not chrome.

    return blank


def _scrollbar_width(mask: np.ndarray) -> int:
    """Width of the browser scrollbar pinned to the right edge, or 0 if there is none.

    `guide-step-detail.png` is the only capture with one, and it kept the file 96 pixels
    wider than every other screen for the sake of a 12 pixel grey line.
    """
    filled = mask.mean(axis=0)
    x = mask.shape[1] - 1
    strip = 0
    while x >= 0 and filled[x] > 0:
        strip += 1
        x -= 1
    gutter = 0
    while x >= 0 and filled[x] == 0:
        gutter += 1
        x -= 1
    if strip and strip <= SCROLLBAR_MAX_WIDTH_PX and gutter >= SCROLLBAR_MIN_GUTTER_PX:
        return strip + gutter
    return 0


def _first_sidebar_text(rgb: np.ndarray) -> int | None:
    """First row of the sidebar holding anything other than its own background.

    The sidebar is a solid block, so "not white" is true of every row in it and useless
    here. What matters is the first row that differs from the block's own colour: the
    navigation labels, and the highlight box behind whichever page is open.
    """
    if rgb.size == 0:
        return None
    background = np.median(rgb.reshape(-1, 3), axis=0)
    ink = np.abs(rgb.astype(int) - background).sum(axis=2) > SIDEBAR_INK_DELTA
    rows = np.where(ink.any(axis=1))[0]
    return int(rows[0]) if len(rows) else None


def _sidebar_end(mask: np.ndarray) -> int:
    """Last column of the solid left sidebar, or 0 when there is no sidebar."""
    filled = mask.mean(axis=0)
    end = 0
    for x in range(mask.shape[1]):
        if filled[x] > 0.5:
            end = x
        elif end:
            break
    return end


def crop_box(image: Image.Image) -> tuple[int, int, int, int] | None:
    """Where the dashboard actually is, or None when the file is already tight."""
    mask = _content_mask(image)
    if not mask.any():
        return None
    rgb_full = np.asarray(image.convert("RGB"))

    # Discard the unpainted part of the canvas FIRST. Everything after this reasons about
    # the page, not about the frame it was dropped into. Measuring the sidebar against the
    # full frame is what broke the first version of this: the sidebar filled exactly half
    # the frame's height, tied with the "more than half a column" test, and lost.
    rows = np.where(mask.any(axis=1))[0]
    columns = np.where(mask.any(axis=0))[0]
    page_left, page_top = int(columns[0]), int(rows[0])
    page = mask[page_top : int(rows[-1]) + 1, page_left : int(columns[-1]) + 1]
    page_rgb = rgb_full[page_top : int(rows[-1]) + 1, page_left : int(columns[-1]) + 1]

    sidebar = _sidebar_end(page)
    blank_row = _toolbar_band(page, sidebar)

    # Drop the scrollbar BEFORE measuring anything else. It runs the full height of the
    # viewport, lower than the page content does, so leaving it in place lets it set the
    # bottom edge as well as the right one. Doing this in the wrong order made the crop
    # non-idempotent: a second run found more to remove, which means the first run was
    # wrong rather than that the second one was clever.
    below = page[blank_row:]
    scrollbar = _scrollbar_width(below)
    if scrollbar:
        below = below[:, :-scrollbar]

    rows = np.where(below.any(axis=1))[0]
    columns = np.where(below.any(axis=0))[0]
    if len(rows) == 0 or len(columns) == 0:
        return None

    # THE TOP EDGE, which took three attempts to get right.
    #
    # It cannot follow the whole page: the sidebar is solid grey with ink on every row, so
    # the page always answers "content starts immediately" and the crop lands back inside
    # the toolbar band. That left half a "Stop" button on every file.
    #
    # It cannot follow the main column alone either. On the Home screen the sidebar's
    # selected item is highlighted, and its box starts higher than anything in the main
    # column, so cropping to the main column sliced "Home" in half.
    #
    # So: whichever of the two starts first, and never above the toolbar.
    main_rows = np.where(below[:, sidebar + 1 :].any(axis=1))[0]
    first_main = int(main_rows[0]) if len(main_rows) else int(rows[0])
    first_side = _first_sidebar_text(page_rgb[blank_row:, : sidebar + 1])
    first = min(first_main, first_side) if first_side is not None else first_main
    top = page_top + max(blank_row, blank_row + first - TOP_MARGIN_PX)

    box = (
        page_left + int(columns[0]),
        top,
        page_left + int(columns[-1]) + 1,
        page_top + blank_row + int(rows[-1]) + 1,
    )
    return None if box == (0, 0, image.width, image.height) else box


def main(argv: list[str]) -> int:
    check_only = "--check" in argv
    targets = [Path(a) for a in argv if not a.startswith("--")]
    if not targets:
        targets = sorted(DEFAULT_DIR.glob("*.png"))
    if not targets:
        print(f"no PNG files found in {DEFAULT_DIR}")
        return 1

    changed = 0
    for path in targets:
        image = Image.open(path)
        before_size = path.stat().st_size
        box = crop_box(image)
        if box is None:
            print(f"{path.name:24s} {image.width}x{image.height}  already tight")
            continue

        cropped = image.crop(box)
        verb = "would crop" if check_only else "cropped"
        if not check_only:
            cropped.save(path, optimize=True)
        after = path.stat().st_size if not check_only else before_size
        print(
            f"{path.name:24s} {image.width}x{image.height} -> {cropped.width}x{cropped.height}"
            f"  {before_size / 1024:5.0f} KB -> {after / 1024:5.0f} KB  {verb}"
        )
        changed += 1

    if check_only and changed:
        print(f"\n{changed} file(s) have margin to remove. Re-run without --check.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
