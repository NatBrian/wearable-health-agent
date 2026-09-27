"""Enforces the module boundaries described in `docs/CODE-CONVENTIONS.md`.

The risk this guards against is not a single bad import. It is two subsystems gradually
growing a dependency nobody decided on, which is discovered only when concurrent work on
both is merged. A new edge between packages is a design decision, so it fails here until it
is declared.

The two existing import cycles are not forbidden. They are declared with their call sites,
and a new one fails.

Shape borrowed from `tests/ui/test_ui_boundary.py`.
"""

import ast
import collections
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "wha"


def _unit(relative: str) -> str:
    """The package a file belongs to, or the module name for a top-level file."""
    parts = relative.split("/")
    return parts[0] if len(parts) > 1 else parts[0][:-3]


def _import_graph() -> tuple[dict[str, set[str]], list[tuple[str, str, str, int, bool]]]:
    """Every cross-package import in `src/wha`, and where each one is written.

    The boolean is whether the import sits inside a function. That distinction is the whole
    of the cycle rule: an import that runs at module load is a hard dependency, and one
    inside a function is a deliberate, documented break.
    """
    edges: dict[str, set[str]] = collections.defaultdict(set)
    sites: list[tuple[str, str, str, int, bool]] = []

    for path in sorted(SRC.rglob("*.py")):
        if "__pycache__" in str(path):
            continue
        relative = path.relative_to(SRC).as_posix()
        importer = _unit(relative)
        tree = ast.parse(path.read_text(encoding="utf-8"))

        nested: set[tuple[int, int]] = set()
        for func in ast.walk(tree):
            if isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for node in ast.walk(func):
                    if isinstance(node, (ast.Import, ast.ImportFrom)):
                        nested.add((node.lineno, node.col_offset))

        for node in ast.walk(tree):
            module = None
            if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                module = node.module
            elif isinstance(node, ast.Import):
                module = node.names[0].name
            if not module or not module.startswith("wha."):
                continue
            imported = module[4:].split(".")[0]
            if imported == importer:
                continue
            edges[importer].add(imported)
            sites.append(
                (
                    importer,
                    imported,
                    relative,
                    node.lineno,
                    (node.lineno, node.col_offset) in nested,
                )
            )

    return dict(edges), sites


# Every dependency between two parts of this system that exists today, and therefore every
# one that somebody once decided on. Adding a pair here is not a formality: it is the moment
# to ask whether the thing you are about to couple should be coupled.
#
# Read it downwards. `config`, `constants`, `errors` and `models` depend on nothing and
# everything depends on them. The dashboard that used to sit at the far end of this graph,
# reaching the application only through `api` over HTTP, was `ui`; it was archived to
# archive/streamlit-ui-2026-09-27/ on 27 September 2026, and the frontend that replaced it
# lives in frontend/ as a separate, non-Python project this graph does not cover.
DECLARED_EDGES: dict[str, set[str]] = {
    "agent": {
        "audit",
        "belief",
        "clock",
        "config",
        "constants",
        "db",
        "errors",
        "llm",
        "models",
        "notify",
        "policy",
        "retrieve",
        "safety",
        "service",
    },
    "api": {"clock", "config", "models"},
    "audit": {"clock", "constants", "db", "models"},
    "belief": {"constants", "errors", "models"},
    "cli": {"api", "service"},
    "clock": {"config"},
    "db": {"config", "errors", "models"},
    "detect": {"audit", "constants", "db", "features", "models"},
    "eval": {
        "belief",
        "clock",
        "constants",
        "detect",
        "errors",
        "ingest",
        "models",
        "policy",
        "safety",
    },
    "features": {"clock", "constants", "db", "models"},
    "ingest": {"clock", "config", "db", "errors", "models"},
    "llm": {"config", "constants", "errors"},
    "notify": {"config", "constants", "models", "safety", "service"},
    "policy": {"belief", "constants", "errors", "models"},
    "retrieve": {"belief", "clock", "constants"},
    "safety": {"constants", "db", "errors", "llm", "models", "policy", "retrieve"},
    "scheduler": {"service"},
    "service": {
        "agent",
        "audit",
        "belief",
        "clock",
        "config",
        "constants",
        "db",
        "detect",
        "errors",
        "eval",
        "features",
        "ingest",
        "llm",
        "models",
        "notify",
        "policy",
        "retrieve",
        "safety",
    },
}

