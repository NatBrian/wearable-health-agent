"""The HTTP boundary. Everything an interface needs, and nothing it does not.

The dashboard used to call service functions as Python imports. That was already a clean
layering, with no SQL and no database access in any screen, but it was a layering only
Python could cross. Replacing Streamlit with React would have meant writing a backend
first.

This is that backend. Every endpoint is a thin pass-through to the same service functions,
returning the same Pydantic models, which serialise to JSON without further work. There is
no logic here beyond routing, on purpose: an endpoint that computed something would be a
second place where behaviour lives, and the two would drift.

``/config`` exists because the dashboard reads constants directly, which a browser client
cannot do. Anything an interface needs to know about thresholds or today's date comes from
there rather than from an import.

Bound to localhost. This holds one person's health record and has no authentication,
because it is a single-user application running on that person's own machine. That is a
deliberate scope decision and it is stated in the README rather than assumed.
"""

from datetime import date, datetime, timedelta
from typing import Annotated, Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from wha import service
from wha.clock import local_today, to_local
from wha.config import get_settings as get_app_settings
from wha.models import (
    Answer,
    AuditFilter,
    DashboardSummary,
    DetectionLevel,
    KnowledgeProvenanceSummary,
    SettingsPatch,
    SubjectProfilePatch,
)

app = FastAPI(
    title="Wearable Health Early Warning Agent",
    version="1.0",
    summary="Everything an interface needs. One person, one device, localhost only.",
)

# CORS is a browser boundary for the configured local frontend, not authentication. The API
# remains local-only and has no authentication, so only the expected loopback origins are
# allowed to make browser requests.
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_app_settings().dashboard_origins,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Accept", "Content-Type"],
)


class AnswerBody(BaseModel):
    """An answer to a question the agent asked."""

    probe_id: str
    option_id: str | None = None
    free_text: str | None = None
    declined: bool = False


class MessageBody(BaseModel):
    """One turn of conversation from the person."""

    text: str
    episode_id: str | None = None
    episode_summary: str = ""
    age_years: int | None = None


