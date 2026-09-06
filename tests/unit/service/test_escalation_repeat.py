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


def _db(previous_robust_z: float | None = None, recorded: bool = True):
    conn = connect(":memory:")
    apply_schema(conn)
    if recorded:
        payload = {"interaction_id": "ep_1"}
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


def _detection(robust_z: float) -> Detection:
    return Detection(
        subject_id="sim",
        night_date=date(2026, 9, 9),
        deviation_bpm=robust_z * 1.5,
        robust_z=robust_z,
        residual_bpm=robust_z * 1.5,
        level=DetectionLevel.RED,
        flagged=True,
        forecast=Forecast(),
    )


def test_a_first_escalation_is_always_sent() -> None:
    assert _should_escalate_again(_db(recorded=False), "ep_1", _detection(6.8)) is True


def test_a_materially_worse_night_is_escalated_again() -> None:
    """Six robust deviations became nine and the person heard nothing."""
    assert _should_escalate_again(_db(previous_robust_z=6.83), "ep_1", _detection(9.34)) is True


def test_the_same_night_rescored_is_not_escalated_again() -> None:
    """Night scoring re-runs every few hours. The same reading must not repeat the message."""
    assert _should_escalate_again(_db(previous_robust_z=6.83), "ep_1", _detection(6.83)) is False


def test_a_slightly_worse_night_is_not_escalated_again() -> None:
    """Below one of the person's own deviations is not a change this system can call one."""
    assert _should_escalate_again(_db(previous_robust_z=6.83), "ep_1", _detection(7.2)) is False


def test_an_improving_night_is_not_escalated_again() -> None:
    assert _should_escalate_again(_db(previous_robust_z=9.34), "ep_1", _detection(7.0)) is False
