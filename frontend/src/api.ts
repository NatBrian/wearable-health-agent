// Typed fetch client for the WHA FastAPI backend (src/wha/api/app.py).
// Mirrors src/wha/api/client.py's endpoint list and Pydantic model shapes 1:1, so a shape
// mismatch here is a real backend contract change, not a naming choice made in this file.

const DEFAULT_BASE_URL = 'http://127.0.0.1:8500'

export class ApiUnavailable extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${DEFAULT_BASE_URL}${path}`
  let response: Response
  try {
    response = await fetch(url, { cache: 'no-store', ...init })
  } catch (exc) {
    throw new ApiUnavailable(`Could not reach the application at ${url}: ${exc}`)
  }
  if (response.status === 404) return null as T
  if (!response.ok) {
    const body = await response.text()
    throw new ApiUnavailable(`${init?.method ?? 'GET'} ${path} failed: ${response.status} ${body}`)
  }
  return response.json() as Promise<T>
}

// ── Domain types (Pydantic models serialised as-is) ──────────────────────────

export type BaselineRung = 'COLD' | 'PRIOR_DOMINATED' | 'SHRINKING' | 'PERSONAL' | 'MATURE'
export type DetectionLevel = 'GREEN' | 'YELLOW' | 'RED' | 'NA'
export type EpisodeState = 'OPEN' | 'AWAITING_USER' | 'AWAITING_MEASUREMENT' | 'AWAITING_HUMAN_REVIEW' | 'CLOSED'
export type Disposition = 'EXPLAINED_BY_EVENT' | 'LIKELY_ILLNESS' | 'LIKELY_BENIGN' | 'ESCALATED' | 'UNRESOLVED' | 'INSUFFICIENT_DATA'
export type CauseId =
  | 'infection' | 'alcohol' | 'exertion' | 'sleep_restriction' | 'stress' | 'luteal'
  | 'vaccination' | 'travel' | 'medication' | 'recovery_tail' | 'sensor_artifact' | 'unexplained'

export const CAUSE_LABELS: Record<CauseId, string> = {
  infection: 'Infection', alcohol: 'Alcohol', exertion: 'Exertion',
  sleep_restriction: 'Sleep restriction', stress: 'Stress', luteal: 'Luteal phase',
  vaccination: 'Vaccination', travel: 'Travel', medication: 'Medication',
  recovery_tail: 'Recovery tail', sensor_artifact: 'Sensor artifact', unexplained: 'Unexplained',
}

export interface Subject {
  subject_id: string; label: string; source_kind: string; timezone: string
  usable_nights: number; rung: BaselineRung
}

export interface ComponentStatus {
  component: string; ok: boolean; detail: string; checked_at_utc: string
  severity: 'ok' | 'warn' | 'error'
}

export interface SystemStatus {
  components: ComponentStatus[]; last_ingest_utc: string | null; last_nightly_utc: string | null
  usable_nights: number; rung: BaselineRung; errors_24h: number
  quiet_nights_streak: number; unmeasured_recent_nights: number
}

export interface NightRow {
  night_date: string; rhr_bpm: number | null; centre_bpm: number | null
  band_lo: number | null; band_hi: number | null; deviation_bpm: number | null
  explained_bpm: number; residual_bpm: number | null; coverage_minutes: number
  usable: boolean; level: DetectionLevel; episode_id: string | null
  rhr_window_source: string; forecast_bpm: number | null; forecast_lo_bpm: number | null
  forecast_hi_bpm: number | null; forecast_status: string | null
  sleep_hours: number | null; steps_prev_day: number | null
}

export interface EpisodeSummary {
  episode_id: string; opened_on: string; closed_on: string | null; state: EpisodeState
  disposition: Disposition | null; night_span: [string, string]
  top_cause: CauseId | null; top_probability: number | null
}

export interface DifferentialItem {
  cause: CauseId; probability: number; supporting: string[]; contradicting: string[]; moved: number
}

export interface Citation {
  source_id: string; title: string; uri: string | null; passage: string; retrieval_score: number
}

export interface EpisodeOutcome {
  schema_version: string; episode_id: string; subject_id: string; opened_on: string; closed_on: string
  disposition: Disposition; observation: string; baseline_nights: number; baseline_rung: BaselineRung
  differential: DifferentialItem[]; evidence_used: string[]; ruled_out: string[]; citations: Citation[]
  unsupported_claims: number; action: string; escalation_criteria: string[]
  confidence: 'low' | 'moderate' | 'high' | 'cannot_determine'
  interruptions_used_this_week: number; depth_used_this_episode: number
}

export interface PipelineStage {
  name: string; status: 'RAN' | 'SKIPPED' | 'FAILED' | 'PENDING'; reason: string
  duration_ms: number | null; detail_json: Record<string, unknown>
}

export type BeliefState = { marginals: Record<CauseId, number>; p_illness: number; state_logprob: number[] }
export type BeliefHistoryEntry = [number, string, BeliefState]

export interface AnswerOption { option_id: string; label: string }

export interface InteractionView {
  id: string; probe_id: string; question_text: string; text_source: 'llm' | 'fallback'
  options: AnswerOption[]; evsi: number; interruption_cost: number
  rejected: [string, number][]; answer_option_id: string | null; free_text: string | null
  status: string; asked_at_utc: string; answered_at_utc: string | null
}

export interface EpisodeDetail {
  summary: EpisodeSummary; outcome: EpisodeOutcome | null; stages: PipelineStage[]
  belief_history: BeliefHistoryEntry[]; interactions: InteractionView[]
  measurements: unknown[]; citations: Citation[]; stripped_claims: string[]
}

export interface Question {
  probe: { probe_id: string; target_cause: CauseId; answer_space: AnswerOption[]; evsi: number; interruption_cost: number; fallback_text: string }
  text: string; text_source: 'llm' | 'fallback'; options: AnswerOption[]; allows_free_text: boolean
}

export interface PendingInteraction {
  kind: 'question' | 'measurement' | 'review'; episode_id: string
  question: Question | null; measurement: { instruction: string } | null
  draft_outcome: EpisodeOutcome | null
}

export interface ConversationTurn {
  id: string; episode_id: string | null; subject_id: string; seq: number
  role: 'user' | 'agent'; text: string; citations_json: string; uncited_json: string
  urgency: 'same_day' | 'urgent' | null; triggered_flags_json: string
  asked_item_id: string | null; presentation: string | null; created_at_utc: string
}

export interface ConversationSession { started_utc: string; turns: ConversationTurn[] }

export interface SafetyRuleProvenance {
  rule: string; number: string; provenance: string; basis: string
}

export interface Settings {
  interruption_budget_per_week: number; depth_budget_per_episode: number
  policy_cost_weight: number; notify_channel: 'none' | 'telegram'
  llm_provider: 'cassette' | 'ollama_native' | 'openai_compatible'
  llm_model: string; llm_base_url: string | null; bridge_host: string | null
}

export interface OxygenReading {
  ts_utc: string
  percentage: number
}

export interface NightDetail {
  row: NightRow
  features: { sleep_hours: number | null; steps_prev_day: number | null; exercise_end_offset_h: number | null }
  baseline: { centre_bpm: number; scale_bpm: number; usable_nights: number; rung: BaselineRung; shrink_weight: number }
  detection: { robust_z: number | null; reasons: string[] }
}

export interface PipelineStepView {
  step_id: string; ordinal: number; layer: 'deterministic' | 'agentic' | 'user' | 'safety'
  status: 'ran' | 'skipped' | 'not_applicable' | 'unrecorded'; reason: string
  headline_figure: string | null; occurred_utc: string | null
  inputs: Record<string, unknown>; outputs: Record<string, unknown>; sources: Citation[]
}

export interface NightPipeline {
  subject_id: string; night_date: string; episode_id: string | null
  headline: { level: DetectionLevel; flagged: boolean; primary_cause: CauseId | null; primary_probability: number | null }
  steps: PipelineStepView[]
}

// ── Client ─────────────────────────────────────────────────────────────────

export const api = {
  config: () => request<Record<string, unknown>>('/config'),

  listSubjects: () => request<Subject[]>('/subjects'),

  getStatus: (subjectId: string) => request<SystemStatus>(`/subjects/${subjectId}/status`),

  listNights: (subjectId: string, days = 28) =>
    request<NightRow[]>(`/subjects/${subjectId}/nights?days=${days}`),

  getNightDetail: (subjectId: string, nightDate: string) =>
    request<NightDetail>(`/subjects/${subjectId}/nights/${nightDate}`),

  getNightPipeline: (subjectId: string, nightDate: string) =>
    request<NightPipeline>(`/subjects/${subjectId}/nights/${nightDate}/pipeline`),

  listOxygenReadings: (subjectId: string, days = 7) =>
    request<OxygenReading[]>(`/subjects/${subjectId}/oxygen?days=${days}`),

  listEpisodes: (subjectId: string) => request<EpisodeSummary[]>(`/subjects/${subjectId}/episodes`),

  getEpisode: (episodeId: string) => request<EpisodeDetail>(`/episodes/${episodeId}`),

  getPending: (subjectId: string) => request<PendingInteraction | null>(`/subjects/${subjectId}/pending`),

  submitAnswer: (episodeId: string, body: { probe_id: string; option_id?: string | null; free_text?: string | null; declined?: boolean }) =>
    request<{ status: string }>(`/episodes/${episodeId}/answer`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    }),

  getConversationSessions: (subjectId: string, limitTurns = 200) =>
    request<ConversationSession[]>(`/subjects/${subjectId}/conversation/sessions?limit_turns=${limitTurns}`),

  postMessage: (subjectId: string, text: string, episodeId?: string | null) =>
    request<{ text: string; urgency: string | null; citations: Citation[]; uncited: string[] }>(
      `/subjects/${subjectId}/conversation`,
      { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text, episode_id: episodeId ?? null }) },
    ),

  getSafetyProvenance: () => request<SafetyRuleProvenance[]>('/knowledge/safety-provenance'),

  getSettings: () => request<Settings>('/settings'),

  updateSettings: (patch: Partial<Settings>) =>
    request<Settings>('/settings', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(patch),
    }),
}