class DecisionBody(BaseModel):
    """A human review decision on a drafted outcome."""

    decision: str
    edited_prose: str | None = None
    rationale: str | None = None


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness only. Says nothing about the person."""
    return {"status": "ok"}


@app.get("/config")
def get_config() -> dict[str, Any]:
    """Public settings and operating limits the browser client needs to explain."""
    return service.get_dashboard_configuration()


@app.get("/localise")
def localise(utc: str) -> dict[str, str]:
    """Render a UTC timestamp in the subject's timezone.

    Here because the dashboard imported wha.clock. Timezone handling is where this project
    has already had one real defect, comparing a UTC date against local night dates, and it
    belongs in one place rather than in every client.
    """
    from datetime import datetime

    try:
        moment = datetime.fromisoformat(utc)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Not a timestamp: {utc}") from exc
    return {"local": to_local(moment).isoformat()}


# ---------------------------------------------------------------------- subjects


@app.get("/subjects")
def list_subjects() -> list[Any]:
    """Everyone this installation holds data for."""
    return service.list_subjects()


@app.delete("/subjects/{subject_id}")
def delete_subject(subject_id: str) -> dict[str, str]:
    """Erase everything held about a person."""
    if subject_id == "me":
        raise HTTPException(status_code=403, detail="The real subject cannot be deleted")
    service.delete_all_subject_data(subject_id)
    return {"status": "deleted", "subject_id": subject_id}


# ------------------------------------------------------------------------ status


def _record_end(subject_id: str) -> date:
    """Where a window of nights should end: today, or later if the record runs ahead.

    A night dated after today exists whenever the watch is being simulated forward, and it
    is a real row with a real reading. Ending every window at the calendar date hid the
    newest night on every screen, which made the record and the interface disagree about
    what had been measured.
    """
    newest = service.latest_recorded_night(subject_id)
    today = local_today()
    return max(newest, today) if newest else today


@app.get("/subjects/{subject_id}/status")
def get_status(subject_id: str) -> Any:
    """The status strip: what is running, what arrived, how mature the baseline is."""
    return service.get_system_status(subject_id)


# ------------------------------------------------------------------------ nights


@app.get("/subjects/{subject_id}/nights")
def list_nights(
    subject_id: str,
    start: date | None = None,
    end: date | None = None,
    days: int = Query(default=60, ge=1, le=400),
    level: Annotated[list[DetectionLevel] | None, Query()] = None,
    investigated_only: bool = False,
) -> list[Any]:
    """Every calendar night in the range, including nights with no reading."""
    end_d = end or _record_end(subject_id)
    start_d = start or (end_d - timedelta(days=days))
    nights = service.list_nights(subject_id, start=start_d, end=end_d)
    return service.filter_history_nights(nights, levels=level, investigated_only=investigated_only)


@app.get("/subjects/{subject_id}/dashboard-summary", response_model=DashboardSummary)
def get_dashboard_summary(subject_id: str, end: date | None = None) -> DashboardSummary:
    """Latest sleep/steps observations and steps averaged over the configured calendar window."""
    config = service.get_dashboard_configuration()
    return service.get_dashboard_summary(
        subject_id,
        end=end or _record_end(subject_id),
        steps_window_days=config["dashboard"]["steps_average_days"],
    )


# Declared before the `{night_date}` route below so that `pipeline` in the path segment
# after `nights` cannot be read as a date. Checked by a test rather than by reasoning.
@app.get("/subjects/{subject_id}/pipeline/nights")
def list_pipeline_nights(subject_id: str, days: int = Query(default=60, ge=1, le=400)) -> list[Any]:
    """Just enough about each night to draw the stepper: date, level, whether investigated."""
    return service.list_pipeline_nights(subject_id, days=days, end=_record_end(subject_id))


@app.get("/subjects/{subject_id}/nights/{night_date}/pipeline")
def get_night_pipeline(subject_id: str, night_date: date) -> Any:
    """One night's journey from watch to conclusion, step by step.

    Assembled from what was stored rather than re-run, so it cannot disagree with the
    detector, and a step with no recorded time is returned with no time rather than a
    plausible one.
    """
    try:
        return service.get_night_pipeline(subject_id, night_date)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/subjects/{subject_id}/oxygen")
def list_oxygen(subject_id: str, days: int = Query(default=7, ge=1, le=60)) -> list[Any]:
    """Spot SpO2 samples in the last N days. Sparse and never baselined, see
    docs/DESIGN-DATA-CHANNELS.md."""
    return service.list_oxygen_readings(subject_id, days=days)


@app.get("/subjects/{subject_id}/nights/{night_date}")
def get_night(subject_id: str, night_date: date) -> Any:
    """One night, with its features, baseline and detection."""
    try:
        detail = service.get_night_detail(subject_id, night_date)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if detail is None:
        raise HTTPException(status_code=404, detail="No such night")
    return detail


# ---------------------------------------------------------------------- episodes


@app.get("/subjects/{subject_id}/episodes")
def list_episodes(subject_id: str) -> list[Any]:
    """Investigations opened for this person."""
    return service.list_episodes(subject_id)


@app.get("/episodes/{episode_id}")
def get_episode(episode_id: str) -> Any:
    """One investigation in full: outcome, interactions, citations, trace.

    A missing episode is a 404, not a 500. A client has to be able to tell "no such thing"
    from "the application broke", and the service layer signals the first by raising.
    """
    try:
        detail = service.get_episode(episode_id)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if detail is None:
        raise HTTPException(status_code=404, detail="No such episode")
    return detail


@app.get("/subjects/{subject_id}/pending")
def get_pending(subject_id: str) -> Any:
    """The one thing that needs the person, or nothing."""
    return service.get_pending_interaction(subject_id)


@app.post("/episodes/{episode_id}/answer")
def submit_answer(episode_id: str, body: AnswerBody) -> dict[str, str]:
    """Record an answer to the agent's question."""
    service.submit_answer(
        episode_id,
        Answer(
            probe_id=body.probe_id,
            option_id=body.option_id,
            free_text=body.free_text,
            declined=body.declined,
        ),
    )
    return {"status": "recorded"}


