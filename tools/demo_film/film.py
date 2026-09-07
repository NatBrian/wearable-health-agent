#!/usr/bin/env python
"""Record the film's live segments by driving the real dashboard.

    uv run python tools/demo_film/film.py                # every scene
    uv run python tools/demo_film/film.py --only 13      # one chapter, while working on it
    uv run python tools/demo_film/film.py --list

Each scene restores the database snapshot for its day, starts the API and dashboard
against it with the clock shifted to that day, drives the browser, and saves the recording
to `docs/demo/footage/NN-slug.mp4` where `assemble.py` picks it up.

WHY THE SERVER RESTARTS FOR EVERY SCENE. The clock offset is read from the environment of
the process that serves the page, so a scene set on 13 September and one set on 22
September cannot share a server. Ten seconds of start-up per scene is the price of every
screen showing the date it is supposed to be showing.

WHY THE PAGE IS ZOOMED RATHER THAN THE VIEWPORT NARROWED. Playwright records video at the
viewport size and ignores the device scale factor, so a 1280 wide viewport gives a 1280
wide video that has to be upscaled and goes soft. Recording at a native 1920x1080 and
setting a page zoom of 1.5 gives the same 1280 wide LAYOUT that the pre-flight checked,
with every pixel real.

Nothing here is scripted to look better than it is. Every screen is the product, driven
through its own interface, over a database the build pass produced.
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import httpx
from playwright.sync_api import Page, sync_playwright

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "demo_film"))

SNAPSHOT_DIR = REPO_ROOT / "data" / "demo-snapshots"
LIVE_DB = REPO_ROOT / "data" / "demo_film_live.sqlite"
FOOTAGE = REPO_ROOT / "docs" / "demo" / "footage"
RAW = REPO_ROOT / "docs" / "demo" / "footage-raw"

BASE = "http://localhost:8501"
API = "http://localhost:8500"
WIDTH, HEIGHT = 1920, 1080

# Page zoom, per scene. 1.5 gives the 1280 wide layout the pre-flight checked, which reads
# well for prose screens.
#
# The RECORD screen is the exception and it films at 1.0. Its step grid is a fixed number
# of columns, so narrowing the effective width narrows every card: at 1.5 the labels wrap
# character by character, "Subtra ct what is explai ned", which looks like a broken page
# rather than a dense one. At full width the cards are wide enough for their labels and
# the grid is the clearest single image in the film.
DEFAULT_ZOOM = 1.5
RECORD_ZOOM = 1.0

from timeline import DAYS


# Hidden while filming, never in the product: the developer menu and the "running" spinner
# that flickers in the corner of every take.
def film_css(zoom: float) -> str:
    return f"""
[data-testid="stToolbar"], [data-testid="stStatusWidget"], #MainMenu,
[data-testid="stDecoration"] {{ display: none !important; }}
html {{ zoom: {zoom}; }}
"""


SCROLLER = """
    document.querySelector('[data-testid="stAppScrollToBottomContainer"]')
        || document.querySelector('section.stMain')
        || document.querySelector('[data-testid="stAppViewContainer"]')
