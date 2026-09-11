package dev.wha.app.core

import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject

// Mirror of the Pydantic models the facade returns (docs/CONTRACTS.md section 6).
// Every optional Pydantic field is nullable with a null default; dict[str, Any] is a
// JsonObject; enums travel as their source strings, so a member added on the PC does
// not crash the phone. tests/unit/android/test_kotlin_models_match_contract.py checks
// every Pydantic field has a Kotlin field of the same snake_case name.

@Serializable data class ComponentStatus(
    val component: String,
    val ok: Boolean,
    val detail: String,
    val checked_at_utc: String,
    val severity: String,
)

@Serializable data class SystemStatus(
    val components: List<ComponentStatus> = emptyList(),
    val last_ingest_utc: String? = null,
    val last_nightly_utc: String? = null,
    val usable_nights: Int = 0,
    val rung: String = "",
    val errors_24h: Int = 0,
    val quiet_nights_streak: Int = 0,
    val unmeasured_recent_nights: Int = 0,
)

@Serializable data class NightRow(
    val night_date: String,
    val rhr_bpm: Double? = null,
    val centre_bpm: Double? = null,
    val band_lo: Double? = null,
    val band_hi: Double? = null,
    val deviation_bpm: Double? = null,
    val explained_bpm: Double = 0.0,
    val residual_bpm: Double? = null,
    val coverage_minutes: Int = 0,
    val usable: Boolean = false,
    val level: String = "",
    val episode_id: String? = null,
    val rhr_window_source: String = "clock",
    val forecast_bpm: Double? = null,
    val forecast_lo_bpm: Double? = null,
    val forecast_hi_bpm: Double? = null,
    val forecast_status: String? = null,
)

@Serializable data class NightlyFeatures(
    val subject_id: String = "",
    val night_date: String = "",
    val rhr_bpm: Double? = null,
    val coverage_minutes: Int = 0,
    val implausible_dropped: Int = 0,
    val usable: Boolean = false,
    val steps_prev_day: Int? = null,
    val sleep_hours: Double? = null,
    val exercise_end_offset_h: Double? = null,
    val rhr_window_source: String = "clock",
)

@Serializable data class Baseline(
    val centre_bpm: Double = 0.0,
    val scale_bpm: Double = 0.0,
    val usable_nights: Int = 0,
    val rung: String = "",
    val shrink_weight: Double = 0.0,
)

@Serializable data class Forecast(
    val predicted_bpm: Double? = null,
    val lo_bpm: Double? = null,
    val hi_bpm: Double? = null,
    val forecast_z: Double? = null,
    val status: String = "",
)

@Serializable data class Detection(
    val subject_id: String = "",
    val night_date: String = "",
    val deviation_bpm: Double? = null,
    val robust_z: Double? = null,
    val explained_bpm: Double = 0.0,
    val residual_bpm: Double? = null,
    val level: String = "",
    val flagged: Boolean = false,
    val forecast: Forecast? = null,
    val reasons: List<String> = emptyList(),
)

@Serializable data class NightDetail(
    val row: NightRow,
    val features: NightlyFeatures? = null,
    val baseline: Baseline? = null,
    val detection: Detection? = null,
)

@Serializable data class PipelineNightRef(
    val night_date: String,
    val level: String = "",
    val has_episode: Boolean = false,
    val usable: Boolean = false,
)

@Serializable data class PipelineStepView(
    val step_id: String,
    val ordinal: Int = 0,
    val layer: String = "",
    val status: String = "",
    val reason: String = "",
    val headline_figure: String? = null,
    val occurred_utc: String? = null,
    val inputs: JsonObject = JsonObject(emptyMap()),
    val outputs: JsonObject = JsonObject(emptyMap()),
    val sources: List<Citation> = emptyList(),
    val detail_json: JsonObject = JsonObject(emptyMap()),
)

@Serializable data class PipelineHeadline(
    val level: String = "",
    val flagged: Boolean = false,
    val rung: String? = null,
    val primary_cause: String? = null,
    val primary_probability: Double? = null,
    val sleep_hours: Double? = null,
    val coverage_minutes: Int = 0,
    val questions_asked: Int = 0,
    val sources_read: Int = 0,
)

