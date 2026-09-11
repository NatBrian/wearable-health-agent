"""The phone's topic table must mirror TOPIC_STEPS, or the two surfaces drift.

Parses the ordinal lists out of HowItWorksTab.kt and compares them, in order,
to TOPIC_STEPS in src/wha/ui/components/how_it_works.py.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
KOTLIN = ROOT / "android/app/src/main/java/dev/wha/app/ui/record/HowItWorksTab.kt"


def test_kotlin_topics_match_python_topic_steps() -> None:
    from wha.ui.components.how_it_works import TOPIC_STEPS

    source = KOTLIN.read_text(encoding="utf-8")
    found = re.findall(r"Topic\((\d+),\s*listOf\(([^)]*)\)\)", source)
    assert len(found) == len(TOPIC_STEPS) == 10, f"expected 10 topics, found {len(found)}"
    numbers = sorted(int(n) for n, _ in found)
    assert numbers == list(range(1, 11))
    by_number = {
        int(n): tuple(int(x) for x in body.split(",") if x.strip()) for n, body in found
    }
    expected = [tuple(steps) for steps in TOPIC_STEPS.values()]
    actual = [by_number[n] for n in range(1, 11)]
    assert actual == expected, f"Kotlin topics differ from TOPIC_STEPS:\n{actual}\n{expected}"