"""


# --------------------------------------------------------------------------- the stage


class Stage:
    """A page, driven at a pace a person can follow.

    Every method leaves the screen still for long enough to be read. A demo that moves at
    the speed the machine can move at is unwatchable, and the cost of a slow take is
    seconds of runtime rather than anything a viewer pays.
    """

    def __init__(self, page: Page, zoom: float = DEFAULT_ZOOM) -> None:
        self.page = page
        self.css = film_css(zoom)

    def open(self, path: str, settle: float = 4.0) -> Stage:
        print(f"      open {path}")
        # `networkidle` never settles on a page holding a websocket open, and Streamlit
        # holds one. `load` plus a deliberate settle is both faster and reliable.
        self.page.goto(f"{BASE}{path}", wait_until="load", timeout=45000)
        self.page.add_style_tag(content=self.css)
        self.page.wait_for_timeout(int(settle * 1000))
        self.top()
        return self

    def top(self) -> Stage:
        self.page.evaluate(f"() => {{ const m = {SCROLLER}; if (m) m.scrollTop = 0; }}")
        self.page.wait_for_timeout(600)
        return self

    def dwell(self, seconds: float) -> Stage:
        self.page.wait_for_timeout(int(seconds * 1000))
        return self

    def glide(self, to_px: int, seconds: float = 2.0) -> Stage:
        """Scroll smoothly. A jump cut inside a screen loses the viewer's place."""
        self.page.evaluate(
            f"""([target, ms]) => {{
                const m = {SCROLLER};
                if (!m) return;
                const from = m.scrollTop;
                const start = performance.now();
                const step = (now) => {{
                    const t = Math.min(1, (now - start) / ms);
                    const eased = t < 0.5 ? 2*t*t : -1 + (4 - 2*t) * t;
                    m.scrollTop = from + (target - from) * eased;
                    if (t < 1) requestAnimationFrame(step);
                }};
                requestAnimationFrame(step);
            }}""",
            [to_px, int(seconds * 1000)],
        )
        self.page.wait_for_timeout(int(seconds * 1000) + 500)
        return self

    def glide_to(self, text: str, seconds: float = 2.0, offset: int = -120) -> Stage:
        """Scroll until `text` is near the top of the frame.

        Uses Playwright's own text locator. A hand written XPath over text() nodes was
        tried first and matched nothing, because Streamlit splits headings across nested
        elements and the text node is rarely the one carrying the whole phrase.
        """
        try:
            box = self.page.get_by_text(text, exact=False).first.bounding_box(timeout=5000)
        except Exception:  # noqa: BLE001
            box = None
        if box is None:
            print(f"      (nothing matching {text!r} to scroll to)")
            return self
        current = self.page.evaluate(
            f"() => {{ const m = {SCROLLER}; return m ? m.scrollTop : 0; }}"
        )
        return self.glide(int(current + box["y"] + offset), seconds)

    def click(self, selector: str, wait: float = 3.0) -> Stage:
        self.page.click(selector)
        self.page.wait_for_timeout(int(wait * 1000))
        self.page.add_style_tag(content=self.css)
        return self

    def click_text(self, text: str, wait: float = 3.0) -> Stage:
        print(f"      click {text!r}")
        try:
            self.page.get_by_text(text, exact=False).first.click(timeout=8000)
        except Exception as e:  # noqa: BLE001
            print(f"      (could not click {text!r}: {type(e).__name__})")
            return self
        self.page.wait_for_timeout(int(wait * 1000))
        self.page.add_style_tag(content=self.css)
        return self

    def say(self, text: str, wait_for_reply: float = 25.0) -> Stage:
        """Type into the chat the way a person does, then wait for the real reply."""
        print(f"      say {text[:50]!r}")
        box = self.page.get_by_placeholder("Say anything, or ask a question")
        box.click()
        box.type(text, delay=45)
        self.page.wait_for_timeout(900)
        self.page.keyboard.press("Enter")
        self.page.wait_for_timeout(int(wait_for_reply * 1000))
        self.page.add_style_tag(content=self.css)
        return self


# --------------------------------------------------------------------------- the scenes


@dataclass
class Scene:
    chapter: int
    slug: str
    day: date
    act: Callable[[Stage], None]
    note: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)
    zoom: float = DEFAULT_ZOOM


def snapshot_for(day: date) -> Path:
    index = next(i for i, d in enumerate(DAYS, 1) if d.date == day)
    return SNAPSHOT_DIR / f"{index:02d}-{day.isoformat()}.sqlite"


def offset_for(day: date) -> int:
    from datetime import UTC, datetime
    from zoneinfo import ZoneInfo

    today = datetime.now(UTC).astimezone(ZoneInfo("Asia/Singapore")).date()
    return (day - today).days