@Serializable data class NightPipeline(
    val subject_id: String = "",
    val night_date: String = "",
    val episode_id: String? = null,
    val headline: PipelineHeadline? = null,
    val steps: List<PipelineStepView> = emptyList(),
)

@Serializable data class LineageEdge(
    val from_step: String,
    val output: String,
    val to_step: String,
)

@Serializable data class AnswerOption(
    val option_id: String,
    val label: String = "",
)

@Serializable data class Probe(
    val probe_id: String,
    val target_cause: String = "",
    val answer_space: List<AnswerOption> = emptyList(),
    val evsi: Double = 0.0,
    val interruption_cost: Double = 0.0,
    val fallback_text: String = "",
)

@Serializable data class Question(
    val probe: Probe? = null,
    val text: String = "",
    val text_source: String = "",
    val options: List<AnswerOption> = emptyList(),
    val allows_free_text: Boolean = false,
)

@Serializable data class MeasurementRequest(
    val measurement_id: String,
    val kind: String = "",
    val instruction: String = "",
    val expires_at_utc: String? = null,
)

@Serializable data class MeasurementResult(
    val measurement_id: String,
    val kind: String = "",
    val value: Double? = null,
    val observed_at_utc: String? = null,
    val satisfied: Boolean = false,
)

@Serializable data class Citation(
    val source_id: String,
    val title: String = "",
    val uri: String? = null,
    val passage: String = "",
    val retrieval_score: Double = 0.0,
)

@Serializable data class DifferentialItem(
    val cause: String,
    val probability: Double = 0.0,
    val supporting: List<String> = emptyList(),
    val contradicting: List<String> = emptyList(),
    val moved: Double = 0.0,
)

@Serializable data class BeliefState(
    val marginals: Map<String, Double> = emptyMap(),
    val p_illness: Double = 0.0,
    val state_logprob: List<Double> = emptyList(),
)

@Serializable data class BeliefEntry(
    val seq: Int = 0,
    val label: String = "",
    val belief: BeliefState? = null,
)
// Note: the wire shape of belief_history is a list of [seq, label, belief] arrays,
// which kotlinx.serialization cannot decode into BeliefEntry directly. EpisodeDetail
// below carries them as JsonElement and the view model reads each positionally;
// BeliefEntry names the positions.

@Serializable data class InteractionView(
    val id: String,
    val probe_id: String = "",
    val question_text: String = "",
    val text_source: String = "",
    val options: List<AnswerOption> = emptyList(),
    val evsi: Double = 0.0,
    val interruption_cost: Double = 0.0,
    val rejected: List<JsonElement> = emptyList(),
    val answer_option_id: String? = null,
    val free_text: String? = null,
    val status: String = "",
    val asked_at_utc: String = "",
    val answered_at_utc: String? = null,
)

@Serializable data class EpisodeSummary(
    val episode_id: String,
    val opened_on: String = "",
    val closed_on: String? = null,
    val state: String = "",
    val disposition: String? = null,
    val night_span: List<String> = emptyList(),
    val top_cause: String? = null,
    val top_probability: Double? = null,
)

@Serializable data class EpisodeOutcome(
    val schema_version: String = "1.0",
    val episode_id: String = "",
    val subject_id: String = "",
    val opened_on: String = "",
    val closed_on: String = "",
    val disposition: String = "",
    val observation: String = "",
    val baseline_nights: Int = 0,
    val baseline_rung: String = "",
    val differential: List<DifferentialItem> = emptyList(),
    val evidence_used: List<String> = emptyList(),
    val ruled_out: List<String> = emptyList(),
    val citations: List<Citation> = emptyList(),
    val unsupported_claims: Int = 0,
    val action: String = "",
    val escalation_criteria: List<String> = emptyList(),
    val confidence: String = "",
    val interruptions_used_this_week: Int = 0,
    val depth_used_this_episode: Int = 0,
)

@Serializable data class PipelineStage(
    val name: String,
    val status: String = "",
    val reason: String = "",
    val duration_ms: Int? = null,
    val detail_json: JsonObject = JsonObject(emptyMap()),
)

