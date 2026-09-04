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
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from wha import service
from wha.clock import local_today, to_local
from wha.models import Answer, AuditFilter

app = FastAPI(
    title="Wearable Health Early Warning Agent",
    version="1.0",
    summary="Everything an interface needs. One person, one device, localhost only.",
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
    """Every public constant, plus the subject's local date.

    Enumerated from the module rather than listed by hand, so a constant added to
    ``wha.constants`` is available to an interface immediately and this endpoint cannot
    drift away from the code. Screens used to import these directly, which a browser
    cannot do and which also let a threshold shown on a screen disagree with the one the
    detector used.

    Names are kept exactly as they appear in the source, so a reader can find the constant
    and its reasoning without a mapping table.
    """
    from wha import constants

    exported: dict[str, Any] = {}
    for name in dir(constants):
        if not name.isupper():
            continue
        value = getattr(constants, name)
        if isinstance(value, str | int | float | bool | list | dict | type(None)):
            exported[name] = value

    # Not a constant, but a client cannot read the environment and needs to know which
    # person this installation is configured for.
    from wha.config import get_settings

    exported["today"] = local_today().isoformat()
    exported["configured_subject"] = get_settings().subject
    return exported


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
    service.delete_all_subject_data(subject_id)
    return {"status": "deleted", "subject_id": subject_id}


# ------------------------------------------------------------------------ status


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
) -> list[Any]:
    """Every calendar night in the range, including nights with no reading."""
    end_d = end or local_today()
    start_d = start or (end_d - timedelta(days=days))
    return service.list_nights(subject_id, start=start_d, end=end_d)


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
def post_settings(body: dict[str, Any]) -> Any:
    """Change those, and report what actually changed."""
    return service.update_settings(**body)


@app.get("/subjects/{subject_id}/profile")
def get_subject_profile(subject_id: str) -> Any:
    """The five standing facts about a person that the rules actually read."""
    return service.get_subject_profile(subject_id)


@app.post("/subjects/{subject_id}/profile")
def post_subject_profile(subject_id: str, body: dict[str, Any]) -> Any:
    """Change them. This changes how the rules decide, so it is recorded."""
    from wha.models import SubjectProfilePatch

    return service.update_subject_profile(
        SubjectProfilePatch.model_validate(body), subject_id=subject_id
    )


@app.get("/knowledge/provenance")
def get_knowledge_provenance() -> Any:
    """Where each clinical number came from, so a screen can mark the guesses."""
    return service.get_knowledge_provenance()


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
    return checks[component](**(overrides or {}))
