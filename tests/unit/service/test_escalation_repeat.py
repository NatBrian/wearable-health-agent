"""Getting worse must not be met with silence.

A person was escalated about on one night, told the system they felt unwell, and then got
materially worse. Nothing was sent the second time, because something had been sent for
that investigation once. That is the failure this file exists to prevent.
"""

import json
from datetime import date

from wha.db import connect
from wha.db.migrations import apply_schema
from wha.models import Detection, DetectionLevel, Forecast
from wha.service.nightly import _should_escalate_again


def _db(
    previous_robust_z: float | None = None,
    recorded: bool = True,
    night: str = "2026-09-09",
):
    conn = connect(":memory:")
    apply_schema(conn)
    if recorded:
        payload = {"interaction_id": "ep_1", "night": night}
        if previous_robust_z is not None:
            payload["robust_z"] = previous_robust_z
        conn.execute(
            """INSERT INTO notifications
               (id, subject_id, episode_id, interaction_id, channel, kind, payload_json,
                queued_at_utc, status)
               VALUES ('ntf_1', 'sim', 'ep_1', 'ep_1', 'telegram', 'ESCALATION', ?,
                       '2026-09-08T14:41:56Z', 'SENT')""",
            (json.dumps(payload),),
        )
        conn.commit()
    return conn


def _detection(robust_z: float, night: date = date(2026, 9, 9)) -> Detection:
    return Detection(
        subject_id="sim",
        night_date=night,
        deviation_bpm=robust_z * 1.5,
        robust_z=robust_z,
        residual_bpm=robust_z * 1.5,
        level=DetectionLevel.RED,
        flagged=True,
        forecast=Forecast(),
    )


def test_a_first_escalation_is_always_sent() -> None:
    assert _should_escalate_again(_db(recorded=False), "ep_1", _detection(6.8)) == "first"


def test_a_materially_worse_night_is_escalated_again() -> None:
    """Six robust deviations became nine and the person heard nothing."""
    assert _should_escalate_again(_db(previous_robust_z=6.83), "ep_1", _detection(9.34)) == "worse"


def test_the_same_night_rescored_is_not_escalated_again() -> None:
    """Night scoring re-runs every few hours. The same reading must not repeat the message."""
    assert _should_escalate_again(_db(previous_robust_z=6.83), "ep_1", _detection(6.83)) is None


def test_a_slightly_worse_night_is_not_escalated_again() -> None:
    """Below one of the person's own deviations is not a change this system can call one."""
    assert _should_escalate_again(_db(previous_robust_z=6.83), "ep_1", _detection(7.2)) is None


def test_an_improving_night_is_not_escalated_again() -> None:
    assert _should_escalate_again(_db(previous_robust_z=9.34), "ep_1", _detection(7.0)) is None


def test_a_reading_that_stays_extreme_is_said_again_after_a_couple_of_nights() -> None:
    """Asked what happens if the night is steady rather than worse, the answer was silence.

    A reading that holds at seven robust deviations above somebody's own normal, night
    after night, is not good news, and saying nothing after the first warning reads as
    though it were.
    """
    conn = _db(previous_robust_z=6.83, night="2026-09-08")

    assert _should_escalate_again(conn, "ep_1", _detection(6.83, date(2026, 9, 10))) == "still"


def test_a_steady_reading_the_very_next_night_is_not_said_again() -> None:
    """The counterpart. Repeating the same sentence nightly is how a warning stops being
    read, and alarm fatigue is its own harm."""
    conn = _db(previous_robust_z=6.83, night="2026-09-08")

    assert _should_escalate_again(conn, "ep_1", _detection(6.83, date(2026, 9, 9))) is None


def test_an_improving_reading_is_never_called_still() -> None:
    """ "Still far outside your usual range" about a reading that has come down is false."""
    conn = _db(previous_robust_z=6.83, night="2026-09-08")

    assert _should_escalate_again(conn, "ep_1", _detection(5.0, date(2026, 9, 12))) is None
