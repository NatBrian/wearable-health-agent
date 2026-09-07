#!/usr/bin/env python
"""Cut the film together: cards, recorded segments, captions, chapter markers.

    uv run python tools/demo_film/cards.py     # render the frames first
    uv run python tools/demo_film/film.py      # record the live segments
    uv run python tools/demo_film/assemble.py

Everything is driven by `script.yaml`, so re-cutting after a wording change costs one
command and no re-shooting.

Captions are collected into a single subtitle file and burned once at the end, rather than
drawn per segment. Two reasons: `drawtext` escaping on Windows is a source of silent
failures, and one subtitle file is a thing you can read and check before committing to a
twenty minute render.

Output:
    docs/demo/wha-demo.mp4          the film
    docs/demo/chapters.txt          timestamps, for a video description
    docs/demo/captions.srt          every caption, with its timing
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "tools" / "demo_film" / "script.yaml"
CARD_DIR = REPO_ROOT / "docs" / "demo" / "cards"
STILL_DIR = REPO_ROOT / "docs" / "demo" / "telegram"
FOOTAGE_DIR = REPO_ROOT / "docs" / "demo" / "footage"
OUT_DIR = REPO_ROOT / "docs" / "demo"

WIDTH, HEIGHT, FPS = 1920, 1080, 30
TITLE_SECONDS = 3.0

# How long a caption stays up. Slow enough to read twice, which is what a viewer does when
# a sentence carries a number.
CAPTION_SECONDS = 4.5


@dataclass
class Segment:
    path: Path
    seconds: float
    kind: str  # "title", "card" or "live"
    chapter: int
    captions: tuple[str, ...] = ()


def ffmpeg(*args: str) -> None:
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"ffmpeg failed:\n{' '.join(args)}\n{result.stderr[-2000:]}")


def probe_seconds(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"ffprobe failed on {path}:\n{result.stderr}")
    return float(result.stdout.strip())


def slug_for(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:48]


def still_to_clip(image: Path, seconds: float, dest: Path) -> None:
    """A still frame becomes a clip. Encoded to match the live footage exactly.

    Same resolution, frame rate, pixel format and codec, or the concat demuxer produces a
    file that plays for a while and then stops without an error.
    """
    ffmpeg(
        "-loop",
        "1",
        "-framerate",
        str(FPS),
        "-t",
        f"{seconds:.3f}",
        "-i",
        str(image),
        "-vf",
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2:white,format=yuv420p",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-r",
        str(FPS),
        str(dest),
    )


def footage_to_clip(source: Path, dest: Path) -> None:
    ffmpeg(
        "-i",
        str(source),
        "-vf",
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2:white,format=yuv420p",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-r",
        str(FPS),
        "-an",
        str(dest),
    )


def timestamp(seconds: float) -> str:
    whole = int(seconds)
    ms = round((seconds - whole) * 1000)
    return f"{whole // 3600:02d}:{whole % 3600 // 60:02d}:{whole % 60:02d},{ms:03d}"


def marker(seconds: float) -> str:
    whole = int(seconds)
    return f"{whole // 60:02d}:{whole % 60:02d}"


def build_segments(script: dict, work: Path) -> list[Segment]:
    segments: list[Segment] = []
    missing_footage: list[str] = []

    for act in script["acts"]:
        for chapter in act["chapters"]:
            cid, title = chapter["id"], chapter["title"]
            slug = slug_for(title)

            title_png = CARD_DIR / f"{cid:02d}-{slug}-title.png"
            if not title_png.is_file():
                raise SystemExit(f"no title frame for chapter {cid}. Run cards.py first.")
            title_clip = work / f"{cid:02d}-0-title.mp4"
            still_to_clip(title_png, TITLE_SECONDS, title_clip)
            segments.append(Segment(title_clip, TITLE_SECONDS, "title", cid))

            form = chapter.get("form", "card")
            captions = tuple(chapter.get("captions") or ())

            if "live" in form or "stills" in form:
                shot = FOOTAGE_DIR / f"{cid:02d}-{slug}.mp4"
                if shot.is_file():
                    clip = work / f"{cid:02d}-1-live.mp4"
                    footage_to_clip(shot, clip)
                    segments.append(Segment(clip, probe_seconds(clip), "live", cid, captions))
                    captions = ()
                else:
                    missing_footage.append(f"chapter {cid}: {shot.name}")

            # Telegram stills. Real messages this build sent to a real phone, held on
            # screen long enough to read rather than flashed past.
            for order, entry in enumerate(chapter.get("stills") or []):
                name, hold = entry
                still = STILL_DIR / f"{name}.png"
                if not still.is_file():
                    print(f"   chapter {cid}: no still {still.name}")
                    continue
                clip = work / f"{cid:02d}-1s{order}-still.mp4"
                still_to_clip(still, float(hold), clip)
                segments.append(Segment(clip, float(hold), "still", cid, captions))
                captions = ()

            card_png = CARD_DIR / f"{cid:02d}-{slug}.png"
            if card_png.is_file():
                seconds = float(chapter.get("seconds", 45))
                if "live" in form:
                    # The card supports a live segment rather than carrying the chapter,
                    # so it needs less time on screen.
                    seconds = max(12.0, seconds * 0.45)
                clip = work / f"{cid:02d}-2-card.mp4"
                still_to_clip(card_png, seconds, clip)
                segments.append(Segment(clip, seconds, "card", cid, captions))
                captions = ()

            after = tuple(chapter.get("captions_after") or ())
            if after and segments:
                segments[-1] = Segment(
                    segments[-1].path,
                    segments[-1].seconds,
                    segments[-1].kind,
                    cid,
                    segments[-1].captions + after,
                )

    if missing_footage:
        print("NO FOOTAGE YET, cutting the cards only for these:")
        for line in missing_footage:
            print(f"   {line}")
    return segments


def write_captions(segments: list[Segment], path: Path) -> None:
    lines: list[str] = []
    index = 1
    clock = 0.0
    for segment in segments:
        if segment.captions:
            # Spread them across the segment, never letting one run past its end.
            each = min(CAPTION_SECONDS, segment.seconds / len(segment.captions))
            start = clock + max(0.0, (segment.seconds - each * len(segment.captions)) / 2)
            for caption in segment.captions:
                lines.append(
                    f"{index}\n{timestamp(start)} --> {timestamp(start + each)}\n{caption}\n"
                )
                index += 1
                start += each
        clock += segment.seconds
    path.write_text("\n".join(lines), encoding="utf-8")


def write_chapters(script: dict, segments: list[Segment], path: Path) -> None:
    titles = {
        chapter["id"]: chapter["title"] for act in script["acts"] for chapter in act["chapters"]
    }
    lines, clock, seen = [], 0.0, set()
    for segment in segments:
        if segment.chapter not in seen:
            lines.append(f"{marker(clock)}  {titles[segment.chapter]}")
            seen.add(segment.chapter)
        clock += segment.seconds
    lines.append("")
    lines.append(f"Total: {marker(clock)}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__ or "")
    parser.add_argument(
        "--no-captions", action="store_true", help="skip the burn-in, for a quick check"
    )
    args = parser.parse_args()

    if shutil.which("ffmpeg") is None:
        raise SystemExit("ffmpeg is not on PATH")

    script = yaml.safe_load(SCRIPT.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="wha-film-") as tmp:
        work = Path(tmp)
        segments = build_segments(script, work)

        listing = work / "concat.txt"
        listing.write_text(
            "\n".join(f"file '{s.path.as_posix()}'" for s in segments) + "\n",
            encoding="utf-8",
        )

        silent = work / "silent.mp4"
        ffmpeg("-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(silent))

        srt = OUT_DIR / "captions.srt"
        write_captions(segments, srt)
        write_chapters(script, segments, OUT_DIR / "chapters.txt")

        final = OUT_DIR / "wha-demo.mp4"
        if args.no_captions or srt.stat().st_size == 0:
            shutil.copyfile(silent, final)
        else:
            # Run from the subtitle file's own directory. An absolute Windows path inside
            # a filter argument has to be escaped twice and fails quietly when it is not.
            staged = work / "captions.srt"
            shutil.copyfile(srt, staged)
            style = (
                "FontName=Segoe UI,FontSize=22,PrimaryColour=&H00FFFFFF,"
                "BackColour=&H90000000,BorderStyle=4,Outline=0,Shadow=0,"
                "MarginV=60,Alignment=2"
            )
            subprocess.run(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-i",
                    str(silent),
                    "-vf",
                    f"subtitles=captions.srt:force_style='{style}'",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "medium",
                    "-crf",
                    "18",
                    str(final),
                ],
                cwd=work,
                check=True,
            )

        total = probe_seconds(final)
        print(f"\n{final}")
        print(f"{len(segments)} segments, {marker(total)} long")
        print(f"chapters: {OUT_DIR / 'chapters.txt'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
