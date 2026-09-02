import sqlite3
from pathlib import Path

from wha.db import connect
from wha.db.migrations import apply_schema
from wha.models import BaselineRung, Subject


def list_subjects(
    db_path: Path | None = None,
    conn: sqlite3.Connection | None = None,
) -> list[Subject]:
    """Retrieve all configured subjects with their latest baseline maturity status.

    Handles empty database cleanly (returns []).
    """
    close_conn = False
    if conn is None:
        conn = connect(db_path) if db_path is not None else connect()
        apply_schema(conn)
        close_conn = True

    try:
        rows = conn.execute(
            "SELECT subject_id, label, source_kind, timezone FROM subjects ORDER BY CASE WHEN subject_id = 'me' THEN 0 ELSE 1 END, subject_id"
        ).fetchall()

        subjects: list[Subject] = []
        for r in rows:
            sub_id = r["subject_id"]
            # Look up baseline maturity
            base_row = conn.execute(
                "SELECT usable_nights, rung FROM baselines WHERE subject_id = ? ORDER BY night_date DESC LIMIT 1",
                (sub_id,),
            ).fetchone()

            if base_row is not None:
                usable = int(base_row["usable_nights"])
                rung = BaselineRung(base_row["rung"])
            else:
                count_row = conn.execute(
                    "SELECT COUNT(*) as count FROM nightly_features WHERE subject_id = ? AND usable = 1",
                    (sub_id,),
                ).fetchone()
                usable = int(count_row["count"]) if count_row else 0
                rung = BaselineRung.COLD

            subjects.append(
                Subject(
                    subject_id=sub_id,
                    label=r["label"],
                    source_kind=r["source_kind"],
                    timezone=r["timezone"],
                    usable_nights=usable,
                    rung=rung,
                )
            )

        return subjects
    finally:
        if close_conn:
            conn.close()
