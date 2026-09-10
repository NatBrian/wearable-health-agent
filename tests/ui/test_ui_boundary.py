"""The dashboard must be replaceable, which means it may not reach past the API."""

import ast
from pathlib import Path

# What a screen is allowed to import from the application.
#
# wha.models is the shared vocabulary: the same Pydantic types the API serialises, so a
# screen gets a typed object rather than a bare dict and a renamed field cannot pass
# silently through JSON. Everything else must arrive over HTTP.
ALLOWED_PREFIXES = (
    "wha.api",
    "wha.models",
    "wha.ui",
    "wha.wording",
)

UI_ROOT = Path("src/wha/ui")


def _ui_modules() -> list[Path]:
    return sorted(p for p in UI_ROOT.rglob("*.py") if "__pycache__" not in str(p))


def test_no_screen_reaches_past_the_api() -> None:
    """A React app could not call wha.service, wha.constants or wha.clock.

    Leaving those imports in place would mean the dashboard worked and any replacement for
    it did not, which is the opposite of a boundary. The data path was already clean, with
    no SQL in any view; this makes the boundary one that something other than Python can
    cross.
    """
    offenders: list[str] = []
    for path in _ui_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            module = None
            if isinstance(node, ast.ImportFrom) and node.module:
                module = node.module
            elif isinstance(node, ast.Import):
                module = node.names[0].name
            if module and module.startswith("wha") and not module.startswith(ALLOWED_PREFIXES):
                offenders.append(f"{path.relative_to(UI_ROOT)}: {module}")

    assert not offenders, "screens reaching past the API: " + "; ".join(offenders)


def test_no_screen_opens_a_database_or_writes_sql() -> None:
    """The oldest version of this rule, kept because it is the one that matters most."""
    banned = ("sqlite3", "apply_schema", "SELECT ", "INSERT INTO", "UPDATE ")
    offenders: list[str] = []
    for path in _ui_modules():
        text = path.read_text(encoding="utf-8")
        offenders += [f"{path.name}: {token}" for token in banned if token in text]

    assert not offenders, "data access in a screen: " + "; ".join(offenders)


def test_the_client_covers_everything_the_screens_call() -> None:
    """A screen calling a client method that does not exist fails only when rendered.

    Streamlit swallows nothing, but a page nobody opened during a test run would still ship
    broken, which is how a guaranteed KeyError once sat in the History page while the whole
    suite passed.
    """
    from wha.api.client import ApiClient

    called: set[str] = set()
    for path in _ui_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Call)
                and isinstance(node.func.value.func, ast.Name)
                and node.func.value.func.id == "api"
            ):
                called.add(node.func.attr)

    missing = sorted(name for name in called if not hasattr(ApiClient, name))
    assert not missing, f"screens call client methods that do not exist: {missing}"
    assert called, "no screen calls the API at all, which cannot be right"
