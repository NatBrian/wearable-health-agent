"""The API and the facade are two clients of one service layer. If one gains an
endpoint the other must too, or the phone and the dashboard drift apart."""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _service_calls(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id == "service":
                names.add(node.attr)
    return names


def test_facade_calls_every_service_function_the_api_calls() -> None:
    api = _service_calls(ROOT / "src/wha/api/app.py")
    facade = _service_calls(ROOT / "src/wha_android/facade.py")
    # The API can delete a subject and probe Telegram; the phone does neither, on purpose.
    phone_never = {"delete_all_subject_data", "test_telegram_connection", "list_subjects"}
    missing = api - facade - phone_never
    assert not missing, f"the API reaches these service functions and the facade does not: {sorted(missing)}"


def test_every_facade_function_is_guarded() -> None:
    source = (ROOT / "src/wha_android/facade.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    unguarded = [
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and not node.name.startswith("_")
        and not any(
            (isinstance(d, ast.Attribute) and d.attr == "guarded")
            or (isinstance(d, ast.Name) and d.id == "guarded")
            for d in node.decorator_list
        )
    ]
    assert not unguarded, f"facade functions that can raise across the boundary: {unguarded}"


def test_contract_lists_every_facade_function() -> None:
    contract = (ROOT / "docs/CONTRACTS.md").read_text(encoding="utf-8")
    tree = ast.parse((ROOT / "src/wha_android/facade.py").read_text(encoding="utf-8"))
    public = [n.name for n in tree.body if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")]
    missing = [name for name in public if not re.search(rf"`{name}\(", contract)]
    assert not missing, f"docs/CONTRACTS.md does not list: {missing}"
