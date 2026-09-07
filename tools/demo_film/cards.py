#!/usr/bin/env python
"""Render the film's full frame cards from `script.yaml`.

    uv run python tools/demo_film/cards.py            # all of them
    uv run python tools/demo_film/cards.py --only 9   # one, while wording it

Cards carry everything the product cannot show on screen: the reasoning, the measured
tables, the citations, the chapter titles. They are rendered rather than screenshotted so
that changing a word is an edit and not a re-shoot.

They deliberately use the DASHBOARD'S own palette, from `src/wha/ui/design.py`: dark text
on pale grounds, colour only where it carries meaning. A film whose explanatory frames look
like a different product than the one being explained is doing the viewer no favours.

Two lines of text get different fonts on purpose. A line holding two or more consecutive
spaces is a table, and is set in a monospace face so its columns line up. Everything else
is proportional, because a non-engineer reads monospace as "code" and stops reading.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "tools" / "demo_film" / "script.yaml"
OUT_DIR = REPO_ROOT / "docs" / "demo" / "cards"

WIDTH, HEIGHT = 1920, 1080
MARGIN_X, MARGIN_TOP = 150, 130

# From src/wha/ui/design.py. Dark text on a pale ground, because a health screen is read
# for minutes at a time and saturated fills are tiring.
INK = (26, 29, 33)
INK_SOFT = (91, 97, 105)
PAPER = (255, 255, 255)
RULE = (223, 227, 231)
ACCENT = (10, 74, 114)  # the "agentic" layer blue
ACCENT_SOFT = (232, 242, 249)

FONTS = Path("C:/Windows/Fonts")
F_HEAD = FONTS / "segoeuib.ttf"
F_BODY = FONTS / "segoeui.ttf"
F_ITAL = FONTS / "segoeuii.ttf"
F_MONO = FONTS / "consola.ttf"

_TABLE_LINE = re.compile(r"\S {2,}\S")


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    if not path.is_file():
        raise SystemExit(f"font not found: {path}")
    return ImageFont.truetype(str(path), size)


def wrap(draw: ImageDraw.ImageDraw, text: str, f: ImageFont.FreeTypeFont, width: int) -> list[str]:
    """Greedy wrap. Lines that are tables are never wrapped, because wrapping breaks them."""
    if _TABLE_LINE.search(text):
        return [text]
    words, lines, current = text.split(), [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=f) <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def render_card(chapter: dict, act_title: str) -> Image.Image:
    card = chapter.get("card") or {}
    image = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
    draw = ImageDraw.Draw(image)

    f_eyebrow = font(F_BODY, 30)
    f_head = font(F_HEAD, 60)
    f_body = font(F_BODY, 40)
    f_mono = font(F_MONO, 35)
    f_foot = font(F_ITAL, 32)

    # A quiet eyebrow so a viewer who joins mid-film knows where they are.
    draw.text((MARGIN_X, 70), act_title.upper(), font=f_eyebrow, fill=INK_SOFT)

    y = MARGIN_TOP + 30
    inner = WIDTH - 2 * MARGIN_X

    for line in wrap(draw, card.get("heading", chapter.get("title", "")), f_head, inner):
        draw.text((MARGIN_X, y), line, font=f_head, fill=INK)
        y += 78

    y += 20
    draw.line([(MARGIN_X, y), (MARGIN_X + 120, y)], fill=ACCENT, width=5)
    body_top = y + 55

    # Lay the body out before drawing it, so the block can be centred in the space that is
    # left. Drawing from the top produced a card with all its text in the upper half and a
    # third of the frame empty above the footer.
    #
    # Prose paragraphs are JOINED before wrapping. The source is hard-wrapped for the
    # benefit of whoever edits the yaml, and honouring those breaks produced ragged lines
    # that stop short of the margin for no reason. Table lines keep their own breaks,
    # because that is the only thing holding their columns together.
    laid_out: list[tuple[str, ImageFont.FreeTypeFont, tuple[int, int, int], int]] = []
    paragraph: list[str] = []

    def flush() -> None:
        if not paragraph:
            return
        for line in wrap(draw, " ".join(paragraph), f_body, inner):
            laid_out.append((line, f_body, INK, 58))
        paragraph.clear()

    for raw in (card.get("body") or "").rstrip().split("\n"):
        if not raw.strip():
            flush()
            laid_out.append(("", f_body, INK, 26))
            continue
        if _TABLE_LINE.search(raw):
            flush()
            laid_out.append((raw.rstrip(), f_mono, ACCENT, 52))
        else:
            paragraph.append(raw.strip())
    flush()

    while laid_out and laid_out[-1][0] == "":
        laid_out.pop()

    block_height = sum(step for _, _, _, step in laid_out)
    available = (HEIGHT - 190) - body_top
    y = body_top + max(0, (available - block_height) // 2)

    for line, f, colour, step in laid_out:
        if line:
            draw.text((MARGIN_X, y), line, font=f, fill=colour)
        y += step

    footer = (card.get("footer") or "").strip()
    if footer:
        box_top = HEIGHT - 190
        draw.rectangle([(0, box_top), (WIDTH, HEIGHT)], fill=ACCENT_SOFT)
        fy = box_top + 45
        for line in wrap(draw, footer, f_foot, inner):
            draw.text((MARGIN_X, fy), line, font=f_foot, fill=ACCENT)
            fy += 46

    if y > HEIGHT - 210:
        raise SystemExit(
            f"chapter {chapter.get('id')} overflows its frame (text reached {y} of "
            f"{HEIGHT - 210}). Shorten the body rather than shrinking the type: this is "
            "read from across a room."
        )
    return image


def render_title(chapter: dict, act_title: str) -> Image.Image:
    """A chapter title, for the beat before a live segment starts."""
    image = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
    draw = ImageDraw.Draw(image)
    f_eyebrow = font(F_BODY, 32)
    f_head = font(F_HEAD, 72)

    draw.text((MARGIN_X, HEIGHT // 2 - 150), act_title.upper(), font=f_eyebrow, fill=INK_SOFT)
    y = HEIGHT // 2 - 80
    for line in wrap(draw, chapter.get("title", ""), f_head, WIDTH - 2 * MARGIN_X):
        draw.text((MARGIN_X, y), line, font=f_head, fill=INK)
        y += 92
    draw.line([(MARGIN_X, y + 30), (MARGIN_X + 120, y + 30)], fill=ACCENT, width=5)
    return image


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__ or "")
    parser.add_argument("--only", type=int, help="render one chapter by id")
    args = parser.parse_args()

    script = yaml.safe_load(SCRIPT.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    written = 0
    for act in script["acts"]:
        for chapter in act["chapters"]:
            if args.only is not None and chapter["id"] != args.only:
                continue
            slug = re.sub(r"[^a-z0-9]+", "-", chapter["title"].lower()).strip("-")[:48]
            title_path = OUT_DIR / f"{chapter['id']:02d}-{slug}-title.png"
            render_title(chapter, act["act"]).save(title_path)
            written += 1
            if chapter.get("card"):
                card_path = OUT_DIR / f"{chapter['id']:02d}-{slug}.png"
                render_card(chapter, act["act"]).save(card_path)
                written += 1

    print(f"wrote {written} frames to {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
