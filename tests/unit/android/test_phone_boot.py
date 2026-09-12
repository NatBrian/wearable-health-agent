"""The phone boots with only its own packages installed.

Anything reachable from the boot entry that needs a PC-only package crashes the
app on first use. That is run 1 finding 2: wha.service.evaluation imported
wha.eval.detection at module top, which needs scipy, which the phone never
installs. The older import sweep missed it because scipy was not on its blocked
list and the dev machine has scipy anyway.

This simulates the phone instead: block every third-party import except what
android/app/requirements-android.txt installs, then run the real boot entry and
the two onboarding checks.
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

SWEEP = r"""
import json, os, sys
sys.path.insert(0, "android/app/src/main/python")
from importlib.metadata import distribution, PackageNotFoundError

dists = []
for line in open("android/app/requirements-android.txt", encoding="utf-8"):
    line = line.strip()
    if not line or line.startswith("#"):
        continue
    dists.append(line.split("==")[0].split(">")[0].split("<")[0].strip())

allowed = set(sys.stdlib_module_names) | {"wha", "wha_android", "wha_boot"}


def top_levels(dist):
    try:
        meta = distribution(dist)
    except PackageNotFoundError:
        return [dist.lower().replace("-", "_")]
    names = set(((meta.read_text("top_level.txt") or "").split()))
    for f in meta.files or []:
        # RECORD paths are relative to site-packages: the first component names
        # the importable top level (top_level.txt is absent in modern packages).
        p = str(f).replace("\\", "/")
        if p.startswith(".") or "/.dist-info/" in p:
            continue
        first = p.split("/")[0]
        if first == "__pycache__":
            continue
        if first.endswith(".py"):
            first = first[:-3]
        if first.isidentifier():
            names.add(first)
    return names or [dist.lower().replace("-", "_")]


for dist in dists:
    allowed.update(top_levels(dist))

import importlib.abc


class Blocker(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] not in allowed:
            # ModuleNotFoundError, not ImportError: optional-dependency fallbacks
            # (try httpx2, except ModuleNotFoundError: use httpx) must behave on
            # the simulator exactly as on the phone.
            raise ModuleNotFoundError(f"{name} is not installed on the phone")
        return None


sys.meta_path.insert(0, Blocker())

from wha_boot import boot

facade = boot(lambda payload: True, object())
bridge = json.loads(facade.diagnose("bridge", "{}"))
llm = json.loads(facade.diagnose("llm", "{}"))
assert "error" not in bridge, bridge
assert "error" not in llm, llm
assert llm.get("ok") is True, llm
print("phone boot ok")
"""


def test_phone_boot_needs_only_phone_packages() -> None:
    env = dict(
        os.environ,
        WHA_LLM_PROVIDER="cassette",
        WHA_BRIDGE_URL="http://127.0.0.1:9",
    )
    proc = subprocess.run(
        [sys.executable, "-c", SWEEP],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
        timeout=300,
    )
    assert proc.returncode == 0, (
        "phone boot failed with only phone packages present:\n" + proc.stderr[-3000:]
    )
    assert "phone boot ok" in proc.stdout
