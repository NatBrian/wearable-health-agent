"""Download the two public inputs the detection evaluation needs.

Neither file is committed. Both are public and neither needs registration. See
`experiments/detection/cohort/README.md` for what they are and why their date shifts match.

Sizes are asserted against the published Content-Length rather than trusted, because a
truncated 378 MB download produces a zip that opens and is missing participants, which
would quietly change every number downstream.
"""

from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEST = REPO / "data" / "cohort"

# Mishra et al. 2020, Nature Biomedical Engineering 4:1208-1220.
WEARABLES_URL = (
    "https://storage.googleapis.com/gbsc-gcp-project-ipop_public/COVID-19/COVID-19-Wearables.zip"
)
WEARABLES_BYTES = 378_380_920

# The same paper's Supplementary Data 1. Supplementary Table 3 holds the symptom dates.
LABELS_URL = (
    "https://static-content.springer.com/esm/art%3A10.1038%2Fs41551-020-00640-6/"
    "MediaObjects/41551_2020_640_MOESM3_ESM.xlsx"
)
LABELS_BYTES = 4_041_311

UA = {"User-Agent": "Mozilla/5.0 (compatible; wha-cohort-eval/1.0)"}


def download(url: str, path: Path, expect_bytes: int) -> None:
    if path.exists() and path.stat().st_size == expect_bytes:
        print(f"  already present, {expect_bytes:,} bytes: {path.name}")
        return
    print(f"  fetching {url}")
    req = urllib.request.Request(url, headers=UA)
    tmp = path.with_suffix(path.suffix + ".part")
    digest = hashlib.sha256()
    got = 0
    with urllib.request.urlopen(req, timeout=120) as response, tmp.open("wb") as out:
        while chunk := response.read(1 << 20):
            out.write(chunk)
            digest.update(chunk)
            got += len(chunk)
            if got % (32 << 20) < (1 << 20):
                print(f"    {got / 1e6:,.0f} MB", flush=True)
    if got != expect_bytes:
        tmp.unlink(missing_ok=True)
        raise SystemExit(
            f"{path.name}: expected {expect_bytes:,} bytes, got {got:,}. "
            "The publisher may have replaced the file. Do not use a partial download."
        )
    tmp.replace(path)
    print(f"  wrote {path} ({got:,} bytes, sha256 {digest.hexdigest()[:16]})")


def main() -> int:
    DEST.mkdir(parents=True, exist_ok=True)
    print("Mishra et al. 2020 wearable records:")
    download(WEARABLES_URL, DEST / "COVID-19-Wearables.zip", WEARABLES_BYTES)
    print("Supplementary Data 1 (symptom onset dates):")
    download(LABELS_URL, DEST / "supplementary-data-1.xlsx", LABELS_BYTES)
    print("\nNext: uv run python experiments/detection/cohort/labels.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
