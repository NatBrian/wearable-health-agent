"""Which parts of this system are allowed to know about which other parts.

Written 8 September 2026, before the repository was handed to people working on it in
parallel. `docs/CODE-CONVENTIONS.md` had a "Module boundaries" section that opened with
"These are enforced by a lint rule, not by good intentions", and all three of its rules were
false: it said the dashboard may import only from `service/`, when a test forbids exactly
that; it said `db/` is the only module that imports `sqlite3`, when 22 files outside `db/`
do; and there was no lint rule. `ruff.toml` sets a line length and two per-file ignores.

That is worse than having no rule at all. An agent handed this repository reads the
convention and does the opposite of what the suite requires.

So the boundary is a test, and the convention document now describes what this file checks.
The shape is borrowed from `tests/ui/test_ui_boundary.py`, which is the one boundary in the
repository that was already real.

**What this is for.** Four workstreams are about to run at once: replacing the dashboard,
restructuring the agent, reshaping retrieval, changing how investigations open. The risk is
not that someone writes a bad import. It is that two subsystems quietly grow a dependency
nobody decided on, and the coupling is only discovered when the two teams try to merge. A
new edge between packages is a design decision, so it fails here and has to be written down.

**This does not forbid the cycles that exist.** It names them, with their reasons, and fails
on the eighth.
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
# everything depends on them. `ui` is at the far end and reaches the application only
# through `api`, over HTTP.
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
    "ui": {"api", "models"},
}

# The two places where something low reaches back up into `service`, each with the reason it
# is allowed and the file it is allowed in. Both are held open by function-local imports,
# which is the convention's own definition of a deliberate break rather than a tangle.
#
# Neither is a good thing. They are the honest state of the code, written down so that they
# are a known list of seven rather than an invisible property. If you are the person who
# removes one, delete its entry and this test will hold you to it.
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


def test_the_dashboard_reaches_the_application_only_through_the_api() -> None:
    """Stated here as well as in tests/ui/test_ui_boundary.py, because it is the boundary
    that decides whether the dashboard can be replaced at all, and the convention document
    got it backwards for long enough to matter.
    """
    edges, _ = _import_graph()
    assert edges["ui"] <= {"api", "models"}, (
        f"a screen reaches past the API into {sorted(edges['ui'] - {'api', 'models'})}. "
        "Screens are an HTTP client, so that a React app could do the same job."
    )


def test_nothing_in_the_application_imports_the_dashboard() -> None:
    """The arrow points one way. A service that imports a screen cannot be run headless."""
    edges, _ = _import_graph()
    offenders = sorted(importer for importer, imported in edges.items() if "ui" in imported)
    assert not offenders, f"these import the dashboard: {offenders}"


def test_the_only_cycles_are_the_ones_written_down() -> None:
    """Two pairs, seven imports. The eighth fails here.

    A cycle usually means a boundary is in the wrong place, and both of these do. They are
    not being fixed today, because breaking them moves code that four people are about to
    work on. They are named instead, which is the difference between debt and a surprise.
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
        "A cycle means two parts of the system each need the other, which is almost always "
        "a boundary in the wrong place. Move the shared thing down rather than importing "
        "upwards."
    )


def test_every_upward_import_is_declared_and_function_local() -> None:
    """The rule that keeps the two cycles from spreading.

    A module-level import upwards would be a hard dependency and would deadlock the import
    order. A function-local one is a deliberate break, and `docs/CODE-CONVENTIONS.md` allows
    it only for that reason. Checking the position rather than trusting the convention is
    the point of this file existing.
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
    """An exemption for a file that no longer reaches upwards is an exemption nobody reads.

    The safety allowlist in tests/unit/safety/test_symptom_persistence.py went stale exactly
    this way when the file it named was split, so the same check is applied here.
    """
    _, sites = _import_graph()
    reaching = {s[2] for s in sites if s[1] == "service" and s[0] in {"agent", "notify"}}
    stale = sorted(set(ALLOWED_UPWARD_IMPORTS) - reaching)
    assert not stale, (
        f"these no longer import wha.service, so remove them from "
        f"ALLOWED_UPWARD_IMPORTS: {stale}"
    )