@Serializable data class EpisodeDetail(
    val summary: EpisodeSummary,
    val outcome: EpisodeOutcome? = null,
    val stages: List<PipelineStage> = emptyList(),
    val belief_history: List<JsonElement> = emptyList(),
    val interactions: List<InteractionView> = emptyList(),
    val measurements: List<MeasurementResult> = emptyList(),
    val citations: List<Citation> = emptyList(),
    val stripped_claims: List<String> = emptyList(),
)

@Serializable data class PendingInteraction(
    val kind: String,
    val episode_id: String = "",
    val question: Question? = null,
    val measurement: MeasurementRequest? = null,
    val draft_outcome: EpisodeOutcome? = null,
)

@Serializable data class ServiceSettings(
    val interruption_budget_per_week: Int = 0,
    val depth_budget_per_episode: Int = 0,
    val policy_cost_weight: Double = 0.0,
    val notify_channel: String = "",
    val llm_provider: String = "",
    val llm_model: String = "",
    val llm_base_url: String? = null,
    val bridge_host: String? = null,
)

@Serializable data class SubjectProfile(
    val subject_id: String,
    val age_years: Int? = null,
    val sex: String? = null,
    val known_vascular_disease: Boolean? = null,
    val menstruates: Boolean? = null,
    val rate_lowering_medicine: Boolean? = null,
    val notes_for_doctor: String? = null,
    val updated_at_utc: String? = null,
)

@Serializable data class DoctorRow(
    val name: String,
    val status: String = "",
    val detail: String = "",
)

@Serializable data class Handover(
    val subject_id: String = "",
    val generated_at_utc: String? = null,
    val text: String = "",
    val situation: List<String> = emptyList(),
    val background: List<String> = emptyList(),
    val assessment: List<String> = emptyList(),
    val recommendation: List<String> = emptyList(),
    val questions: List<String> = emptyList(),
    val what_this_is_not: List<String> = emptyList(),
)

@Serializable data class Urgency(
    val urgency: String? = null,
    val reason: String = "",
    val set_on: String? = null,
    val days_ago: Int? = null,
    val stale: Boolean = false,
    val cleared: Boolean = false,
)

@Serializable data class AuditEventView(
    val event_id: String,
    val timestamp_utc: String = "",
    val episode_id: String? = null,
    val step_index: Int? = null,
    val actor: String = "",
    val operation: String = "",
    val control_tier: String? = null,
    val tool_name: String? = null,
    val permission_decision: String? = null,
    val sources: List<String> = emptyList(),
    val validation_status: String? = null,
    val human_decision: String? = null,
    val safety_event: String = "none",
    val latency_ms: Int? = null,
    val hash_ok: Boolean = false,
)

@Serializable data class AuditPage(
    val events: List<AuditEventView> = emptyList(),
    val plain: JsonElement? = null,
    val count: Int = 0,
    val intact: Boolean = false,
    val first_bad_event: Int? = null,
    val permitted_tools: List<String> = emptyList(),
)

@Serializable data class Turn(
    val role: String = "",
    val text: String = "",
    // Stored as JSON strings in conversation_turns (schema.sql), parsed by the
    // screens that render citations. Strings, not lists, because that is the wire shape.
    val citations_json: String = "[]",
    val uncited_json: String = "[]",
)

@Serializable data class SayResult(
    val text: String = "",
    val citations: List<Citation> = emptyList(),
    val uncited: List<String> = emptyList(),
    val urgency: String? = null,
    val urgency_reason: String = "",
    val triggered_flags: List<String> = emptyList(),
    val guidance: List<String> = emptyList(),
    val asked_item_id: String? = null,
    val triage: JsonObject? = null,
    val turn_index: Int = 0,
    val at_turn_limit: Boolean = false,
    val refused: Boolean = false,
)

@Serializable data class Recorded(val status: String = "")
@Serializable data class Exported(val content: String = "")
@Serializable data class Ready(val ready: Boolean = false)
@Serializable data class Message(val message: String = "")
@Serializable data class JobResult(
    val job: String = "",
    val started: String = "",
    val result: JsonElement? = null,
)
