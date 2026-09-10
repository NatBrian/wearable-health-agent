"""What Kotlin calls. Every function is @guarded and returns JSON.

A second client of the same service layer the HTTP API exposes; see the parity test in
tests/unit/android/test_facade_parity.py. Reads of the record use the same end-date rule
as the API: today, or later if the record runs ahead (the watch being simulated
forward), so "the last sixty nights" means the last sixty the watch produced.
"""

from __future__ import annotations

import json
import tempfile
import threading
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from wha import service
from wha.clock import local_today, to_local
from wha.models import Answer, AuditFilter, SettingsPatch, SubjectProfilePatch
from wha_android.envelope import error, guarded, ok

# One job at a time, like safe_job_wrapper's lock on the PC. WorkManager may overlap an
# ingest with a tick; the second waits rather than racing the first for the database.
_JOB_LOCK = threading.Lock()


def _record_end(subject_id: str) -> date:
    newest = service.latest_recorded_night(subject_id)
    today = local_today()
    return max(newest, today) if newest else today


# ----------------------------------------------------------------- configuration


@guarded
def config() -> str:
    return ok(service.config_export())


@guarded
def localise(utc_iso: str) -> str:
    return ok({"local": to_local(datetime.fromisoformat(utc_iso)).isoformat()})


@guarded
def settings() -> str:
    return ok(service.get_service_settings())


@guarded
def update_settings(patch_json: str) -> str:
    patch = SettingsPatch.model_validate(json.loads(patch_json))
    return ok(service.update_settings(patch))


@guarded
def profile(subject_id: str) -> str:
    return ok(service.get_subject_profile(subject_id))


@guarded
def update_profile(subject_id: str, patch_json: str) -> str:
    patch = SubjectProfilePatch.model_validate(json.loads(patch_json))
    return ok(service.update_subject_profile(patch, subject_id=subject_id))


# ------------------------------------------------------------------------ status


@guarded
def status(subject_id: str) -> str:
    return ok(service.get_system_status(subject_id))


@guarded
def urgency(subject_id: str) -> str:
    state = service.urgency_banner(subject_id)
    return ok(
        {
            "urgency": state["urgency"],
            "reason": service.latest_urgency_reason(subject_id),
            "set_on": state["set_on"],
            "days_ago": state["days_ago"],
            "stale": state["stale"],
            "cleared": state["cleared"],
        }
    )


@guarded
def acknowledge_urgency(subject_id: str) -> str:
    return ok(service.acknowledge_urgency(subject_id))


# ------------------------------------------------------------------------ nights


@guarded
def nights(subject_id: str, days: int = 60) -> str:
    end = _record_end(subject_id)
    return ok(service.list_nights(subject_id, start=end - timedelta(days=days), end=end))


@guarded
def night(subject_id: str, night_date: str) -> str:
    return ok(service.get_night_detail(subject_id, date.fromisoformat(night_date)))


@guarded
def pipeline_nights(subject_id: str, days: int = 60) -> str:
    return ok(service.list_pipeline_nights(subject_id, days=days, end=_record_end(subject_id)))


@guarded
def night_pipeline(subject_id: str, night_date: str) -> str:
    return ok(service.get_night_pipeline(subject_id, date.fromisoformat(night_date)))


# ---------------------------------------------------------------------- episodes


@guarded
def episodes(subject_id: str) -> str:
    return ok(service.list_episodes(subject_id))


@guarded
def episode(episode_id: str) -> str:
    return ok(service.get_episode(episode_id))


@guarded
def pending(subject_id: str) -> str:
    return ok(service.get_pending_interaction(subject_id))


@guarded
def answer(
    episode_id: str,
    probe_id: str,
    option_id: str | None,
    free_text: str | None,
    declined: bool,
) -> str:
    service.submit_answer(
        episode_id,
        Answer(probe_id=probe_id, option_id=option_id, free_text=free_text, declined=declined),
    )
    return ok({"status": "recorded"})


