#!/usr/bin/env python
"""Record the existing demo film scenes from the Vite dashboard.

    uv run python tools/demo_film/film_vite.py --list
    uv run python tools/demo_film/film_vite.py --only 1 --only 2

The API and Vite frontend must already be serving the demo subject. The recorder uses the
dashboard's accessible controls. Chapter 12 displays actual turns already submitted through
the real chat panel and API, including their source-status labels. Chapter 18 is separate: it
records one fixed-rule fallback against a disposable clone with the model disabled. No
setting is saved.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from playwright.sync_api import Locator, Page, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "demo_film"))

from assemble import probe_seconds, slug_for

FRONTEND = "http://127.0.0.1:8443/"
WIDTH, HEIGHT = 1920, 1080
ZOOM = 1.25
DEFAULT_OUTPUT = REPO_ROOT / "docs" / "demo" / "footage-vite"


class Stage:
    """Drive the real dashboard at a pace that leaves each screen readable."""

    def __init__(self, page: Page) -> None:
        self.page = page

    def wait(self, seconds: float = 2.0) -> Stage:
        self.page.wait_for_timeout(int(seconds * 1000))
        return self

    def primary(self, name: str) -> Stage:
        navigation = self.page.get_by_role("navigation", name="Main navigation")
        navigation.get_by_role("button", name=name).click()
        self.wait(1.0)
        return self

    def dashboard_tab(self, name: str) -> Stage:
        tabs = self.page.get_by_role("tablist", name="Dashboard sections")
        tabs.get_by_role("tab", name=name).click()
        self.wait(1.0)
        return self

    def pipeline_tab(self, name: str) -> Stage:
        tabs = self.page.get_by_role("tablist", name="Pipeline sections")
        tabs.get_by_role("tab", name=name).click()
        self.wait(1.0)
        return self

    def night(self, night_date: str) -> Stage:
        self.page.get_by_label("Which night", exact=False).select_option(night_date)
        self.page.wait_for_function(
            "date => document.querySelector('.night-navigation select')?.value === date "
            "&& document.querySelector('.pipeline-card')?.innerText.includes('From your watch to the conclusion')",
            arg=night_date,
            timeout=15000,
        )
        self.wait(0.8)
        return self

    def history_night(self, night_date: str) -> Stage:
        button = self.page.get_by_role(
            "button", name=re.compile(rf"^{re.escape(night_date)},")
        )
        button.click()
        self.wait(1.0)
        return self

    def focus(self, locator: Locator) -> Stage:
        box = locator.bounding_box()
        scroller = self.page.locator(".workspace-scroll")
        if box is None or scroller.count() == 0:
            locator.scroll_into_view_if_needed()
            return self.wait(0.8)
        current = scroller.evaluate("element => element.scrollTop")
        target = max(0, int(current + box["y"] - 130))
        self.glide(target, 1.5)
        return self

    def glide(self, target: int, seconds: float = 1.8) -> Stage:
        self.page.evaluate(
            """([target, duration]) => {
              const element = document.querySelector('.workspace-scroll');
              if (!element) return;
              const startTop = element.scrollTop;
              const startTime = performance.now();
              const step = now => {
                const progress = Math.min(1, (now - startTime) / duration);
                const eased = progress < 0.5
                  ? 2 * progress * progress
                  : 1 - Math.pow(-2 * progress + 2, 2) / 2;
                element.scrollTop = startTop + (target - startTop) * eased;
                if (progress < 1) requestAnimationFrame(step);
              };
              requestAnimationFrame(step);
            }""",
            [target, int(seconds * 1000)],
        )
        return self.wait(seconds + 0.4)

    def glide_chat(self, target: int, seconds: float = 1.5) -> Stage:
        self.page.evaluate(
            """([target, duration]) => {
              const element = document.querySelector('.chat-transcript');
              if (!element) return;
              const startTop = element.scrollTop;
              const startTime = performance.now();
              const step = now => {
                const progress = Math.min(1, (now - startTime) / duration);
                const eased = progress < 0.5
                  ? 2 * progress * progress
                  : 1 - Math.pow(-2 * progress + 2, 2) / 2;
                element.scrollTop = startTop + (target - startTop) * eased;
                if (progress < 1) requestAnimationFrame(step);
              };
              requestAnimationFrame(step);
            }""",
            [target, int(seconds * 1000)],
        )
        return self.wait(seconds + 0.4)


@dataclass(frozen=True)
class Scene:
    chapter: int
    title: str
    note: str
    act: Callable[[Stage], None]

    @property
    def slug(self) -> str:
        return slug_for(self.title)


def scene_opening(stage: Stage) -> None:
    stage.wait(3.0)
    stage.focus(stage.page.get_by_role("heading", name="Resting HR trend"))
    stage.wait(3.0)
    stage.primary("Pipeline")
    stage.pipeline_tab("System overview")
    stage.focus(stage.page.get_by_role("heading", name="Detection layer"))
    stage.wait(5.0)


def scene_pipeline(stage: Stage) -> None:
    stage.primary("Pipeline")
    stage.pipeline_tab("This night, step by step")
    stage.night("2026-09-13")
    heading = stage.page.get_by_role("heading", name="From your watch to the conclusion")
    stage.focus(heading)
    stage.wait(4.0)
    stage.glide(950, 2.0)
    stage.wait(5.0)


def scene_one_number(stage: Stage) -> None:
    stage.primary("Pipeline")
    stage.pipeline_tab("This night, step by step")
    stage.night("2026-09-06")
    stage.page.get_by_role("button", name=re.compile("One number for the night")).click()
    stage.focus(stage.page.locator(".step-detail"))
    stage.wait(8.0)


def scene_own_normal(stage: Stage) -> None:
    stage.primary("Pipeline")
    stage.pipeline_tab("This night, step by step")
    stage.night("2026-09-06")
    stage.page.get_by_role("button", name=re.compile("Your normal")).click()
    stage.focus(stage.page.locator(".step-detail"))
    stage.wait(9.0)


def scene_month(stage: Stage) -> None:
    stage.primary("Dashboard")
    stage.dashboard_tab("Overview")
    stage.wait(4.0)
    stage.primary("Dashboard")
    stage.dashboard_tab("History")
    stage.focus(stage.page.get_by_role("heading", name="Your nights over time"))
    stage.wait(8.0)
    stage.glide(430, 1.8)
    stage.wait(5.0)


def scene_quiet_nights(stage: Stage) -> None:
    stage.primary("Pipeline")
    stage.pipeline_tab("This night, step by step")
    stage.night("2026-09-08")
    stage.page.get_by_role("button", name=re.compile("Subtract what is explained")).click()
    stage.focus(stage.page.locator(".step-detail"))
    stage.wait(7.0)
    stage.night("2026-09-09")
    stage.page.get_by_role("button", name=re.compile("Judge the night")).click()
    stage.focus(stage.page.locator(".step-detail"))
    stage.wait(8.0)


def scene_first_red(stage: Stage) -> None:
    stage.primary("Pipeline")
    stage.pipeline_tab("This night, step by step")
    stage.night("2026-09-12")
    stage.page.get_by_role("button", name=re.compile("Open an investigation")).click()
    stage.focus(stage.page.locator(".step-detail"))
    stage.wait(10.0)


def scene_agent_wakes(stage: Stage) -> None:
    stage.primary("Pipeline")
    stage.pipeline_tab("This night, step by step")
    stage.night("2026-09-13")
    stage.page.get_by_role("button", name=re.compile("AI gathers evidence")).click()
    stage.focus(stage.page.locator(".step-detail"))
    stage.wait(6.0)
    stage.page.get_by_role("button", name=re.compile("Ask you")).click()
    stage.focus(stage.page.locator(".step-detail"))
    stage.wait(9.0)


def scene_grounding(stage: Stage) -> None:
    stage.primary("Pipeline")
    stage.pipeline_tab("Everything the system did")
    archive = stage.page.locator(".archive-list")
    archive.wait_for(state="visible", timeout=15000)
    archive.locator(".archive-session").nth(1).locator("summary").click()
    stage.focus(stage.page.get_by_text("Sources behind this reply").first)
    stage.wait(7.0)

    stage.primary("Dashboard")
    stage.dashboard_tab("Overview")
    stage.page.get_by_role("button", name=re.compile("Open Agent Chat")).click()
    stage.page.get_by_role("heading", name="Ask about any of this").wait_for(timeout=15000)
    transcript = stage.page.locator(".chat-transcript")
    transcript.locator(".chat-turn--agent").nth(1).wait_for(state="visible", timeout=60000)
    user_count = transcript.locator(".chat-turn--user").count()
    agent_turns = transcript.locator(".chat-turn--agent")
    if user_count < 2 or agent_turns.count() < 2:
        raise SystemExit(
            "Chapter 12 needs at least two actual user/API/agent exchanges already "
            "recorded for the demo night."
        )
    for index in range(agent_turns.count()):
        _require_live_chat_turn(agent_turns.nth(index))
    if transcript.locator('[aria-label="Source status unavailable"]').count() == 0:
        raise SystemExit("The live chat has no visible missing-source-status warning.")

    max_scroll = transcript.evaluate("element => element.scrollHeight - element.clientHeight")
    for position in (0, max_scroll * 0.5, max_scroll):
        stage.glide_chat(position)
        stage.wait(5.0)


def _require_live_chat_turn(turn: Locator) -> None:
    reply = turn.locator(":scope > p").inner_text().strip()
    if not reply:
        raise SystemExit("The live chat turn returned an empty agent message.")
    if "I cannot reach the language model right now" in reply:
        raise SystemExit("The live model is unavailable; the chat scene was not captured.")
    status = turn.locator(
        '[aria-label="Sources behind this reply"], '
        '[aria-label="Not from a cited source"], '
        '[aria-label="Source status unavailable"]',
    )
    status.wait_for(state="visible", timeout=10000)


def scene_safety(stage: Stage) -> None:
    stage.primary("Pipeline")
    stage.pipeline_tab("This night, step by step")
    stage.night("2026-09-18")
    stage.page.get_by_role("button", name=re.compile("Check what you told us")).click()
    stage.focus(stage.page.locator(".step-detail"))
    stage.wait(12.0)


def scene_audit(stage: Stage) -> None:
    stage.primary("Pipeline")
    stage.pipeline_tab("Everything the system did")
    stage.wait(4.0)
    stage.focus(stage.page.get_by_role("heading", name="Conversations"))
    stage.wait(8.0)
    stage.focus(stage.page.get_by_role("heading", name="Every recorded action"))
    stage.wait(7.0)


def scene_recovery(stage: Stage) -> None:
    stage.primary("Dashboard")
    stage.dashboard_tab("History")
    stage.history_night("2026-09-22")
    stage.focus(stage.page.get_by_role("heading", name="Look at one night in full"))
    stage.wait(11.0)


def scene_human_review(stage: Stage) -> None:
    stage.primary("Pipeline")
    stage.pipeline_tab("Everything the system did")
    select = stage.page.get_by_label("What kind of action", exact=False)
    select.select_option(label="human_decision")
    stage.wait(2.0)
    stage.focus(stage.page.get_by_role("region", name="Recorded actions"))
    stage.wait(10.0)


def scene_marburg(stage: Stage) -> None:
    stage.primary("Pipeline")
    stage.pipeline_tab("How this works")
    safety_topic = stage.page.get_by_text(
        "The safety rules, which run before anything else", exact=True
    )
    safety_topic.click()
    rule = stage.page.get_by_text("marburg_heart_score", exact=False).first
    rule.wait_for(state="visible", timeout=15000)
    stage.focus(rule)
    stage.wait(12.0)


def scene_ai_away(stage: Stage) -> None:
    stage.primary("Dashboard")
    stage.dashboard_tab("Overview")
    stage.wait(4.0)
    stage.page.get_by_role("button", name=re.compile("Open Agent Chat")).click()
    stage.wait(4.0)
    stage.focus(stage.page.get_by_role("heading", name="Ask about any of this"))
    prompt = "I have had a fever since yesterday and I keep throwing up"
    previous_prompt = stage.page.get_by_text(prompt, exact=True)
    try:
        previous_prompt.wait_for(state="visible", timeout=5000)
    except PlaywrightTimeoutError:
        stage.page.get_by_text("No conversation has been recorded for this night.").wait_for(
            state="visible", timeout=15000
        )
        composer = stage.page.get_by_label("Say anything, or ask a question", exact=False)
        composer.fill(prompt)
        stage.wait(1.0)
        stage.page.get_by_role("button", name="Send message").click()
    stage.page.get_by_text("I cannot reach the language model right now", exact=False).wait_for(
        timeout=90000
    )
    stage.page.get_by_text("I can only tell you what the fixed rules found", exact=False).wait_for(
        timeout=10000
    )
    stage.wait(12.0)


def scene_settings(stage: Stage) -> None:
    stage.primary("Settings")
    settings = stage.page.get_by_role("navigation", name="Settings sections")
    settings.get_by_role("button", name="Agent Behavior").click()
    stage.wait(5.0)
    settings.get_by_role("button", name="Model & RAG").click()
    stage.focus(stage.page.get_by_role("heading", name="The AI model"))
    stage.wait(10.0)


def scene_disclosure(stage: Stage) -> None:
    stage.primary("Dashboard")
    stage.dashboard_tab("Overview")
    stage.wait(5.0)
    stage.glide(520, 2.2)
    stage.wait(7.0)


SCENES = (
    Scene(1, "Why an agent, and not a better algorithm", "Vite dashboard and navigation", scene_opening),
    Scene(2, "Perceive, reason, act", "color-coded pipeline trace", scene_pipeline),
    Scene(3, "From a wrist to one number", "nightly reading and sleep window", scene_one_number),
    Scene(4, "What your own normal means", "personal baseline detail", scene_own_normal),
    Scene(6, "A month of nights", "overview and history timeline", scene_month),
    Scene(7, "Four quiet nights", "exercise, alcohol, and their recorded outcomes", scene_quiet_nights),
    Scene(8, "Something starts, and it still says nothing", "first raised night", scene_first_red),
    Scene(10, "The agent wakes", "recorded investigation and question", scene_agent_wakes),
    Scene(12, "It has to prove what it says", "archive and live API conversation", scene_grounding),
    Scene(13, "Two symptoms, two different nights", "recorded safety floor", scene_safety),
    Scene(14, "Everything it did, written down", "audit trail and archive", scene_audit),
    Scene(15, "Feeling better is not the same as being better", "recovery night in History", scene_recovery),
    Scene(16, "It comes back, and the person overrules the system", "human decision audit", scene_human_review),
    Scene(17, "Chest pain: five questions, then a rule the AI cannot argue with", "published rule explanation", scene_marburg),
    Scene(18, "Take the AI away", "chat response during an isolated offline-model capture", scene_ai_away),
    Scene(20, "What did not work", "Settings sections", scene_settings),
    Scene(23, "What this is not", "Dashboard safety copy scrolls with its content", scene_disclosure),
)


def record(scene: Scene, base_url: str, output_dir: Path) -> Path:
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(
            viewport={"width": WIDTH, "height": HEIGHT},
            record_video_dir=str(raw_dir),
            record_video_size={"width": WIDTH, "height": HEIGHT},
        )
        source = None
        video = None
        try:
            page = context.new_page()
            page.set_default_timeout(15000)
            page.set_default_navigation_timeout(45000)
            page.goto(base_url, wait_until="load", timeout=45000)
            page.get_by_role("heading", name="Health Overview").wait_for(timeout=60000)
            page.add_style_tag(content=f"html {{ zoom: {ZOOM}; }}")
            page.wait_for_timeout(1500)
            video = page.video
            scene.act(Stage(page))
            page.wait_for_timeout(1500)
        finally:
            context.close()
            source = Path(video.path()) if video else None
            browser.close()

    if source is None or not source.is_file():
        raise SystemExit(f"No Playwright video was written for chapter {scene.chapter}.")
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / f"{scene.chapter:02d}-{scene.slug}.mp4"
    result = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-vf",
            f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2:white,format=yuv420p",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-r",
            "30",
            "-an",
            str(destination),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise SystemExit(f"ffmpeg could not encode {source.name}:\n{result.stderr[-2000:]}")
    source.unlink(missing_ok=True)
    duration = probe_seconds(destination)
    print(f"    {destination.name}  {duration:.1f}s")
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__ or "")
    parser.add_argument("--only", type=int, action="append", help="chapter id, repeatable")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--base-url", default=FRONTEND, help="Vite frontend URL")
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT),
        help="destination for Vite footage and raw Playwright recordings",
    )
    parser.add_argument(
        "--offline-base-url",
        help="isolated Vite URL for chapter 18; its API must use a cloned demo DB, no scheduler, no notifier, and a closed localhost model endpoint",
    )
    args = parser.parse_args()

    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise SystemExit("ffmpeg and ffprobe must be on PATH")

    if args.list:
        for scene in SCENES:
            print(f"{scene.chapter:>3}  {scene.title:<58} {scene.note}")
        return 0

    chosen = [scene for scene in SCENES if not args.only or scene.chapter in args.only]
    if not chosen:
        raise SystemExit("No scenes matched.")
    if any(scene.chapter == 18 for scene in chosen) and not args.offline_base_url:
        raise SystemExit(
            "Chapter 18 requires --offline-base-url so the outage interaction cannot reach "
            "the regular application API."
        )

    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = REPO_ROOT / output_dir
    for index, scene in enumerate(chosen, start=1):
        print(f"\n[{index}/{len(chosen)}] chapter {scene.chapter}: {scene.note}")
        base_url = args.offline_base_url if scene.chapter == 18 else args.base_url
        record(scene, base_url or args.base_url, output_dir)
    print(f"\nVite footage in {output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
