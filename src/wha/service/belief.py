"""Belief explanation service."""

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from wha.belief import update_belief
from wha.config import get_settings
from wha.db import apply_schema, connect
from wha.detect.detector import detect_range
from wha.models import BeliefState, CauseId, Detection


@dataclass(frozen=True)
class BeliefNightRecord:
    night_date: date
    residual_bpm: float | None
    p_illness: float
    top_causes: list[tuple[CauseId, float]]
    belief: BeliefState


def explain_belief(
    subject_id: str | None = None,
    date_or_range: str | None = None,
    episode_id: str | None = None,
    db_path: Path | None = None,
) -> list[BeliefNightRecord]:
    """Compute and explain evolving causal belief over a range of nights."""
    settings = get_settings()
    subj = subject_id if subject_id is not None else settings.subject
    target_db = db_path if db_path is not None else settings.db_path

    target_db.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(target_db)
    apply_schema(conn)

    start_d: date
    end_d: date

    if episode_id:
        if episode_id.lower() == "latest":
            if subject_id:
                ep_row = conn.execute(
                    """SELECT episode_id, subject_id, opened_on, closed_on
                       FROM episodes WHERE subject_id = ? ORDER BY opened_on DESC LIMIT 1""",
                    (subj,),
                ).fetchone()
            else:
                ep_row = conn.execute(
                    """SELECT episode_id, subject_id, opened_on, closed_on
                       FROM episodes ORDER BY opened_on DESC LIMIT 1"""
                ).fetchone()
        else:
            ep_row = conn.execute(
                """SELECT episode_id, subject_id, opened_on, closed_on
                   FROM episodes WHERE episode_id = ?""",
                (episode_id,),
            ).fetchone()

        if ep_row is not None:
            subj = ep_row["subject_id"]
            start_d = date.fromisoformat(ep_row["opened_on"])
            end_d = (
                date.fromisoformat(ep_row["closed_on"])
                if ep_row["closed_on"]
                else start_d + timedelta(days=7)
            )
        else:
            start_d = date(2026, 8, 25)
            end_d = date(2026, 9, 1)
    elif date_or_range and ":" in date_or_range:
        s_str, e_str = date_or_range.split(":", 1)
        start_d, end_d = date.fromisoformat(s_str.strip()), date.fromisoformat(e_str.strip())
    elif date_or_range:
        start_d = date.fromisoformat(date_or_range.strip())
        end_d = start_d
    else:
        # Default: read all existing detections for subject
        rows = conn.execute(
            "SELECT MIN(night_date), MAX(night_date) FROM detections WHERE subject_id = ?",
            (subj,),
        ).fetchone()
        if rows and rows[0] and rows[1]:
            start_d = date.fromisoformat(rows[0])
            end_d = date.fromisoformat(rows[1])
        else:
            start_d = date(2026, 8, 25)
            end_d = date(2026, 9, 1)

    # Fetch detections in range
    detections = detect_range(conn, subj, start_d, end_d)
    conn.close()

    history_dets: list[Detection] = []
    records: list[BeliefNightRecord] = []

    for det in detections:
        history_dets.append(det)
        current_belief = update_belief(history_dets)
        records.append(
            BeliefNightRecord(
                night_date=det.night_date,
                residual_bpm=det.residual_bpm,
                p_illness=current_belief.p_illness,
                top_causes=current_belief.top(3),
                belief=current_belief,
            )
        )

    return records


def get_knowledge_provenance() -> dict[str, dict[str, str]]:
    """Where each cause's numbers came from, so the dashboard can say which are guesses.

    The project's own rule is that an unevidenced choice is stated in the documents AND on
    the dashboard. It was in neither for most of these, because the documents described
    them as human judgement and they are not.

    About 140 numbers here have no source: 45 of the 57 temporal profile weights, most of
    the between-person spreads, and all 64 answer likelihoods. On screen they looked
    exactly like the ones measured on tens of thousands of people.

    Served rather than read directly by the interface, because a screen may not import
    below the API.
    """
    import yaml

    out: dict[str, dict[str, str]] = {}

    causes_raw = yaml.safe_load(Path("data/knowledge/causes.yaml").read_text(encoding="utf-8"))
    for row in causes_raw.get("causes", []):
        cause_id = str(row.get("cause"))
        # A row is only as sourced as its weakest load-bearing number. `profile_source` is
        # what tells the causes apart across nights, and 45 of 57 weights have none.
        has_profile_source = bool(str(row.get("profile_source", "")).strip())
        # A DERIVED row whose derivation contains "NO EVIDENCE FOUND" has at least one
        # number nobody measured, and the screen must not call that "from a study". Every
        # remaining CITED row in causes.yaml was relabelled DERIVED on 5 September 2026
        # after an audit found all three were CITED for numbers their own papers do not
        # contain, so without this the whole table would have gone on reading as sourced.
        backing = str(row.get("derivation") or row.get("assumption") or "")
        holds_an_unevidenced_number = "NO EVIDENCE FOUND" in backing.upper()
        out[cause_id] = {
            "provenance": str(row.get("provenance", "unstated")),
            "profile_sourced": "yes" if has_profile_source else "no",
            "has_unevidenced_number": "yes" if holds_an_unevidenced_number else "no",
            "note": (
                str(row.get("assumption") or row.get("derivation") or row.get("citation") or "")
                .strip()
                .replace("\n", " ")[:400]
            ),
        }

    probes_raw = yaml.safe_load(Path("data/knowledge/probes.yaml").read_text(encoding="utf-8"))
    for row in probes_raw.get("probes", []):
        out[f"probe:{row.get('probe_id')}"] = {
            "provenance": str(row.get("provenance", "unstated")),
            "profile_sourced": "n/a",
            "note": str(row.get("assumption") or row.get("citation") or "")
            .strip()
            .replace("\n", " ")[:400],
        }

    return out


