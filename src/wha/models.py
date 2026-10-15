"""Domain, service, tool, and LLM models for WHA.

All models are defined here and are frozen with extra="forbid" by default
as specified in docs/CONTRACTS.md section 6.
"""

from datetime import date, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator

# ---------------------------------------------------------------------------
# 6.1 Enumerations
# ---------------------------------------------------------------------------


class BaselineRung(StrEnum):
    COLD = "COLD"
    PRIOR_DOMINATED = "PRIOR_DOMINATED"
    SHRINKING = "SHRINKING"
    PERSONAL = "PERSONAL"
    MATURE = "MATURE"


class DetectionLevel(StrEnum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"
    NA = "NA"


class ForecastStatus(StrEnum):
    OK = "OK"
    NOT_RUN = "NOT_RUN"
    TOO_FEW_NIGHTS = "TOO_FEW_NIGHTS"
    FAILED = "FAILED"


class EpisodeState(StrEnum):
    OPEN = "OPEN"
    AWAITING_USER = "AWAITING_USER"
    AWAITING_MEASUREMENT = "AWAITING_MEASUREMENT"
    AWAITING_HUMAN_REVIEW = "AWAITING_HUMAN_REVIEW"
    CLOSED = "CLOSED"


class Disposition(StrEnum):
    EXPLAINED_BY_EVENT = "EXPLAINED_BY_EVENT"
    LIKELY_ILLNESS = "LIKELY_ILLNESS"
    LIKELY_BENIGN = "LIKELY_BENIGN"
    ESCALATED = "ESCALATED"
    UNRESOLVED = "UNRESOLVED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class ActionKind(StrEnum):
    OBSERVE = "OBSERVE"
    ASK = "ASK"
    MEASURE = "MEASURE"
    ESCALATE = "ESCALATE"
    CONCLUDE = "CONCLUDE"


class ControlTier(StrEnum):
    T0 = "T0"
    T1 = "T1"
    T2 = "T2"
    T3 = "T3"
    T4 = "T4"
    X = "X"


class CauseId(StrEnum):
    INFECTION = "infection"
    ALCOHOL = "alcohol"
    EXERTION = "exertion"
    SLEEP_RESTRICTION = "sleep_restriction"
    STRESS = "stress"
    LUTEAL = "luteal"
    VACCINATION = "vaccination"
    TRAVEL = "travel"
    MEDICATION = "medication"
    RECOVERY_TAIL = "recovery_tail"
    SENSOR_ARTIFACT = "sensor_artifact"
    UNEXPLAINED = "unexplained"


class StageStatus(StrEnum):
    RAN = "RAN"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"
    PENDING = "PENDING"


# ---------------------------------------------------------------------------
# 6.2 Pipeline models
# ---------------------------------------------------------------------------


class NightlyFeatures(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    subject_id: str
    night_date: date
    rhr_bpm: float | None
    coverage_minutes: int
    implausible_dropped: int = 0
    usable: bool
    steps_prev_day: int | None = None
    sleep_hours: float | None = None
    exercise_end_offset_h: float | None = None
    # Which window the reading was taken over: "sleep" when the watch reported when the
    # person slept, "clock" when it did not and local 00:00-07:00 was assumed. A health
    # figure has to be able to say how it was produced.
    rhr_window_source: str = "clock"


class Baseline(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    centre_bpm: float
    scale_bpm: float
    usable_nights: int
    rung: BaselineRung
    shrink_weight: float


class Forecast(BaseModel):
    """Chronos second opinion. Advisory. Never sets level or flagged."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    predicted_bpm: float | None = None
    lo_bpm: float | None = None
    hi_bpm: float | None = None
    forecast_z: float | None = None  # (actual - predicted) / half-interval width
    status: ForecastStatus = ForecastStatus.NOT_RUN


class Detection(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    subject_id: str
    night_date: date
    deviation_bpm: float | None = None
    robust_z: float | None = None
    explained_bpm: float = 0.0
    residual_bpm: float | None = None
    level: DetectionLevel
    flagged: bool  # set by the deterministic detector ONLY
    forecast: Forecast
    reasons: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 6.3 Belief, probes and questions
# ---------------------------------------------------------------------------


class CausePrior(BaseModel):
    """One row of data/knowledge/causes.yaml. Every field carries a citation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    cause: CauseId
    base_rate: float  # P(present on any given night)
    effect_mean_bpm: float  # expected contribution to nocturnal RHR
    effect_sd_bpm: float  # between-person spread of that effect
    profile: list[float]  # contribution weight by nights since onset
    evidence_grade: Literal["A", "B", "C", "D"]
    citation: str


class BeliefState(BaseModel):
    """Belief over WHICH CAUSES ARE CONTRIBUTING to this episode's deviation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    marginals: dict[CauseId, float]  # all keys present. Does NOT sum to 1
    p_illness: float  # P(infection contributing). The decision variable
    state_logprob: list[float] = Field(default_factory=list)  # length BELIEF_STATE_COUNT

    def top(self, n: int = 3) -> list[tuple[CauseId, float]]:
        return sorted(self.marginals.items(), key=lambda item: item[1], reverse=True)[:n]


class AnswerOption(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    option_id: str  # <= 8 chars, used inside callback_data
    label: str


class Probe(BaseModel):
    """WHAT to find out. Selected by arithmetic, never by the LLM."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    probe_id: str
    target_cause: CauseId
    answer_space: list[AnswerOption]  # FIXED. Likelihood table lives over these
    evsi: float  # utility units, computed at decision time
    interruption_cost: float
    fallback_text: str  # used if LLM is unavailable or invalid


class Question(BaseModel):
    """HOW it is asked. Written by LLM, in context, informed by what it retrieved."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    probe: Probe
    text: str
    text_source: Literal["llm", "fallback"]
    options: list[AnswerOption]  # same length and slot order as probe.answer_space
    allows_free_text: bool


class Answer(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    probe_id: str
    option_id: str | None = None
    free_text: str | None = None
    declined: bool = False


# ---------------------------------------------------------------------------
# 6.4 Actions, evidence and outcome
# ---------------------------------------------------------------------------


class MeasurementRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    measurement_id: str
    kind: Literal["spot_resting_hr", "wear_tonight"]
    instruction: str
    expires_at_utc: datetime


class MeasurementResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    measurement_id: str
    kind: str
    value: float | None = None
    observed_at_utc: datetime | None = None
    satisfied: bool


class Citation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: str
    title: str
    uri: str | None = None
    passage: str
    retrieval_score: float
    quoted_span: str | None = None


class ExtractedFact(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    field: str
    value: str | float | bool | None  # explicit null, never omitted
    evidence_span: str  # verbatim substring of source text
    source_ref: str  # interaction id, or doc_id + chunk_id
    confidence: Literal["stated", "implied"]


class GeneratedClaim(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str
    citation: Citation | None = None  # None means unsupported
    evidence_span: str | None = None


class DifferentialItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    cause: CauseId
    probability: float
    supporting: list[str] = Field(default_factory=list)
    contradicting: list[str] = Field(default_factory=list)
    # How far THIS EPISODE moved the cause: probability now, minus probability under the
    # prior alone. Signed, so a cause the evidence argued AGAINST reads negative.
    #
    # The panel is ordered by this and, until 5 September 2026, drew bars of `probability`
    # instead, so the bar lengths meant something different from the ordering, and
    # `st.bar_chart` re-sorted the categories alphabetically on top of that, discarding the
    # ranking entirely. Carrying the number is what lets the chart show what the panel
    # claims to show. `docs/CONTRACTS.md` is read-only and does not list this field; the
    # disagreement is recorded in docs/DISCLOSURES.md, as it is for the other three.
    moved: float = 0.0


class Action(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: ActionKind
    question: Question | None = None
    measurement: MeasurementRequest | None = None
    escalation_level: Literal["advice", "same_day", "urgent"] | None = None
    disposition: Disposition | None = None
    rationale: str  # produced by policy, not LLM
    rejected: list[tuple[str, float]] = Field(default_factory=list)
    # The symptom this ASK is following up, when the action was chosen as a rule rather
    # than on expected information gain. Carried on the action rather than inferred from
    # the rationale text, because the ask node needs it for two things that must not be
    # guessed at: a per-night interaction id, so a follow-up does not overwrite the
    # question it follows, and the `followup` initiation that makes the per-episode cap
    # countable. A cap that cannot count is not a cap, and an uncapped follow-up is a
    # nightly alarm.
    followup_for: str | None = None


class EpisodeOutcome(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    episode_id: str
    subject_id: str
    opened_on: date
    closed_on: date
    disposition: Disposition
    observation: str
    baseline_nights: int
    baseline_rung: BaselineRung
    differential: list[DifferentialItem]
    evidence_used: list[str]
    ruled_out: list[str]
    citations: list[Citation]
    unsupported_claims: int
    action: Literal["rest", "monitor", "seek_same_day_care", "seek_urgent_care"]
    escalation_criteria: list[str]
    confidence: Literal["low", "moderate", "high", "cannot_determine"]
    interruptions_used_this_week: int
    depth_used_this_episode: int


# ---------------------------------------------------------------------------
# 6.5 View models for the service layer
# ---------------------------------------------------------------------------


class Subject(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    subject_id: str
    label: str
    source_kind: str
    timezone: str
    usable_nights: int
    rung: BaselineRung


class ComponentStatus(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    component: Literal["bridge", "scheduler", "llm", "telegram", "database", "datasets"]
    ok: bool
    detail: str
    checked_at_utc: datetime
    severity: Literal["ok", "warn", "error"]


class DetectionStreak(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    length: int
    level: DetectionLevel
    direction: Literal["rising", "steady", "falling"] | None = None


class SystemStatus(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    components: list[ComponentStatus]
    last_ingest_utc: datetime | None = None
    last_nightly_utc: datetime | None = None
    usable_nights: int
    rung: BaselineRung
    errors_24h: int
    quiet_nights_streak: int
    detection_streak: DetectionStreak | None = None
    # Nights in the same recent window with no usable reading. A night the watch did not
    # measure is not a quiet night, and reporting it as one turns missing data into
    # reassurance, which is the opposite of what it means.
    unmeasured_recent_nights: int = 0


class ConnectionCheck(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    ok: bool
    detail: str
    latency_ms: int | None = None


class OxygenReading(BaseModel):
    """One spot SpO2 sample. Never baselined: see docs/DESIGN-DATA-CHANNELS.md."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ts_utc: datetime
    percentage: float


class NightRow(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    night_date: date
    rhr_bpm: float | None = None
    centre_bpm: float | None = None
    band_lo: float | None = None
    band_hi: float | None = None
    deviation_bpm: float | None = None
    explained_bpm: float = 0.0
    residual_bpm: float | None = None
    coverage_minutes: int
    usable: bool
    level: DetectionLevel
    episode_id: str | None = None
    # Whether the night was measured over the sleep the watch recorded, or over the
    # midnight-to-07:00 clock fallback because it recorded none. The Today and History
    # pages state which, in those words, so the field has to reach them. It did not:
    # `NightlyFeatures` carried it and `NightRow` did not, and the pages read it with
    # `getattr(n, "rhr_window_source", "clock")`, so the default always won and both
    # asserted "because no sleep was recorded" on every night including the 44 of 72
    # where sleep WAS recorded. A dead branch that makes a false statement about the
    # person's own watch is worse than the vaguer wording it replaced.
    rhr_window_source: str = "clock"
    # What the forecasting model expected for this night, and how far the reading fell
    # from it. Advisory only: it never sets the level or opens an investigation. Carried
    # on the row so an interface can show it without reaching past the service layer.
    forecast_bpm: float | None = None
    forecast_lo_bpm: float | None = None
    forecast_hi_bpm: float | None = None
    forecast_status: str | None = None
    # Carried here, not fetched per-night through NightDetail, so a chart across many
    # nights costs one list_nights call rather than one NightDetail call per night. Both
    # are frequently None: sleep_hours is absent whenever the watch recorded no sleep
    # session, and steps_prev_day whenever the previous day has no step bucket.
    sleep_hours: float | None = None
    steps_prev_day: int | None = None


class DashboardSummary(BaseModel):
    """Latest sleep and step observations plus a calendar-bounded steps summary."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    latest_sleep_hours: float | None = None
    latest_sleep_night: date | None = None
    latest_steps: int | None = None
    latest_steps_night: date | None = None
    steps_average: int | None = None
    steps_window_start: date
    steps_window_end: date


class KnowledgeProvenanceSummary(BaseModel):
    """Entry counts for the Home evidence summary, without exposing figure counts."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    unevidenced_entries: int
    total_entries: int


class NightDetail(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    row: NightRow
    features: NightlyFeatures
    baseline: Baseline
    detection: Detection


class EpisodeSummary(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    episode_id: str
    opened_on: date
    closed_on: date | None = None
    state: EpisodeState
    disposition: Disposition | None = None
    night_span: tuple[date, date]
    top_cause: CauseId | None = None
    top_probability: float | None = None


class PipelineStage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    status: StageStatus
    reason: str  # why it ran, or why it was skipped
    duration_ms: int | None = None
    detail_json: dict[str, Any] = Field(default_factory=dict)


class StepLayer(StrEnum):
    """Which machine ran the step.

    The three halves of this system are different kinds of machine and behave differently
    when they are wrong. Arithmetic that is wrong is wrong the same way every night; a
    language model is not. A person looking at a result deserves to know which one produced
    it, so the layer travels with the step rather than being inferred from its name.
    """

    DETERMINISTIC = "deterministic"
    AGENTIC = "agentic"
    USER = "user"
    SAFETY = "safety"


class StepStatus(StrEnum):
    """RAN and SKIPPED are claims about the night. UNRECORDED is a claim about us.

    Reporting "we did not write this down" as "it did not run" is exactly the defect the
    September 2026 audit found on every episode: `_pipeline_stages` matched stage names
    against a column that never held them, so every stage on every episode read SKIPPED
    with an invented reason, directly above a chart showing the work it denied doing.
    """

    RAN = "ran"
    SKIPPED = "skipped"
    NOT_APPLICABLE = "not_applicable"
    UNRECORDED = "unrecorded"


class PipelineStepDef(BaseModel):
    """One step of the journey, independent of any particular night."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    step_id: str
    ordinal: int
    layer: StepLayer


class PipelineStepView(BaseModel):
    """What one step did on one night.

    `occurred_utc` is optional because most of the deterministic half records what it
    computed and not when, and a clock time nobody wrote down would be an invented figure.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    step_id: str
    ordinal: int
    layer: StepLayer
    status: StepStatus
    reason: str
    headline_figure: str | None = None
    occurred_utc: datetime | None = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)
    sources: list[Citation] = Field(default_factory=list)
    detail_json: dict[str, Any] = Field(default_factory=dict)


class PipelineHeadline(BaseModel):
    """The tiles above the graph. Assembled from stored values, never recalculated."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    level: DetectionLevel
    flagged: bool
    # How well the system knows this person's normal. A screen that says "your usual
    # range" without this can claim a personal range on a three-night baseline, where the
    # band is still the population estimate.
    rung: BaselineRung | None = None
    primary_cause: CauseId | None = None
    primary_probability: float | None = None
    sleep_hours: float | None = None
    coverage_minutes: int = 0
    questions_asked: int = 0
    sources_read: int = 0


class NightPipeline(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    subject_id: str
    night_date: date
    episode_id: str | None = None
    headline: PipelineHeadline
    steps: list[PipelineStepView] = Field(default_factory=list)


class PipelineNightRef(BaseModel):
    """One entry in the night stepper. Small on purpose: sixty of these load at once."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    night_date: date
    level: DetectionLevel
    has_episode: bool
    usable: bool


# The journey, in the order it happens. The agentic ids are the agent's own node names, so
# a step drawn on screen and a stage written into `episode_traces` cannot mean different
# things. `deliver` has no node: it is what happens after the graph finishes.
CANONICAL_PIPELINE_STEPS: tuple[PipelineStepDef, ...] = (
    PipelineStepDef(step_id="collect", ordinal=1, layer=StepLayer.DETERMINISTIC),
    PipelineStepDef(step_id="store", ordinal=2, layer=StepLayer.DETERMINISTIC),
    PipelineStepDef(step_id="sleep_window", ordinal=3, layer=StepLayer.DETERMINISTIC),
    PipelineStepDef(step_id="features", ordinal=4, layer=StepLayer.DETERMINISTIC),
    PipelineStepDef(step_id="baseline", ordinal=5, layer=StepLayer.DETERMINISTIC),
    PipelineStepDef(step_id="subtract_explained", ordinal=6, layer=StepLayer.DETERMINISTIC),
    PipelineStepDef(step_id="detect", ordinal=7, layer=StepLayer.DETERMINISTIC),
    # The deterministic floor over what you have TOLD us, added 7 September 2026.
    #
    # It ran before the agent from the beginning and was not on this list, so the one
    # screen that claims to show every step showed everything except the layer that can
    # override every other layer. It is also where the persistence and co-occurrence
    # rules live, and those are the rules a person most needs to see, because they are
    # the ones that decide whether anybody is told anything.
    PipelineStepDef(step_id="safety_floor", ordinal=8, layer=StepLayer.SAFETY),
    PipelineStepDef(step_id="episode_open", ordinal=9, layer=StepLayer.AGENTIC),
    PipelineStepDef(step_id="preload", ordinal=10, layer=StepLayer.AGENTIC),
    PipelineStepDef(step_id="investigate", ordinal=11, layer=StepLayer.AGENTIC),
    PipelineStepDef(step_id="believe", ordinal=12, layer=StepLayer.AGENTIC),
    PipelineStepDef(step_id="decide", ordinal=13, layer=StepLayer.AGENTIC),
    PipelineStepDef(step_id="ask", ordinal=14, layer=StepLayer.AGENTIC),
    PipelineStepDef(step_id="answer", ordinal=15, layer=StepLayer.USER),
    PipelineStepDef(step_id="conclude", ordinal=16, layer=StepLayer.AGENTIC),
    PipelineStepDef(step_id="critique", ordinal=17, layer=StepLayer.AGENTIC),
    PipelineStepDef(step_id="review", ordinal=18, layer=StepLayer.AGENTIC),
    PipelineStepDef(step_id="deliver", ordinal=19, layer=StepLayer.AGENTIC),
    PipelineStepDef(step_id="safety_phrase_rules", ordinal=20, layer=StepLayer.SAFETY),
    PipelineStepDef(step_id="safety_triage", ordinal=21, layer=StepLayer.SAFETY),
)


class InteractionView(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    probe_id: str
    question_text: str
    text_source: Literal["llm", "fallback"]
    options: list[AnswerOption]
    evsi: float
    interruption_cost: float
    rejected: list[tuple[str, float]] = Field(default_factory=list)
    answer_option_id: str | None = None
    free_text: str | None = None
    status: str
    asked_at_utc: datetime
    answered_at_utc: datetime | None = None


class EpisodeDetail(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    summary: EpisodeSummary
    outcome: EpisodeOutcome | None = None
    stages: list[PipelineStage] = Field(default_factory=list)
    belief_history: list[tuple[int, str, BeliefState]] = Field(default_factory=list)
    interactions: list[InteractionView] = Field(default_factory=list)
    measurements: list[MeasurementResult] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    stripped_claims: list[str] = Field(default_factory=list)


class PendingInteraction(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["question", "measurement", "review"]
    episode_id: str
    question: Question | None = None
    measurement: MeasurementRequest | None = None
    draft_outcome: EpisodeOutcome | None = None


class GroundedAnswer(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str
    citations: list[Citation] = Field(default_factory=list)
    refused: bool  # true when it could not be grounded
    refusal_reason: str | None = None


class AuditFilter(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    subject_id: str
    episode_id: str | None = None
    actor: str | None = None
    operation: str | None = None
    safety_event: str | None = None
    since_utc: datetime | None = None
    until_utc: datetime | None = None


class AuditEventView(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str
    timestamp_utc: datetime
    episode_id: str | None = None
    step_index: int | None = None
    actor: str
    operation: str
    control_tier: ControlTier | None = None
    tool_name: str | None = None
    permission_decision: str | None = None
    sources: list[str] = Field(default_factory=list)
    validation_status: str | None = None
    human_decision: str | None = None
    safety_event: str = "none"
    latency_ms: int | None = None
    hash_ok: bool  # chain verification result for this row


class EvaluationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    suite: str
    generated_at_utc: datetime
    metrics: dict[str, float] = Field(default_factory=dict)
    tables: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    figures: list[str] = Field(default_factory=list)  # relative paths to written plots
    sample_size: int
    caveats: list[str] = Field(default_factory=list)  # underpowered claims, stated explicitly


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    interruption_budget_per_week: int
    depth_budget_per_episode: int
    policy_cost_weight: float
    notify_channel: Literal["none", "telegram"]
    llm_provider: Literal["cassette", "ollama_native", "openai_compatible"]
    llm_model: str
    llm_base_url: str | None = None
    bridge_host: str | None = None
    # secrets are NEVER present on this model


class SettingsPatch(BaseModel):
    """Every field optional. Secrets are write-only and never read back."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    interruption_budget_per_week: int | None = Field(default=None, ge=0, le=20)
    depth_budget_per_episode: int | None = Field(default=None, ge=0, le=10)
    policy_cost_weight: float | None = Field(default=None, ge=0, le=1)
    notify_channel: Literal["none", "telegram"] | None = None
    llm_provider: Literal["cassette", "ollama_native", "openai_compatible"] | None = None
    llm_model: str | None = None
    llm_base_url: str | None = None
    bridge_host: str | None = None
    bridge_token: SecretStr | None = None
    llm_api_key: SecretStr | None = None
    telegram_token: SecretStr | None = None


class SubjectProfile(BaseModel):
    """The standing facts about a person that something in this system actually reads.

    Every field here is consumed by named code. That is the rule for being on this list,
    and it is why weight, height and BMI are not: nothing has a covariate model, the
    baseline becomes personal after seven nights, and a field nobody reads tells a person
    their data is being used when it is not.

    `notes_for_doctor` is the exception that proves the rule. It is free text, it goes into
    the SBAR handover a clinician reads, and it enters no prompt. The distinction is the
    point: information for the doctor is not information for the model. Free text in a
    prompt is the "model reasons from unverified clinical text" path this whole project
    exists to prevent, and it would feel safe precisely because the person wrote it.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    subject_id: str
    # The Marburg age gate (minimum_age_years: 35) and Marburg item 1.
    age_years: int | None = None
    sex: Literal["female", "male"] | None = None
    # Marburg item 2. Pre-filled so the conversation asks only the three that vary.
    known_vascular_disease: bool | None = None
    # The luteal cause in causes.yaml. A standing fact, not worth an interruption.
    menstruates: bool | None = None
    # Read by nothing on purpose. It becomes a disclosure rather than a covariate.
    rate_lowering_medicine: bool | None = None
    notes_for_doctor: str | None = None
    updated_at_utc: datetime | None = None


class SubjectProfilePatch(BaseModel):
    """Every field optional, so a partial update leaves the rest alone."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    age_years: int | None = Field(default=None, ge=0, le=120)
    sex: Literal["female", "male"] | None = None
    known_vascular_disease: bool | None = None
    menstruates: bool | None = None
    rate_lowering_medicine: bool | None = None
    notes_for_doctor: str | None = None


# ---------------------------------------------------------------------------
# 6.6 Agent, tool and LLM models
# ---------------------------------------------------------------------------


class HeartRateSample(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    ts_utc: datetime
    avg_bpm: float
    min_bpm: float | None = None
    max_bpm: float | None = None
    origin: str | None = None


class AuditEvent(BaseModel):
    """What append_audit takes. The stored row plus the hash fields it computes."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str
    subject_id: str
    episode_id: str | None = None
    step_index: int | None = None
    checkpoint_id: str | None = None
    timestamp_utc: datetime
    actor: Literal["agent", "human", "system", "monitor"]
    operation: Literal[
        "ingest",
        "nightly",
        "plan",
        "retrieval",
        "execute_tool",
        "invoke_agent",
        "chat",
        "notify",
        "human_decision",
        "settings",
    ]
    control_tier: ControlTier | None = None
    input: dict[str, Any] | None = None
    tool_name: str | None = None
    tool_args: dict[str, Any] | None = None
    tool_result: dict[str, Any] | None = None
    permission_decision: Literal["allowed", "denied", "required_approval"] | None = None
    sources: list[str] = Field(default_factory=list)
    output: dict[str, Any] | None = None
    output_schema_version: str | None = None
    validation_status: Literal["pass", "repaired", "failed"] | None = None
    human_decision: str | None = None
    human_decision_rationale: str | None = None
    model_id: str | None = None
    prompt_id: str | None = None
    prompt_version: str | None = None
    latency_ms: int | None = None
    token_usage: dict[str, Any] | None = None
    safety_event: str = "none"


class ToolCall(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    tool_name: str
    args: dict[str, Any] = Field(default_factory=dict)
    called_at_utc: datetime


class EpisodePattern(BaseModel):
    """What the model supplies to find_similar_past_episodes. It chooses these."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    peak_residual_bpm: float | None = None
    elevated_nights: int | None = None
    exercise_recorded: bool | None = None
    month: int | None = None


class PastEpisodeSummary(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    episode_id: str
    opened_on: date
    closed_on: date
    disposition: Disposition
    peak_residual_bpm: float
    elevated_nights: int
    resolved_by: str  # e.g. "answer: probe_alcohol=three"


class EpisodeContext(BaseModel):
    """Everything update_belief needs that is not a night, an answer or a measurement."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    subject_id: str
    episode_opened_on: date
    rung: BaselineRung
    usable_nights: int
    prior_illness_episodes: list[PastEpisodeSummary] = Field(default_factory=list)
    cycle_applicable: bool | None = None  # None means not yet asked
    cycle_last_period_start: date | None = None
    # `update_belief` reads this by name and raises recovery_tail sharply when it is True.
    # It was not on this model, so `hasattr(context, "has_recent_illness")` was False even
    # for a correctly built context, and nothing built one anyway. Two ways for the same
    # boost to never fire.
    has_recent_illness: bool = False


class InjectionVerdict(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    detected: bool
    patterns_hit: list[str] = Field(default_factory=list)
    source_id: str


class Prompt(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    prompt_id: str
    prompt_version: str
    rendered: str  # the fully assembled text sent to the provider
    schema_name: str  # the Pydantic model the response must validate against


class LLMUsage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    model_id: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    provider: Literal["cassette", "ollama_native", "openai_compatible"]


class Done(BaseModel):
    """investigate: the model has enough."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    reason: str


class InvestigateStep(BaseModel):
    """investigate returns exactly one of these."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    tool_call: ToolCall | None = None
    done: Done | None = None

    @model_validator(mode="after")
    def validate_exactly_one(self) -> "InvestigateStep":
        has_tool = self.tool_call is not None
        has_done = self.done is not None
        if has_tool == has_done:
            raise ValueError("InvestigateStep must have exactly one of tool_call or done set")
        return self


class QuestionDraft(BaseModel):
    """write_question and interview_followup."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str
    option_labels: list[str]  # SAME LENGTH AND SLOT ORDER as Probe.answer_space
    rationale: str  # why this wording, for the trace


class VetoVerdict(BaseModel):
    """veto_check. May only CANCEL an authorised ask."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    veto: bool
    reason: str


class CritiqueVerdict(BaseModel):
    """critique. May only cause MORE claims to be stripped, never fewer."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    strip_claim_indices: list[int] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)


class OutcomeDraft(BaseModel):
    """write_outcome. Prose only. Every number must already exist in the structured fields."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    observation: str
    claims: list[GeneratedClaim] = Field(default_factory=list)
    action_text: str
    escalation_criteria: list[str] = Field(default_factory=list)


class RedFlagVerdict(BaseModel):
    """red_flag_check. ADDITIVE ONLY. Combined with the rules by set union."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    suspected_flag_ids: list[str] = Field(default_factory=list)
    reason: str


# ---------------------------------------------------------------------------
# 6.7 Retrieval, fixture, and data models
# ---------------------------------------------------------------------------


class Chunk(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    chunk_id: str
    doc_id: str
    layer: int
    title: str
    uri: str | None = None
    text: str  # the small chunk, matched on
    parent_text: str  # the enclosing section, RETURNED
    metadata: dict[str, Any] = Field(default_factory=dict)


class Scenario(BaseModel):
    """A frozen fixture in tests/fixtures/scenarios/*.json."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    description: str
    days: int
    base_bpm: float
    seed: int
    timezone: str
    injections: list[dict[str, Any]] = Field(default_factory=list)
    oracle: dict[str, Any] = Field(default_factory=dict)  # hidden answers, revealed only on ask
    local_disease_activity: dict[str, Any] | None = None
    corpus: Literal["clean", "poisoned"] | None = None
    prior_budget_used: int = 0
    expect: dict[str, Any] = Field(default_factory=dict)  # THE CONTRACT


class RawPayload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    subject_id: str
    source_kind: str
    fetched_at_utc: datetime
    sha256: str
    body: dict[str, Any]
