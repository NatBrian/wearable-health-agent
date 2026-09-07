"""The deterministic half writes down what it did, in words a person can read.

Audit events came only from the agent's tool calls and from settings changes, so after a
full night of measuring, scoring and judging, the page that exists to show a person what
happened to their data was blank. There was no way to tell that from the system having done
nothing at all.
"""

from datetime import date
from pathlib import Path

from wha.audit.monitor import night_narrative, record_ingest, record_night_scored
from wha.db import connect
from wha.db.migrations import apply_schema
from wha.detect.baseline import compute_baseline
from wha.models import (
    Baseline,
    Detection,
    DetectionLevel,
    Forecast,
    ForecastStatus,
    NightlyFeatures,
)
from wha.service.audit import list_plain_records, verify_hash_chain


def _db(tmp_path: Path) -> Path:
    db_file = tmp_path / "audit.db"
    conn = connect(db_file)
    apply_schema(conn)
    conn.execute(
        """INSERT INTO subjects (subject_id, label, source_kind, timezone, created_at_utc)
           VALUES ('me', 'me', 'live', 'Asia/Singapore', '2026-09-01T00:00:00Z')"""
    )
    conn.commit()
    conn.close()
    return db_file


def _features(
    rhr: float | None = 45.0, usable: bool = True, source: str = "sleep"
) -> NightlyFeatures:
    return NightlyFeatures(
        subject_id="me",
        night_date=date(2026, 9, 3),
        rhr_bpm=rhr,
        coverage_minutes=398 if usable else 20,
        usable=usable,
        rhr_window_source=source,
    )


def _detection(level: DetectionLevel, residual: float | None, flagged: bool = False) -> Detection:
    return Detection(
        subject_id="me",
        night_date=date(2026, 9, 3),
        level=level,
        flagged=flagged,
        deviation_bpm=residual,
        explained_bpm=0.0,
        residual_bpm=residual,
        robust_z=0.0,
        forecast=Forecast(status=ForecastStatus.NOT_RUN),
        reasons=[],
    )


def _baseline(nights: int) -> Baseline:
    return compute_baseline(
        [
            NightlyFeatures(
                subject_id="me",
                night_date=date(2026, 8, 1),
                rhr_bpm=45.0,
                coverage_minutes=400,
                usable=True,
            )
        ]
        * nights
    )


def test_a_scored_night_is_recorded_the_first_time(tmp_path: Path) -> None:
    """The regression: a full night processed and the record stayed empty."""
    db_file = _db(tmp_path)
    conn = connect(db_file)
    record_night_scored(
        conn, _features(), _baseline(3), _detection(DetectionLevel.GREEN, -10.4), None
    )
    conn.close()

    records = list_plain_records("me", conn=connect(db_file))
    assert len(records) == 1
    assert records[0]["night"] == "2026-09-03"
    assert records[0]["sentences"], "an entry with no readable sentences is not a record"


def test_rescoring_with_no_change_writes_nothing(tmp_path: Path) -> None:
    """Night scoring runs every few hours; identical passes must not fill the record."""
    db_file = _db(tmp_path)
    conn = connect(db_file)
    features, baseline = _features(), _baseline(3)
    detection = _detection(DetectionLevel.GREEN, -10.4)

    record_night_scored(conn, features, baseline, detection, None)
    previous = {"level": "GREEN", "flagged": 0, "residual_bpm": -10.4}
    record_night_scored(conn, features, baseline, detection, previous)
    conn.close()

    assert len(list_plain_records("me", conn=connect(db_file))) == 1


def test_a_changed_result_is_recorded_and_says_what_changed(tmp_path: Path) -> None:
    """A night settles when its sleep syncs, and that change is worth knowing about."""
    db_file = _db(tmp_path)
    conn = connect(db_file)
    features, baseline = _features(), _baseline(10)

    record_night_scored(conn, features, baseline, _detection(DetectionLevel.GREEN, -10.4), None)
    previous = {"level": "GREEN", "flagged": 0, "residual_bpm": -10.4}
    record_night_scored(
        conn, features, baseline, _detection(DetectionLevel.RED, 4.5, flagged=True), previous
    )
    conn.close()

    records = list_plain_records("me", conn=connect(db_file))
    assert len(records) == 2
    newest = " ".join(records[0]["sentences"])
    assert "Re-scored" in newest
    assert "level" in newest