@app.post("/episodes/{episode_id}/review")
def submit_review(episode_id: str, body: DecisionBody) -> dict[str, str]:
    """Record a human decision on a drafted outcome."""
    service.submit_human_decision(
        episode_id=episode_id,
        decision=body.decision,
        edited_prose=body.edited_prose,
        rationale=body.rationale,
    )
    return {"status": "recorded"}


# ------------------------------------------------------------------ conversation


@app.get("/subjects/{subject_id}/conversation")
def get_transcript(subject_id: str, limit: int = Query(default=40, ge=1, le=500)) -> list[Any]:
    """The whole conversation, oldest first."""
    return service.get_transcript(subject_id, limit=limit)


@app.get("/subjects/{subject_id}/conversation/sessions")
def get_conversation_sessions(
    subject_id: str,
    limit_turns: int = Query(default=400, ge=1, le=2000),
    since_night: date | None = None,
) -> list[Any]:
    """The conversation split into the consultations it was, newest first.

    A screen showing the last N turns regardless of when they happened puts a question
    about one night under another night's verdict.
    """
    return service.get_conversation_sessions(
        subject_id, limit_turns=limit_turns, since_night=since_night
    )


@app.post("/subjects/{subject_id}/conversation")
def post_message(subject_id: str, body: MessageBody) -> Any:
    """One turn, with every deterministic check applied around the model."""
    return service.send_message(
        subject_id=subject_id,
        text=body.text,
        episode_id=body.episode_id,
        episode_summary=body.episode_summary,
        age_years=body.age_years,
    )


@app.get("/subjects/{subject_id}/urgency")
def get_urgency(subject_id: str) -> dict[str, Any]:
    """What the rules have concluded, and which rule concluded it."""
    state = service.urgency_banner(subject_id)
    return {
        "urgency": state["urgency"],
        "reason": service.latest_urgency_reason(subject_id),
        "set_on": state["set_on"],
        "days_ago": state["days_ago"],
        "stale": state["stale"],
        "cleared": state["cleared"],
    }


@app.post("/subjects/{subject_id}/urgency/acknowledged")
def acknowledge_urgency(subject_id: str) -> dict[str, Any]:
    """The person says they have seen somebody about it. Recorded, not erased."""
    return service.acknowledge_urgency(subject_id)


# --------------------------------------------------------------------- handover


@app.get("/subjects/{subject_id}/handover")
def get_handover(subject_id: str, episode_id: str | None = None) -> dict[str, Any]:
    """The SBAR summary to take to a clinician."""
    handover = service.build_handover(subject_id, episode_id=episode_id)
    return {
        "text": handover.as_text(),
        "situation": handover.situation,
        "background": handover.background,
        "assessment": handover.assessment,
        "recommendation": handover.recommendation,
        "questions": handover.questions,
        "what_this_is_not": handover.what_this_is_not,
    }


# ------------------------------------------------------------------------ audit


@app.get("/subjects/{subject_id}/audit")
def query_audit(
    subject_id: str,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = 0,
    episode_id: str | None = None,
    actor: str | None = None,
    operation: str | None = None,
    safety_event: str | None = None,
    since_utc: datetime | None = None,
    until_utc: datetime | None = None,
) -> dict[str, Any]:
    """The tamper-evident record, filtered, and whether it is still intact.

    Filters are query parameters rather than a posted body so a record view is a URL that
    can be linked to and reloaded, which is what an audit page is for.
    """
    audit_filter = AuditFilter(
        subject_id=subject_id,
        episode_id=episode_id,
        actor=actor,
        operation=operation,
        safety_event=safety_event,
        since_utc=since_utc,
        until_utc=until_utc,
    )
    intact, bad_event = service.verify_hash_chain(subject_id)
    return {
        "events": service.query_audit(audit_filter, limit=limit, offset=offset),
        "plain": service.list_plain_records(subject_id, limit=limit),
        "count": service.count_audit_events(subject_id),
        "intact": intact,
        "first_bad_event": bad_event,
        "permitted_tools": sorted(service.get_permitted_tool_names()),
    }


