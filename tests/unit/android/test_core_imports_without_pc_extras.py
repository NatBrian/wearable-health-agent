"""The phone installs the core without the PC-only packages. Every core module must
import with those packages absent, or the app crashes on first use of that module.

Blocks the PC-only packages in sys.modules for the duration of one import sweep, in a
subprocess so nothing already imported in this test session hides a failure.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

PC_ONLY_PACKAGES = (
    "streamlit",
    "altair",
    "fastapi",
    "uvicorn",
    "sentence_transformers",
    "torch",
    "apscheduler",
    "playwright",
)

# Modules that legitimately need a PC-only package. Everything else under wha must load
# without them.
PC_ONLY_MODULES = (
    "wha.ui",
    "wha.api",
    "wha.cli",
    "wha.service.scheduler",
    "wha.service.demo",
    "wha.eval",
)

SWEEP = r'''
import importlib, pkgutil, sys, traceback
blocked = %r
pc_only = %r
class Blocker:
    def find_spec(self, name, path=None, target=None):
        root = name.split(".")[0]
        if root in blocked:
            raise ImportError(f"{name} is PC-only and must not be imported by the core")
        return None
sys.meta_path.insert(0, Blocker())
import wha
failures = []
for info in pkgutil.walk_packages(wha.__path__, "wha."):
    if info.name.startswith(pc_only):
        continue
    try:
        importlib.import_module(info.name)
    except Exception:
        failures.append(info.name + ": " + traceback.format_exc().splitlines()[-1])
print("\n".join(failures))
sys.exit(1 if failures else 0)
'''


def test_every_core_module_imports_with_pc_packages_blocked() -> None:
    code = SWEEP % (PC_ONLY_PACKAGES, PC_ONLY_MODULES)
    proc = subprocess.run(
        [sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True
    )
    assert proc.returncode == 0, "core modules that reach a PC-only package:\n" + proc.stdout


def test_pyproject_declares_the_pc_extra() -> None:
    import tomllib

    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    extras = pyproject["project"].get("optional-dependencies", {})
    assert "pc" in extras, "pyproject.toml has no [project.optional-dependencies] pc"
    names = {dep.split(">")[0].split("<")[0].split("=")[0].strip() for dep in extras["pc"]}
    for required in ("streamlit", "altair", "fastapi", "uvicorn", "sentence-transformers", "apscheduler"):
        assert required in names, f"{required} must be in the pc extra, not in core"
    core = {d.split(">")[0].split("<")[0].split("=")[0].strip() for d in pyproject["project"]["dependencies"]}
    assert not (core & names), f"declared in both core and pc: {core & names}"
