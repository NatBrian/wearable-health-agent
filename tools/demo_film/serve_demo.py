#!/usr/bin/env python
"""Open the finished demo timeline in the dashboard, exactly as the film shows it.

    uv run python tools/demo_film/serve_demo.py

Then run `npm run dev` in frontend/ and go to http://localhost:8443. Every night from 4
August to 23 September 2026 is there: the quiet nights, the illness, the relapse, the
three linked investigations, every question asked and answered, the escalation, and the
full audit trail behind all of it.

THREE THINGS THIS HANDLES that running `wha serve` by hand does not.

**The clock.** The last night in this database is 23 September 2026. Without shifting the
clock the dashboard believes today is whatever today actually is, so the newest night is
either in the future or months stale, and Today shows nothing. The offset is computed at
launch from the real date, so this keeps working however long from now you run it.

**A copy, not the original.** It serves a working copy, so browsing, chatting or answering
something cannot alter the committed timeline. Delete the copy and run this again to get
back to exactly the state the film was cut from.

**No scheduler.** Nothing ingests, nothing advances, nothing expires. The timeline stays
where the film left it.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE = REPO_ROOT / "data" / "demo_film.sqlite"
WORKING = REPO_ROOT / "data" / "demo_film_live.sqlite"
SUBJECT = "demo"
TZ = "Asia/Singapore"

# The last night the demo timeline contains. The dashboard is shown this as "today".
LAST_NIGHT = date(2026, 9, 25)


def main() -> int:
    if not SOURCE.is_file():
        raise SystemExit(
            f"{SOURCE} is missing. It is committed, so a fresh checkout has it; if you "
            "deleted it, rebuild with tools/demo_film/build.py."
        )

    if not WORKING.is_file():
        shutil.copyfile(SOURCE, WORKING)
        print(f"copied {SOURCE.name} to {WORKING.name}")
    else:
        print(f"using the existing {WORKING.name}; delete it to start from the film's state")

    today = datetime.now(UTC).astimezone(ZoneInfo(TZ)).date()
    offset = (LAST_NIGHT - today).days

    env = dict(os.environ)
    env["WHA_DB_PATH"] = str(WORKING)
    env["WHA_SUBJECT"] = SUBJECT
    env["WHA_TIMEZONE"] = TZ
    env["WHA_CLOCK_OFFSET_DAYS"] = str(offset)

    print(f"clock shifted {offset:+d} days, so the dashboard reads {LAST_NIGHT}")
    print("API on http://localhost:8500")
    print("dashboard: run `npm run dev` in frontend/, then open http://localhost:8443")
    print("ctrl-c to stop\n")

    return subprocess.call(
        ["uv", "run", "wha", "serve", "--no-scheduler", "--db", str(WORKING)],
        cwd=REPO_ROOT,
        env=env,
    )


if __name__ == "__main__":
    sys.exit(main())