# Each scene is written as a function so it can do whatever that chapter needs, rather
# than being squeezed into a step vocabulary that would need extending for every one.


def scene_month_of_nights(s: Stage) -> None:
    s.open("/").dwell(4)
    s.glide(700, 2.5).dwell(3)
    s.open("/Today").dwell(6)
    s.glide_to("Last night", 2.0).dwell(5)
    s.glide_to("YOUR READING", 2.0).dwell(6)
    s.open("/History").dwell(6)
    s.glide(500, 2.5).dwell(6)


def scene_quiet_nights(s: Stage) -> None:
    s.open("/History").dwell(5)
    s.glide(420, 2.5).dwell(8)
    s.open("/Today").dwell(5)
    s.glide_to("Last night", 2.0).dwell(6)


def scene_first_red(s: Stage) -> None:
    s.open("/Today").dwell(5)
    s.glide_to("Last night", 2.0).dwell(7)
    s.glide_to("Ask about any of this", 2.0).dwell(4)


def scene_control_loop(s: Stage) -> None:
    s.open("/The_record").dwell(5)
    s.glide_to("From your watch to the conclusion", 2.5).dwell(6)
    s.glide(1100, 2.5).dwell(8)
    s.glide(1700, 2.0).dwell(6)


def scene_one_number(s: Stage) -> None:
    s.open("/The_record").dwell(4)
    s.glide_to("From your watch to the conclusion", 2.5).dwell(3)
    s.click_text("Open step 3", wait=4).dwell(7)
    s.click_text("Open step 4", wait=4).dwell(7)


def scene_your_normal(s: Stage) -> None:
    s.open("/The_record").dwell(4)
    s.glide_to("From your watch to the conclusion", 2.5).dwell(3)
    s.click_text("Open step 5", wait=4).dwell(8)


def scene_agent_wakes(s: Stage) -> None:
    s.open("/Today").dwell(5)
    s.glide_to("Being looked into", 2.0).dwell(6)
    s.open("/The_record").dwell(5)
    s.glide_to("From your watch to the conclusion", 2.5).dwell(4)
    s.click_text("Open step 13", wait=4).dwell(9)
    s.click_text("Open step 12", wait=4).dwell(9)


def scene_grounding(s: Stage) -> None:
    s.open("/Today").dwell(4)
    s.say("what does a high resting heart rate at night usually mean?", 30)
    s.glide(2200, 2.0).dwell(10)


def scene_two_symptoms(s: Stage) -> None:
    s.open("/Today").dwell(5)
    s.glide_to("Last night", 2.0).dwell(5)
    s.glide_to("Being looked into", 2.0).dwell(8)


def scene_audit(s: Stage) -> None:
    s.open("/The_record").dwell(4)
    s.click_text("Everything the system did", wait=5).dwell(6)
    s.glide(600, 2.5).dwell(8)
    s.glide(1200, 2.0).dwell(6)


def scene_not_closing(s: Stage) -> None:
    s.open("/Today").dwell(5)
    s.glide_to("Last night", 2.0).dwell(6)
    s.glide_to("Being looked into", 2.0).dwell(9)


def scene_review(s: Stage) -> None:
    s.open("/Today").dwell(6)
    s.glide_to("Being looked into", 2.0).dwell(8)
    s.glide(1400, 2.0).dwell(8)


def scene_chest_pain(s: Stage) -> None:
    s.open("/Today").dwell(4)
    s.say("I have a heavy pressure in my chest and it is worse when I walk upstairs", 35)
    s.dwell(6)
    s.say("no, pressing on my chest does not make it hurt more", 35)
    s.dwell(8)


def scene_ai_away(s: Stage) -> None:
    s.open("/Home").dwell(5)
    s.glide(500, 2.0).dwell(6)
    s.open("/Today").dwell(4)
    s.say("I have had a fever since yesterday and I keep throwing up", 30)
    s.dwell(8)


