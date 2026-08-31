"""Belief explanation service."""

from dataclasses import dataclass
from datetime import date
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

    # Parse date range
    if date_or_range and ":" in date_or_range:
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