def test_an_ingest_that_brings_nothing_writes_nothing(tmp_path: Path) -> None:
    """Ingest polls every 30 minutes and mostly finds nothing new."""
    db_file = _db(tmp_path)
    conn = connect(db_file)
    record_ingest(conn, "me", 0, "your watch")
    conn.close()
    assert list_plain_records("me", conn=connect(db_file)) == []


def test_an_ingest_that_brings_data_is_recorded(tmp_path: Path) -> None:
    db_file = _db(tmp_path)
    conn = connect(db_file)
    record_ingest(conn, "me", 660, "your watch")
    conn.close()

    records = list_plain_records("me", conn=connect(db_file))
    assert len(records) == 1
    assert "660" in " ".join(records[0]["sentences"])


# -- the words themselves ------------------------------------------------------------


def test_the_narrative_explains_why_nothing_could_be_flagged() -> None:
    """The silence that prompted this: the deterministic half did work and said nothing.

    CORRECTED 5 September 2026. This also asserted "forecasting model did not run" and
    "5 usable nights", which were the Chronos explanation. Chronos is gone, measured
    rather than argued: over 7,295 nights it separated illness worse than the residual the
    detector already computes, AUC 0.586 against 0.629. A narrative explaining why a model
    that no longer exists declined to run is noise on a page whose purpose is to say what
    happened.

    What the narrative must still do is explain the OTHER refusal, which is real: below
    seven of the person's own nights the centre is still mostly a population guess, so
    nothing can be flagged. That is a decision made about them and it is still recorded.
    """
    lines = " ".join(
        night_narrative(
            _features(), _baseline(3), _detection(DetectionLevel.GREEN, -10.4), "First."
        )
    )
    assert "Nothing can be flagged yet" in lines
    assert "7 nights" in lines
    assert "forecast" not in lines.lower(), "a model that was removed does not get a line"


def test_the_narrative_says_which_window_was_used() -> None:
    on_sleep = " ".join(
        night_narrative(
            _features(source="sleep"), _baseline(9), _detection(DetectionLevel.GREEN, -1.0), "x"
        )
    )
    on_clock = " ".join(
        night_narrative(
            _features(source="clock"), _baseline(9), _detection(DetectionLevel.GREEN, -1.0), "x"
        )
    )
    assert "measured over that sleep" in on_sleep
    assert "recorded no sleep" in on_clock


def test_a_night_below_usual_is_not_described_with_a_signed_number() -> None:
    """A negative residual reads as a fault to someone simply below their usual."""
    lines = " ".join(
        night_narrative(_features(), _baseline(9), _detection(DetectionLevel.GREEN, -10.4), "x")
    )
    assert "below your usual, not above it" in lines
    assert "-10.4 unexplained" not in lines


def test_an_unusable_night_says_so_rather_than_reporting_a_number() -> None:
    lines = " ".join(
        night_narrative(
            _features(rhr=None, usable=False),
            _baseline(9),
            _detection(DetectionLevel.NA, None),
            "x",
        )
    )
    assert "left out rather than guessed at" in lines


def test_records_do_not_break_the_hash_chain(tmp_path: Path) -> None:
    """These entries join the same tamper-evident chain as the agent's."""
    db_file = _db(tmp_path)
    conn = connect(db_file)
    record_ingest(conn, "me", 660, "your watch")
    record_night_scored(
        conn, _features(), _baseline(3), _detection(DetectionLevel.GREEN, -10.4), None
    )
    intact, bad = verify_hash_chain("me", conn=conn)
    conn.close()

    assert intact is True
    assert bad is None