@guarded
def review(
    episode_id: str, decision: str, edited_prose: str | None, rationale: str | None
) -> str:
    service.submit_human_decision(
        episode_id=episode_id, decision=decision, edited_prose=edited_prose, rationale=rationale
    )
    return ok({"status": "recorded"})


@guarded
def handover(subject_id: str, episode_id: str | None = None) -> str:
    h = service.build_handover(subject_id, episode_id=episode_id)
    return ok(
        {
            "text": h.as_text(),
            "situation": h.situation,
            "background": h.background,
            "assessment": h.assessment,
            "recommendation": h.recommendation,
            "questions": h.questions,
            "what_this_is_not": h.what_this_is_not,
        }
    )


# ------------------------------------------------------------------ conversation


@guarded
def conversation(subject_id: str, limit: int = 40) -> str:
    return ok(service.get_transcript(subject_id, limit=limit))


@guarded
def conversation_sessions(subject_id: str, limit_turns: int = 400) -> str:
    return ok(service.get_conversation_sessions(subject_id, limit_turns=limit_turns))


@guarded
def say(subject_id: str, text: str, episode_id: str | None = None) -> str:
    return ok(service.send_message(subject_id=subject_id, text=text, episode_id=episode_id))


# ------------------------------------------------------------------------- audit


@guarded
def audit(subject_id: str, limit: int = 100, offset: int = 0) -> str:
    audit_filter = AuditFilter(subject_id=subject_id)
    intact, bad_event = service.verify_hash_chain(subject_id)
    return ok(
        {
            "events": service.query_audit(audit_filter, limit=limit, offset=offset),
            "plain": service.list_plain_records(subject_id, limit=limit),
            "count": service.count_audit_events(subject_id),
            "intact": intact,
            "first_bad_event": bad_event,
            "permitted_tools": sorted(service.get_permitted_tool_names()),
        }
    )


@guarded
def audit_export(subject_id: str) -> str:
    target = Path(tempfile.mkdtemp()) / f"audit-{subject_id}.jsonl"
    service.export_audit(AuditFilter(subject_id=subject_id), target)
    return ok({"content": target.read_text(encoding="utf-8")})


# --------------------------------------------------------------------- knowledge


@guarded
def knowledge_provenance() -> str:
    return ok(service.get_knowledge_provenance())


@guarded
def safety_provenance() -> str:
    return ok(service.get_safety_rule_provenance())


# ------------------------------------------------------------------- diagnostics


@guarded
def diagnose(component: str, overrides_json: str = "{}") -> str:
    checks = {"bridge": service.test_bridge_connection, "llm": service.test_llm_connection}
    if component not in checks:
        return error("invalid", f"No such component: {component}")
    return ok(checks[component](**json.loads(overrides_json)))


@guarded
def doctor() -> str:
    return ok([{"name": i.name, "status": str(i.status), "detail": i.detail} for i in service.run_doctor()])


@guarded
def retrieval_ready() -> str:
    return ok({"ready": service.corpus_present()})


@guarded
def fetch_corpus() -> str:
    return ok({"message": service.fetch_data("corpus")})


# -------------------------------------------------------------------------- jobs


def _job(name: str, fn: Any) -> str:
    from wha.clock import now_utc
    from wha.models import ComponentStatus

    with _JOB_LOCK:
        started = now_utc().isoformat()
        result = fn()
        service.record_component_status(
            ComponentStatus(
                component=name,
                ok=True,
                detail="ran from the phone",
                checked_at_utc=now_utc(),
                severity="ok",
            )
        )
        return ok({"job": name, "started": started, "result": result})


@guarded
def run_ingest() -> str:
    return _job("ingest", lambda: service.run_ingest())


@guarded
def run_nightly() -> str:
    from wha.service import jobs

    return _job("nightly", lambda: [d.model_dump(mode="json") for d in jobs._rescore_recent()])


@guarded
def run_episode_tick() -> str:
    return _job("episode_tick", lambda: service.run_episode_tick())


@guarded
def run_startup_catchup() -> str:
    from wha.service import jobs

    return _job("startup_catchup", lambda: jobs.run_startup_catchup())
