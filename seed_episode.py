"""Seed a realistic multi-stage episode with beliefs, trace audit events, and differential outcome."""

import json
from datetime import UTC, date, datetime, timedelta
from wha.db import connect
from wha.db.migrations import apply_schema
from wha.models import (
    BaselineRung,
    CauseId,
    Citation,
    DifferentialItem,
    Disposition,
    EpisodeOutcome,
)

def seed_demo_episode():
    conn = connect()
    apply_schema(conn)

    ep_id = "ep_demo_illness"
    subj_id = "demo-illness-onset"
    now = datetime.now(UTC)

    # 1. Subject
    conn.execute(
        """INSERT OR IGNORE INTO subjects (subject_id, label, source_kind, timezone, created_at_utc)
           VALUES (?, 'Demo Illness Onset', 'synthetic', 'Asia/Singapore', ?)""",
        (subj_id, now.isoformat()),
    )

    # 2. Episode
    conn.execute(
        """INSERT OR REPLACE INTO episodes (
               episode_id, subject_id, thread_id, opened_on, closed_on, state,
               disposition, baseline_nights, baseline_rung, step_count
           ) VALUES (?, ?, 'th_demo_01', '2026-08-21', '2026-08-22', 'CLOSED',
                     'LIKELY_ILLNESS', 21, 'PERSONAL', 2)""",
        (ep_id, subj_id),
    )

    # 3. Beliefs
    b1_marginals = {
        "infection": 0.45, "alcohol": 0.08, "exertion": 0.04,
        "sleep_restriction": 0.12, "stress": 0.09, "vaccination": 0.01,
        "travel": 0.02, "medication": 0.01, "luteal": 0.0,
        "recovery_tail": 0.03, "sensor_artifact": 0.01, "unexplained": 0.14
    }
    b2_marginals = {
        "infection": 0.88, "alcohol": 0.01, "exertion": 0.01,
        "sleep_restriction": 0.02, "stress": 0.02, "vaccination": 0.0,
        "travel": 0.01, "medication": 0.0, "luteal": 0.0,
        "recovery_tail": 0.01, "sensor_artifact": 0.0, "unexplained": 0.04
    }

    conn.execute(
        """INSERT OR REPLACE INTO beliefs (
               episode_id, seq, trigger, ts_utc, marginals_json, p_illness
           ) VALUES (?, 1, 'nightly_deviation', ?, ?, 0.45)""",
        (ep_id, (now - timedelta(hours=24)).isoformat(), json.dumps(b1_marginals)),
    )
    conn.execute(
        """INSERT OR REPLACE INTO beliefs (
               episode_id, seq, trigger, ts_utc, marginals_json, p_illness
           ) VALUES (?, 2, 'user_answer_fever', ?, ?, 0.88)""",
        (ep_id, (now - timedelta(hours=12)).isoformat(), json.dumps(b2_marginals)),
    )

    # 4. Interactions
    opts = [
        {"option_id": "fever", "label": "Fever / Chills"},
        {"option_id": "cough", "label": "Cough / Sore Throat"},
        {"option_id": "fatigue", "label": "Fatigue / Body Aches"},
        {"option_id": "none", "label": "None of these"}
    ]
    rejections = [
        ["probe_alcohol", 0.08],
        ["probe_exercise", 0.04],
        ["probe_stress", 0.05]
    ]

    conn.execute(
        """INSERT OR REPLACE INTO interactions (
               id, episode_id, probe_id, question_text, text_source, options_json,
               evsi, interruption_cost, channel, status, asked_at_utc, answered_at_utc,
               answer_option_id, free_text, rejected_json
           ) VALUES (
               'int_demo_01', ?, 'probe_symptoms',
               'We noticed an overnight resting HR elevation (+3.8 bpm). Are you experiencing any of these symptoms today?',
               'llm', ?, 0.42, 0.15, 'telegram', 'ANSWERED', ?, ?, 'fever', 'Mild chills since morning', ?
           )""",
        (
            ep_id,
            json.dumps(opts),
            (now - timedelta(hours=14)).isoformat(),
            (now - timedelta(hours=12)).isoformat(),
            json.dumps(rejections),
        ),
    )

    # 5. Outcome (Validated with Pydantic)
    outcome = EpisodeOutcome(
        schema_version="1.0",
        episode_id=ep_id,
        subject_id=subj_id,
        opened_on=date(2026, 8, 21),
        closed_on=date(2026, 8, 22),
        disposition=Disposition.LIKELY_ILLNESS,
        observation="Elevated overnight resting heart rate (+3.8 bpm above personal baseline) combined with reported fever and chills indicates high probability of acute viral respiratory infection.",
        baseline_nights=21,
        baseline_rung=BaselineRung.PERSONAL,
        differential=[
            DifferentialItem(
                cause=CauseId.INFECTION,
                probability=0.88,
                supporting=["+3.8 bpm RHR elevation over 2 nights", "Reported mild chills and fever"],
                contradicting=[],
            ),
            DifferentialItem(
                cause=CauseId.UNEXPLAINED,
                probability=0.04,
                supporting=[],
                contradicting=[],
            ),
            DifferentialItem(
                cause=CauseId.SLEEP_RESTRICTION,
                probability=0.02,
                supporting=[],
                contradicting=["Sleep duration was 7.8 hours"],
            ),
            DifferentialItem(
                cause=CauseId.STRESS,
                probability=0.02,
                supporting=[],
                contradicting=[],
            ),
        ],
        evidence_used=[
            "Nightly RHR trend: 2026-08-20 (+3.1 bpm), 2026-08-21 (+3.8 bpm)",
            "User questionnaire response: fever/chills",
            "Stanford Viral Infection Wearable Cohort Evidence"
        ],
        ruled_out=[
            "alcohol: Confirmed no evening alcohol intake; lack of rebound pattern.",
            "exertion: No strenuous workout recorded in preceding 18 hours."
        ],
        citations=[
            Citation(
                source_id="quer_2021_wearable_infection",
                title="Wearable sensor data show significant resting heart rate elevation during pre-symptomatic phase",
                uri="https://doi.org/10.1038/s41591-021-01404-1",
                passage="Wearable sensor data show significant resting heart rate elevation (+1.5 to +3.5 bpm) during the pre-symptomatic and acute phase of viral respiratory infections.",
                retrieval_score=0.92,
            )
        ],
        unsupported_claims=0,
        action="rest",
        escalation_criteria=[
            "Shortness of breath or difficulty breathing at rest",
            "Persistent high fever > 39.0C unresponsive to antipyretics",
            "Severe chest pain, confusion, or inability to stay hydrated"
        ],
        confidence="high",
        interruptions_used_this_week=1,
        depth_used_this_episode=1,
    )

    conn.execute(
        """INSERT OR REPLACE INTO outcomes (episode_id, schema_version, payload_json, created_at_utc)
           VALUES (?, '1.0', ?, ?)""",
        (ep_id, outcome.model_dump_json(), now.isoformat()),
    )

    # 6. Audit Events (Trace)
    stages = [
        ("investigate", "read_history", '{"subject_id": "demo-illness-onset", "nights": 14}', 120),
        ("investigate", "check_surveillance", '{"region": "SG", "pathogen": "ILI"}', 85),
        ("investigate", "query_evidence", '{"query": "resting heart rate elevation viral incubation"}', 145),
        ("decide", "compute_evsi_policy", '{"active_causes": 12, "candidates": 9}', 15),
        ("conclude", "generate_differential", '{"top_cause": "infection", "prob": 0.88}', 420),
    ]

    prev_hash = "0" * 64
    for idx, (op, tool, args, lat) in enumerate(stages, 1):
        ev_id = f"aud_demo_{idx:03d}"
        ev_hash = f"hash_sha256_{idx:03d}_{op}"
        conn.execute(
            """INSERT OR REPLACE INTO audit_events (
                   event_id, subject_id, episode_id, step_index, timestamp_utc,
                   actor, operation, control_tier, tool_name, tool_args_json,
                   permission_decision, latency_ms, safety_event, prev_hash, hash
               ) VALUES (?, ?, ?, ?, ?, 'agent', ?, 'T1', ?, ?, 'allowed', ?, 'none', ?, ?)""",
            (
                ev_id, subj_id, ep_id, idx,
                (now - timedelta(minutes=60 - idx * 10)).isoformat(),
                op, tool, args, lat, prev_hash, ev_hash,
            ),
        )
        prev_hash = ev_hash

    conn.commit()
    conn.close()
    print("Demo episode successfully seeded!")

if __name__ == "__main__":
    seed_demo_episode()
