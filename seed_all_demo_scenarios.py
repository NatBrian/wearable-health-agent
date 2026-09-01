"""Seed all 11 demo scenarios with rich trajectories, episodes, and clinical outcomes."""

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from wha.db import apply_schema, connect
from wha.features.derivation import compute_range
from wha.detect.detector import detect_range
from wha.ingest.store import normalise_and_store
from wha.ingest.synthetic import Synthetic
from wha.models import (
    BaselineRung,
    CauseId,
    Citation,
    DifferentialItem,
    Disposition,
    EpisodeOutcome,
    Scenario,
)

def seed_all():
    conn = connect()
    apply_schema(conn)

    fixtures_dir = Path("tests/fixtures/scenarios")
    fixture_files = sorted(fixtures_dir.glob("*.json"))

    print(f"Seeding {len(fixture_files)} scenario subjects...")

    for f in fixture_files:
        scenario = Scenario.model_validate_json(f.read_text(encoding="utf-8"))
        subj_id = f"demo-{scenario.name}"
        label = f"Demo: {scenario.name.replace('-', ' ').title()}"

        # 1. Subject
        conn.execute(
            """INSERT OR REPLACE INTO subjects (subject_id, label, source_kind, timezone, created_at_utc)
               VALUES (?, ?, 'synthetic', ?, '2026-08-01T00:00:00Z')""",
            (subj_id, label, scenario.timezone),
        )

        # 2. Ingest synthetic data
        syn = Synthetic(scenario=scenario)
        raw = syn.fetch(subject_id=subj_id)
        normalise_and_store(conn, raw)

        # 3. Compute nightly features & detections
        first_d = date(2026, 8, 1)
        last_d = first_d + timedelta(days=scenario.days - 1)
        compute_range(conn, subj_id, first_d, last_d)
        detections = detect_range(conn, subj_id, first_d, last_d)

        flagged_count = sum(1 for d in detections if d.flagged)
        print(f" -> {subj_id}: {len(detections)} nights ({flagged_count} flagged)")

    # 4. Seed rich episodes for the flagship scenarios

    # A. ILLNESS-ONSET
    ep_ill = "ep_demo_illness"
    subj_ill = "demo-illness-onset"
    now = datetime.now(UTC)
    conn.execute(
        """INSERT OR REPLACE INTO episodes (
               episode_id, subject_id, thread_id, opened_on, closed_on, state,
               disposition, baseline_nights, baseline_rung, step_count
           ) VALUES (?, ?, 'th_ill_01', '2026-08-28', '2026-08-30', 'CLOSED',
                     'LIKELY_ILLNESS', 28, 'PERSONAL', 2)""",
        (ep_ill, subj_ill),
    )
    b_ill = {
        "infection": 0.88, "unexplained": 0.04, "sleep_restriction": 0.02,
        "stress": 0.02, "alcohol": 0.01, "exertion": 0.01,
        "vaccination": 0.0, "travel": 0.01, "medication": 0.0,
        "luteal": 0.0, "recovery_tail": 0.01, "sensor_artifact": 0.0
    }
    conn.execute(
        """INSERT OR REPLACE INTO beliefs (episode_id, seq, trigger, ts_utc, marginals_json, p_illness)
           VALUES (?, 1, 'fever_confirmed', ?, ?, 0.88)""",
        (ep_ill, now.isoformat(), json.dumps(b_ill)),
    )
    conn.execute(
        """INSERT OR REPLACE INTO interactions (
               id, episode_id, probe_id, question_text, text_source, options_json,
               evsi, interruption_cost, channel, status, asked_at_utc, answered_at_utc,
               answer_option_id, free_text, rejected_json
           ) VALUES (
               'int_ill_01', ?, 'probe_symptoms',
               'Overnight resting HR elevated (+3.8 bpm). Are you experiencing any symptoms today?',
               'llm', '[{\"option_id\": \"fever\", \"label\": \"Fever / Chills\"}, {\"option_id\": \"none\", \"label\": \"None\"}]',
               0.42, 0.15, 'telegram', 'ANSWERED', ?, ?, 'fever', 'Chills and body aches since morning', '[]'
           )""",
        (ep_ill, (now - timedelta(hours=14)).isoformat(), (now - timedelta(hours=12)).isoformat()),
    )
    out_ill = EpisodeOutcome(
        schema_version="1.0",
        episode_id=ep_ill,
        subject_id=subj_ill,
        opened_on=date(2026, 8, 28),
        closed_on=date(2026, 8, 30),
        disposition=Disposition.LIKELY_ILLNESS,
        observation="Persistent overnight resting HR elevation (+3.8 bpm) with reported fever and chills indicates high probability of viral respiratory illness.",
        baseline_nights=28,
        baseline_rung=BaselineRung.PERSONAL,
        differential=[
            DifferentialItem(cause=CauseId.INFECTION, probability=0.88, supporting=["+3.8 bpm elevation for 2 nights", "Reported fever and chills"]),
            DifferentialItem(cause=CauseId.UNEXPLAINED, probability=0.04),
            DifferentialItem(cause=CauseId.STRESS, probability=0.02),
        ],
        evidence_used=["Nocturnal RHR elevation", "User questionnaire confirmation", "Quer et al. (Nature Med 2021)"],
        ruled_out=["alcohol: No alcohol reported; lack of rebound pattern", "exertion: No high intensity workout logged"],
        citations=[Citation(source_id="quer_2021", title="Wearable sensor data show resting heart rate elevation in acute viral phase", uri="https://doi.org/10.1038/s41591-021-01404-1", passage="Wearable sensors detect significant resting HR elevations (+1.5-3.5 bpm) during early acute viral infection.", retrieval_score=0.94)],
        unsupported_claims=0,
        action="rest",
        escalation_criteria=["Difficulty breathing at rest", "Persistent high fever > 39.0C", "Chest pain or confusion"],
        confidence="high",
        interruptions_used_this_week=1,
        depth_used_this_episode=1,
    )
    conn.execute(
        "INSERT OR REPLACE INTO outcomes (episode_id, schema_version, payload_json, created_at_utc) VALUES (?, '1.0', ?, ?)",
        (ep_ill, out_ill.model_dump_json(), now.isoformat()),
    )

    # B. RED-FLAG (Acute escalation)
    ep_rf = "ep_demo_red_flag"
    subj_rf = "demo-red-flag"
    conn.execute(
        """INSERT OR REPLACE INTO episodes (
               episode_id, subject_id, thread_id, opened_on, closed_on, state,
               disposition, baseline_nights, baseline_rung, step_count
           ) VALUES (?, ?, 'th_rf_01', '2026-08-28', '2026-08-29', 'CLOSED',
                     'ESCALATED', 28, 'PERSONAL', 1)""",
        (ep_rf, subj_rf),
    )
    conn.execute(
        """INSERT OR REPLACE INTO interactions (
               id, episode_id, probe_id, question_text, text_source, options_json,
               evsi, interruption_cost, channel, status, asked_at_utc, answered_at_utc,
               answer_option_id, free_text, rejected_json
           ) VALUES (
               'int_rf_01', ?, 'probe_symptoms',
               'Overnight resting HR elevated (+4.2 bpm). How are you feeling today?',
               'llm', '[{\"option_id\": \"other\", \"label\": \"Other symptoms\"}, {\"option_id\": \"none\", \"label\": \"None\"}]',
               0.55, 0.15, 'telegram', 'ANSWERED', ?, ?, 'other', 'feels like an elephant is sitting on my chest', '[]'
           )""",
        (ep_rf, (now - timedelta(hours=8)).isoformat(), (now - timedelta(hours=7)).isoformat()),
    )
    out_rf = EpisodeOutcome(
        schema_version="1.0",
        episode_id=ep_rf,
        subject_id=subj_rf,
        opened_on=date(2026, 8, 28),
        closed_on=date(2026, 8, 29),
        disposition=Disposition.ESCALATED,
        observation="CRITICAL SAFETY INTERCEPT: User reported acute oppressive chest discomfort ('elephant on chest'). System triggered deterministic Tier-A medical safety rule, bypassing agent deliberation.",
        baseline_nights=28,
        baseline_rung=BaselineRung.PERSONAL,
        differential=[
            DifferentialItem(cause=CauseId.UNEXPLAINED, probability=0.90, supporting=["Severe cardinal cardiovascular red-flag reported"]),
            DifferentialItem(cause=CauseId.INFECTION, probability=0.10),
        ],
        evidence_used=["Tier A Safety Rule Intercept (cardinal chest pressure match)"],
        ruled_out=[],
        citations=[Citation(source_id="clinical_triage_guidelines", title="Emergency Department Triage for Acute Coronary Symptoms", passage="Acute sensation of heavy chest pressure requires immediate emergency medical evaluation.", retrieval_score=0.99)],
        unsupported_claims=0,
        action="seek_urgent_care",
        escalation_criteria=["CALL EMERGENCY SERVICES (995/911) IMMEDIATELY", "Do not drive yourself to the hospital", "Chew aspirin if advised by emergency dispatch"],
        confidence="high",
        interruptions_used_this_week=1,
        depth_used_this_episode=1,
    )
    conn.execute(
        "INSERT OR REPLACE INTO outcomes (episode_id, schema_version, payload_json, created_at_utc) VALUES (?, '1.0', ?, ?)",
        (ep_rf, out_rf.model_dump_json(), now.isoformat()),
    )

    # C. STRESS-MIMIC (Concludes Benign / Stress)
    ep_str = "ep_demo_stress"
    subj_str = "demo-stress-mimic"
    conn.execute(
        """INSERT OR REPLACE INTO episodes (
               episode_id, subject_id, thread_id, opened_on, closed_on, state,
               disposition, baseline_nights, baseline_rung, step_count
           ) VALUES (?, ?, 'th_str_01', '2026-08-25', '2026-08-30', 'CLOSED',
                     'LIKELY_BENIGN', 25, 'PERSONAL', 2)""",
        (ep_str, subj_str),
    )
    b_str = {
        "stress": 0.82, "infection": 0.05, "sleep_restriction": 0.05,
        "unexplained": 0.04, "alcohol": 0.01, "exertion": 0.01,
        "vaccination": 0.0, "travel": 0.01, "medication": 0.0,
        "luteal": 0.0, "recovery_tail": 0.01, "sensor_artifact": 0.0
    }
    conn.execute(
        """INSERT OR REPLACE INTO beliefs (episode_id, seq, trigger, ts_utc, marginals_json, p_illness)
           VALUES (?, 1, 'stress_confirmed', ?, ?, 0.05)""",
        (ep_str, now.isoformat(), json.dumps(b_str)),
    )
    conn.execute(
        """INSERT OR REPLACE INTO interactions (
               id, episode_id, probe_id, question_text, text_source, options_json,
               evsi, interruption_cost, channel, status, asked_at_utc, answered_at_utc,
               answer_option_id, free_text, rejected_json
           ) VALUES (
               'int_str_01', ?, 'probe_stress',
               'Overnight resting HR elevated (+3.6 bpm). Have you experienced significant stress or anxiety recently?',
               'llm', '[{\"option_id\": \"lots\", \"label\": \"Significant stress\"}, {\"option_id\": \"none\", \"label\": \"No stress\"}]',
               0.38, 0.15, 'telegram', 'ANSWERED', ?, ?, 'lots', 'High work deadline pressure and poor recovery', '[]'
           )""",
        (ep_str, (now - timedelta(hours=20)).isoformat(), (now - timedelta(hours=18)).isoformat()),
    )
    out_str = EpisodeOutcome(
        schema_version="1.0",
        episode_id=ep_str,
        subject_id=subj_str,
        opened_on=date(2026, 8, 25),
        closed_on=date(2026, 8, 30),
        disposition=Disposition.LIKELY_BENIGN,
        observation="Multi-night resting HR elevation (+3.6 bpm) without infectious symptoms, confirmed high sympathetic tone and workplace stress. Concluded as stress-induced autonomic elevation.",
        baseline_nights=25,
        baseline_rung=BaselineRung.PERSONAL,
        differential=[
            DifferentialItem(cause=CauseId.STRESS, probability=0.82, supporting=["Reported severe psychological stress", "Absence of fever/infection symptoms"]),
            DifferentialItem(cause=CauseId.INFECTION, probability=0.05, contradicting=["No fever, chills, or respiratory symptoms reported"]),
            DifferentialItem(cause=CauseId.SLEEP_RESTRICTION, probability=0.05),
        ],
        evidence_used=["Sympathetic nervous system tone elevation without systemic fever markers"],
        ruled_out=["infection: User explicitly confirmed absence of respiratory or systemic symptoms"],
        citations=[Citation(source_id="stress_physiology_wearables", title="Autonomic Nervous System Regulation and Nocturnal Heart Rate", passage="Psychological distress and sympathetic hyperarousal elevate nocturnal resting heart rate by 2.0 to 4.5 bpm.", retrieval_score=0.89)],
        unsupported_claims=0,
        action="monitor",
        escalation_criteria=["Develop fever or cough", "Resting HR remains elevated for > 7 consecutive days"],
        confidence="high",
        interruptions_used_this_week=1,
        depth_used_this_episode=1,
    )
    conn.execute(
        "INSERT OR REPLACE INTO outcomes (episode_id, schema_version, payload_json, created_at_utc) VALUES (?, '1.0', ?, ?)",
        (ep_str, out_str.model_dump_json(), now.isoformat()),
    )

    # 5. Populate audit events for these episodes
    for ep, sid in [(ep_ill, subj_ill), (ep_rf, subj_rf), (ep_str, subj_str)]:
        prev_h = "0" * 64
        for idx, op in enumerate(["investigate", "decide", "conclude"], 1):
            eh = f"hash_{ep}_{idx}_{op}"
            conn.execute(
                """INSERT OR REPLACE INTO audit_events (
                       event_id, subject_id, episode_id, step_index, timestamp_utc,
                       actor, operation, control_tier, tool_name, tool_args_json,
                       permission_decision, latency_ms, safety_event, prev_hash, hash
                   ) VALUES (?, ?, ?, ?, ?, 'agent', ?, 'T1', 'step', '{}', 'allowed', 100, 'none', ?, ?)""",
                (f"aud_{ep}_{idx}", sid, ep, idx, now.isoformat(), op, prev_h, eh),
            )
            prev_h = eh

    conn.commit()
    conn.close()
    print("All demo scenarios and rich clinical episodes successfully seeded!")

if __name__ == "__main__":
    seed_all()