SCENES: tuple[Scene, ...] = (
    Scene(
        2,
        "perceive-reason-act",
        date(2026, 9, 13),
        scene_control_loop,
        "the 21 steps, colour coded by which machine ran them",
        zoom=RECORD_ZOOM,
    ),
    Scene(
        3,
        "from-a-wrist-to-one-number",
        date(2026, 9, 13),
        scene_one_number,
        "the sleep window and the one number it produces",
        zoom=RECORD_ZOOM,
    ),
    Scene(
        4,
        "what-your-own-normal-means",
        date(2026, 9, 13),
        scene_your_normal,
        "the baseline, and the refusal to judge before it knows you",
        zoom=RECORD_ZOOM,
    ),
    Scene(
        6,
        "a-month-of-nights",
        date(2026, 9, 11),
        scene_month_of_nights,
        "Home, Today and History on a quiet person",
    ),
    Scene(
        7,
        "four-quiet-nights",
        date(2026, 9, 11),
        scene_quiet_nights,
        "exercise, alcohol and two ordinary nights, none of them an alarm",
    ),
    Scene(
        8,
        "something-starts-and-it-still-says-nothing",
        date(2026, 9, 12),
        scene_first_red,
        "first RED night, and silence",
    ),
    Scene(
        10,
        "the-agent-wakes",
        date(2026, 9, 13),
        scene_agent_wakes,
        "the investigation opens, and the decision to ask",
        zoom=RECORD_ZOOM,
    ),
    Scene(
        12,
        "it-has-to-prove-what-it-says",
        date(2026, 9, 14),
        scene_grounding,
        "a live question, and the sources behind the reply",
    ),
    Scene(
        13,
        "two-symptoms-two-different-nights",
        date(2026, 9, 14),
        scene_two_symptoms,
        "the escalation to same day care",
    ),
    Scene(
        14,
        "everything-it-did-written-down",
        date(2026, 9, 14),
        scene_audit,
        "the journal and the hash chain",
        zoom=RECORD_ZOOM,
    ),
    Scene(
        15,
        "feeling-better-is-not-the-same-as-being-better",
        date(2026, 9, 16),
        scene_not_closing,
        "green night, feels better, stays open",
    ),
    Scene(
        16,
        "it-comes-back-and-the-person-overrules-the-syste",
        date(2026, 9, 17),
        scene_review,
        "the drafted conclusion, waiting to be checked",
    ),
    Scene(
        17,
        "chest-pain-five-questions-then-a-rule-the-ai-can",
        date(2026, 9, 23),
        scene_chest_pain,
        "Marburg elicited live",
        ("live-llm",),
    ),
    Scene(
        18,
        "take-the-ai-away",
        date(2026, 9, 23),
        scene_ai_away,
        "the safety floor with the model unreachable",
        ("no-llm",),
    ),
)


# ---------------------------------------------------------------------------- the rig


def kill_stragglers() -> None:
    """Nothing else may be holding 8500 and 8501 when a scene starts.

    A dashboard left over from the pre-flight, running at a different clock offset, kept
    both ports. The server this rig started could not bind, said nothing about it, and
    Playwright happily filmed the stale one: a scene set on 12 September was recorded
    against a system that believed it was the 23rd, so the screen read "no night has been
    measured yet" over a database that had the night.

    That is the worst failure available here, because the footage looks fine.
    """
    for image in ("streamlit.exe", "uvicorn.exe"):
        subprocess.run(["taskkill", "/F", "/IM", image], capture_output=True, check=False)
    kill_by_port = (
        "Get-NetTCPConnection -LocalPort 8500,8501 -State Listen "
        "-ErrorAction SilentlyContinue | ForEach-Object { "
        "Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", kill_by_port],
        capture_output=True,
        check=False,
    )
    time.sleep(2)