def get_knowledge_provenance_summary() -> dict[str, int]:
    """Count provenance entries with at least one assumed or unsourced figure."""
    entries = get_knowledge_provenance()
    unevidenced_entries = sum(
        1
        for entry in entries.values()
        if entry.get("provenance", "").upper() == "ASSUMED"
        or entry.get("has_unevidenced_number", "").lower() == "yes"
    )
    return {"unevidenced_entries": unevidenced_entries, "total_entries": len(entries)}


def get_safety_rule_provenance() -> list[dict[str, str | int | None]]:
    """Every published or assumed safety-rule number and its source.

    The standing rule requires an unevidenced clinical figure to be labelled in the docs
    AND on the dashboard. These rows cover assumed red-flag thresholds, cited triage rule
    scope and source, and cited overnight oxygen limits. Assumed values are shown with the
    basis recorded in their source table.
    """
    from wha.safety.rules import load_red_flags
    from wha.safety.triage import load_oxygen_rule, load_triage_rules

    config = load_red_flags()
    rows: list[dict[str, str | int | None]] = []

    triage = load_triage_rules()
    for rule in triage.rules:
        age = rule.minimum_age_years
        rows.append(
            {
                "rule": rule.id,
                "number": (
                    f"applies to {rule.applies_to}; minimum age {age}"
                    if age is not None
                    else f"applies to {rule.applies_to}"
                ),
                "provenance": "CITED",
                "basis": rule.citation.strip(),
                "minimum_age_years": age,
            }
        )

    for rule in config.tier_b:
        rows.append(
            {
                "rule": rule.id,
                "number": f"persists beyond {rule.persist_nights} nights",
                "provenance": rule.provenance or "UNLABELLED",
                "basis": (rule.assumption or rule.derivation or rule.source or "").strip(),
            }
        )

    for rule in config.vitals:
        bound = (
            f"robust z above {rule.robust_z_above}"
            if rule.robust_z_above is not None
            else f"robust z below {rule.robust_z_below}"
        )
        rows.append(
            {
                "rule": rule.id,
                "number": bound,
                "provenance": rule.provenance or "UNLABELLED",
                "basis": (rule.derivation or rule.assumption or rule.source or "").strip(),
            }
        )
        cold = rule.cold_rung_fallback_bpm_above or rule.cold_rung_fallback_bpm_below
        if cold is not None:
            rows.append(
                {
                    "rule": rule.id,
                    "number": f"{cold:.0f} bpm before your own range exists",
                    "provenance": rule.provenance_cold_rung or "UNLABELLED",
                    "basis": (rule.assumption_cold_rung or "").strip(),
                }
            )

    oxygen = load_oxygen_rule()
    if oxygen is not None:
        rows.append(
            {
                "rule": "oxygen_threshold",
                "number": f"only after {oxygen.min_overnight_readings} overnight readings",
                "provenance": "CITED",
                "basis": oxygen.citation.strip(),
            }
        )
        rows.extend(
            {
                "rule": "oxygen_threshold",
                "number": f"{band.max_percent:g} percent or less: {band.urgency}",
                "provenance": "CITED",
                "basis": f"{band.meaning.strip()} {oxygen.citation_plain.strip()}",
            }
            for band in oxygen.bands
        )
        rows.append(
            {
                "rule": "oxygen_threshold",
                "number": "above every threshold does not mean all clear",
                "provenance": "CITED",
                "basis": oxygen.never_reassure.strip(),
            }
        )

    return rows