# The files that import `service` from below it, each with the reason. All are function-local
# imports, which `docs/CODE-CONVENTIONS.md` permits only to break a cycle.
#
# Both cycles mark a boundary in the wrong place and are candidates for removal. Declaring
# them here keeps the set bounded. When one is removed, delete its entry: a stale entry fails
# the last test in this file.
ALLOWED_UPWARD_IMPORTS: dict[str, str] = {
    # The conversation can open an investigation, read a person's profile, and record a
    # symptom. Those are application concerns, and the agent reaches up for them rather
    # than the service reaching in and driving the graph from outside.
    "agent/conversation.py": "opens episodes, reads the profile, records symptoms",
    # node_ask records what the person said against the symptom timeline before it parks.
    "agent/nodes/ask.py": "records an answer's symptoms before the graph interrupts",
    # node_decide needs the outstanding symptoms to decide whether to ask anything.
    "agent/nodes/decide.py": "reads outstanding symptoms when scoring a question",
    # node_preload loads the symptom history the deterministic floor is judged against.
    "agent/nodes/preload.py": "loads the symptom history for the safety floor",
    # An inbound Telegram message has to reach the conversation, and the transport cannot
    # own the conversation without the two swapping places.
    "notify/receiver.py": "hands an inbound message to the conversation",
}


def test_the_dependency_graph_is_the_one_that_was_decided_on() -> None:
    """A new edge between two packages is a design decision, not an import.

    If this fails you have coupled two parts of the system that were not coupled before.
    That may be right. Add the pair to DECLARED_EDGES with the change that needed it, and
    say so in the pull request, because somebody else is probably working in one of them.
    """
    edges, _ = _import_graph()

    added = {
        importer: sorted(imported - DECLARED_EDGES.get(importer, set()))
        for importer, imported in edges.items()
        if imported - DECLARED_EDGES.get(importer, set())
    }
    removed = {
        importer: sorted(imported - edges.get(importer, set()))
        for importer, imported in DECLARED_EDGES.items()
        if imported - edges.get(importer, set())
    }

    assert not added, f"new dependencies between packages, undeclared: {added}"
    assert not removed, (
        "these declared dependencies no longer exist, which is good news: "
        f"delete them from DECLARED_EDGES: {removed}"
    )


def test_nothing_in_the_application_imports_the_dashboard() -> None:
    """The arrow points one way. A service that imports a screen cannot be run headless."""
    edges, _ = _import_graph()
    offenders = sorted(importer for importer, imported in edges.items() if "ui" in imported)
    assert not offenders, f"these import the dashboard: {offenders}"


def test_the_only_cycles_are_the_ones_written_down() -> None:
    """Two known pairs. A third fails here.

    Removing either means moving `symptoms`, `settings` and `episode_lifecycle` into a lower
    layer. Until then they are declared rather than undocumented.
    """
    edges, _ = _import_graph()
    found = {
        tuple(sorted((importer, imported)))
        for importer, targets in edges.items()
        for imported in targets
        if importer in edges.get(imported, set())
    }
    expected = {("agent", "service"), ("notify", "service")}

    assert found == expected, (
        f"unexpected import cycles: {sorted(found - expected)}. "
        "A cycle means two packages each depend on the other, which usually indicates a "
        "boundary in the wrong place. Move the shared code down rather than importing "
        "upwards."
    )


def test_every_upward_import_is_declared_and_function_local() -> None:
    """Keeps the two cycles from spreading.

    A module-level upward import is a hard dependency and would break the import order. A
    function-local one is a deliberate cycle break, which is the only form
    `docs/CODE-CONVENTIONS.md` permits.
    """
    _, sites = _import_graph()
    upward = [s for s in sites if s[1] == "service" and s[0] in {"agent", "notify"}]

    assert upward, "found no upward imports at all, which means this check is not working"

    undeclared = sorted({s[2] for s in upward if s[2] not in ALLOWED_UPWARD_IMPORTS})
    assert not undeclared, (
        f"these reach up into wha.service without being declared: {undeclared}. "
        "Add the file to ALLOWED_UPWARD_IMPORTS with the reason, or move what it needs "
        "down out of the service layer."
    )

    at_module_level = sorted(f"{s[2]}:{s[3]}" for s in upward if not s[4])
    assert not at_module_level, (
        f"these import wha.service at module level: {at_module_level}. "
        "An upward import must sit inside the function that needs it, so that it breaks a "
        "cycle rather than creating one."
    )


def test_no_allowed_upward_import_is_stale() -> None:
    """An entry for a file that no longer imports upwards is misleading and should go.

    The allowlist in tests/unit/safety/test_symptom_persistence.py went stale this way when
    the file it named was split, so the same check applies here.
    """
    _, sites = _import_graph()
    reaching = {s[2] for s in sites if s[1] == "service" and s[0] in {"agent", "notify"}}
    stale = sorted(set(ALLOWED_UPWARD_IMPORTS) - reaching)
    assert not stale, (
        f"these no longer import wha.service, so remove them from "
        f"ALLOWED_UPWARD_IMPORTS: {stale}"
    )