def assert_serving(day: date) -> None:
    """The page must agree about what day it is before a single frame is recorded."""
    reported = httpx.get(f"{API}/config", timeout=5.0).json().get("today")
    if reported != day.isoformat():
        raise SystemExit(
            f"the API says today is {reported} and this scene is set on {day}. Something "
            "else is answering on port 8500, or the clock offset did not reach it. Filming "
            "would have produced a scene showing the wrong day."
        )


def start_server(day: date, tags: tuple[str, ...]) -> subprocess.Popen:
    env = dict(os.environ)
    env["WHA_DB_PATH"] = str(LIVE_DB)
    env["WHA_SUBJECT"] = "demo"
    env["WHA_CLOCK_OFFSET_DAYS"] = str(offset_for(day))
    if "no-llm" in tags:
        # Chapter 18 films what happens when the model cannot be reached. Pointing it at a
        # closed port is the honest version of that: nothing is stubbed, the call simply
        # fails the way it would in an outage.
        env["WHA_LLM_BASE_URL"] = "http://127.0.0.1:9"
    return subprocess.Popen(
        ["uv", "run", "wha", "serve", "--no-scheduler", "--db", str(LIVE_DB)],
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def wait_for_server(timeout: float = 120.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            httpx.get(f"{API}/health", timeout=2.0)
            httpx.get(BASE, timeout=2.0)
        except Exception:  # noqa: BLE001
            time.sleep(2)
            continue
        time.sleep(3)  # streamlit needs a moment after the port opens
        return
    raise SystemExit("the dashboard did not come up")


def stop_server(process: subprocess.Popen) -> None:
    if process.poll() is None:
        process.send_signal(signal.SIGTERM)
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
    # Streamlit spawns a child that holds the database open, and the next scene cannot
    # overwrite the file while it does.
    kill_stragglers()


def record(scene: Scene) -> Path:
    snapshot = snapshot_for(scene.day)
    if not snapshot.is_file():
        raise SystemExit(f"no snapshot for {scene.day}: {snapshot}")
    shutil.copyfile(snapshot, LIVE_DB)

    kill_stragglers()
    server = start_server(scene.day, scene.tags)
    try:
        wait_for_server()
        assert_serving(scene.day)
        RAW.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(
                viewport={"width": WIDTH, "height": HEIGHT},
                record_video_dir=str(RAW),
                record_video_size={"width": WIDTH, "height": HEIGHT},
            )
            page = context.new_page()
            page.set_default_timeout(15000)
            page.set_default_navigation_timeout(45000)
            scene.act(Stage(page, scene.zoom))
            page.wait_for_timeout(1500)
            video = page.video
            context.close()
            source = Path(video.path()) if video else None
            browser.close()
    finally:
        stop_server(server)

    if source is None or not source.is_file():
        raise SystemExit(f"no video came out of chapter {scene.chapter}")

    FOOTAGE.mkdir(parents=True, exist_ok=True)
    dest = FOOTAGE / f"{scene.chapter:02d}-{scene.slug}.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            str(dest),
        ],
        check=True,
    )
    source.unlink(missing_ok=True)
    return dest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__ or "")
    parser.add_argument("--only", type=int, action="append", help="chapter id, repeatable")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    if args.list:
        for scene in SCENES:
            print(f"{scene.chapter:>3}  {scene.day}  {scene.slug:<48} {scene.note}")
        return 0

    chosen = [s for s in SCENES if not args.only or s.chapter in args.only]
    if not chosen:
        raise SystemExit("no scenes matched")

    for index, scene in enumerate(chosen, 1):
        print(f"\n[{index}/{len(chosen)}] chapter {scene.chapter}: {scene.note}")
        print(f"    {scene.day}, clock {offset_for(scene.day):+d} days")
        started = time.time()
        dest = record(scene)
        print(f"    {dest.name}  ({time.time() - started:.0f}s)")

    print(f"\nfootage in {FOOTAGE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