@app.get("/subjects/{subject_id}/audit/export")
def export_audit(
    subject_id: str,
    episode_id: str | None = None,
    actor: str | None = None,
    operation: str | None = None,
    safety_event: str | None = None,
    since_utc: datetime | None = None,
    until_utc: datetime | None = None,
) -> dict[str, str]:
    """The record as text, for someone who wants to keep or check it elsewhere.

    Returns content rather than writing a file. Where that content is saved is the
    client's business, and a browser cannot be handed a server-side path.
    """
    import tempfile
    from pathlib import Path as _Path

    audit_filter = AuditFilter(
        subject_id=subject_id,
        episode_id=episode_id,
        actor=actor,
        operation=operation,
        safety_event=safety_event,
        since_utc=since_utc,
        until_utc=until_utc,
    )
    target = _Path(tempfile.mkdtemp()) / f"audit-{subject_id}.jsonl"
    service.export_audit(audit_filter, target)
    return {"content": target.read_text(encoding="utf-8")}


# --------------------------------------------------------------------- settings


@app.get("/settings")
def get_settings() -> Any:
    """Where readings come from and how the person is contacted."""
    return service.get_service_settings()


@app.post("/settings")
def post_settings(body: SettingsPatch) -> Any:
    """Change those, and report what actually changed."""
    return service.update_settings(body)


@app.get("/subjects/{subject_id}/profile")
def get_subject_profile(subject_id: str) -> Any:
    """The five standing facts about a person that the rules actually read."""
    return service.get_subject_profile(subject_id)


@app.post("/subjects/{subject_id}/profile")
def post_subject_profile(subject_id: str, body: SubjectProfilePatch) -> Any:
    """Change them. This changes how the rules decide, so it is recorded."""
    return service.update_subject_profile(body, subject_id=subject_id)


@app.get("/knowledge/provenance")
def get_knowledge_provenance() -> Any:
    """Where each clinical number came from, so a screen can mark the guesses."""
    return service.get_knowledge_provenance()


@app.get("/knowledge/provenance/summary", response_model=KnowledgeProvenanceSummary)
def get_knowledge_provenance_summary() -> KnowledgeProvenanceSummary:
    """Entry counts for the Home evidence summary, computed outside the browser."""
    return service.get_knowledge_provenance_summary()


@app.get("/knowledge/safety-provenance")
def get_safety_rule_provenance() -> list[dict[str, str | int | None]]:
    """Where each number in the deterministic safety floor came from."""
    return service.get_safety_rule_provenance()


@app.post("/diagnostics/{component}")
def check_component(component: str, overrides: dict[str, Any] | None = None) -> Any:
    """Probe one subsystem live: the bridge, the model provider, or Telegram.

    Takes overrides because the Settings screen lets a person test a host or token they
    have typed but not saved yet. Without them the button would only ever test what is
    already stored, which is the opposite of what it is for.
    """
    checks = {
        "bridge": service.test_bridge_connection,
        "llm": service.test_llm_connection,
        "telegram": service.test_telegram_connection,
    }
    if component not in checks:
        raise HTTPException(status_code=404, detail=f"No such component: {component}")
    supplied = overrides or {}
    if component == "llm":
        supplied = {
            "provider": supplied.get("provider", supplied.get("llm_provider")),
            "model": supplied.get("model", supplied.get("llm_model")),
            "base_url": supplied.get("base_url", supplied.get("llm_base_url")),
            "api_key": supplied.get("api_key", supplied.get("llm_api_key")),
        }
    return checks[component](**{key: value for key, value in supplied.items() if value is not None})
