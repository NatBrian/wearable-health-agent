"""The Record tab's frame cannot drift from the canonical step list.

Regenerate with `uv run python tools/android_canonical_steps.py` after any change
to CANONICAL_PIPELINE_STEPS; this test fails until the committed file is
regenerated, which is the point.
"""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TARGET = ROOT / "android/app/src/main/java/dev/wha/app/core/CanonicalSteps.kt"


def test_generated_canonical_steps_are_current(tmp_path: Path) -> None:
    before = TARGET.read_text(encoding="utf-8")
    subprocess.run(
        ["uv", "run", "python", "tools/android_canonical_steps.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    assert TARGET.read_text(encoding="utf-8") == before, (
        "CanonicalSteps.kt is stale: re-run tools/android_canonical_steps.py and commit the result"
    )
