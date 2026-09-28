// Typed fetch client for the WHA FastAPI backend (src/wha/api/app.py).
// Mirrors src/wha/api/client.py's endpoint list and Pydantic model shapes 1:1, so a shape
// mismatch here is a real backend contract change, not a naming choice made in this file.

const DEFAULT_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8500'

export class ApiUnavailable extends Error {}
export class ApiHttpError extends Error {
  constructor(
    readonly status: number,
    readonly path: string,
    readonly responseBody: string,
  ) {
    super(`Request ${path} failed with HTTP ${status}: ${responseBody}`)
    this.name = 'ApiHttpError'
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${DEFAULT_BASE_URL}${path}`
  let response: Response
  try {
    response = await fetch(url, { cache: 'no-store', ...init })
  } catch (exc) {
    throw new ApiUnavailable(`Could not reach the application at ${url}: ${exc}`)
  }
  if (!response.ok) {
    const body = await response.text()
    throw new ApiHttpError(response.status, `${init?.method ?? 'GET'} ${path}`, body)
  }
  return response.json() as Promise<T>
}

async function requestOptional<T>(path: string): Promise<T | null> {
  try {
    return await request<T>(path)
  } catch (error) {
    if (error instanceof ApiHttpError && error.status === 404) return null
    throw error
  }
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
  detection_streak: { length: number; level: DetectionLevel; direction: 'rising' | 'steady' | 'falling' | null } | null
}

export interface NumericBounds {
  minimum: number | null
  maximum: number | null
  step?: number
}

export interface DashboardConfig {
  history_windows_days: number[]
  steps_average_days: number
  cause_combinations: number
  settings_bounds: {
    age_years: NumericBounds
    interruption_budget_per_week: NumericBounds
    depth_budget_per_episode: NumericBounds
    policy_cost_weight: NumericBounds
  }
}

export interface SystemConfig extends Record<string, unknown> {
  today: string
  configured_subject: string
  BASELINE_MIN_NIGHTS_PERSONAL: number
  SOURCE_LABEL_PREFIXES?: Record<string, string>
  SOURCE_LABEL_FALLBACK?: string
  EXTERNAL_SOURCE_PREFIX?: string
  ATTRIBUTION_NOTE?: string
  dashboard: DashboardConfig
}

export interface DashboardSummary {
  latest_sleep_hours: number | null
  latest_sleep_night: string | null
  latest_steps: number | null
  latest_steps_night: string | null
  steps_average: number | null
  steps_window_start: string
  steps_window_end: string
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
  quoted_span?: string | null
}

export interface EpisodeOutcome {
  schema_version: string; episode_id: string; subject_id: string; opened_on: string; closed_on: string
  disposition: Disposition; observation: string; baseline_nights: number; baseline_rung: BaselineRung
  differential: DifferentialItem[]; evidence_used: string[]; ruled_out: string[]; citations: Citation[]
  unsupported_claims: number; action: string; escalation_criteria: string[]
  confidence: 'low' | 'moderate' | 'high' | 'cannot_determine'
  interruptions_used_this_week: number; depth_used_this_episode: number
}

export interface MeasurementRequest {
  measurement_id: string
  kind: 'spot_resting_hr' | 'wear_tonight'
  instruction: string
  expires_at_utc: string
}

export interface MeasurementResult {
  measurement_id: string
  kind: string
  value: number | null
  observed_at_utc: string | null
  satisfied: boolean
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
  measurements: MeasurementResult[]; citations: Citation[]; stripped_claims: string[]
}

export interface Question {
  probe: { probe_id: string; target_cause: CauseId; answer_space: AnswerOption[]; evsi: number; interruption_cost: number; fallback_text: string }
  text: string; text_source: 'llm' | 'fallback'; options: AnswerOption[]; allows_free_text: boolean
}

export interface PendingInteraction {
  kind: 'question' | 'measurement' | 'review'; episode_id: string
  question: Question | null; measurement: MeasurementRequest | null
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
  rule: string; number: string; provenance: string; basis: string; minimum_age_years?: number | null
}

export interface Settings {
  interruption_budget_per_week: number; depth_budget_per_episode: number
  policy_cost_weight: number; notify_channel: 'none' | 'telegram'
  llm_provider: 'cassette' | 'ollama_native' | 'openai_compatible'
  llm_model: string; llm_base_url: string | null; bridge_host: string | null
}

export interface SettingsPatch extends Partial<Settings> {
  bridge_token?: string
  llm_api_key?: string
  telegram_token?: string
}

export interface SubjectProfile {
  subject_id: string
  age_years: number | null
  sex: 'female' | 'male' | null
  known_vascular_disease: boolean | null
  menstruates: boolean | null
  rate_lowering_medicine: boolean | null
  notes_for_doctor: string | null
  updated_at_utc: string | null
}

export type SubjectProfilePatch = Partial<Omit<SubjectProfile, 'subject_id' | 'updated_at_utc'>>

export interface PipelineNightRef {
  night_date: string
  level: DetectionLevel
  has_episode: boolean
  usable: boolean
}

export interface AuditFilter {
  episode_id?: string
  actor?: string
  operation?: string
  safety_event?: string
  since_utc?: string
  until_utc?: string
}

export interface AuditEventView {
  event_id: string
  timestamp_utc: string
  episode_id: string | null
  step_index: number | null
  actor: string
  operation: string
  control_tier: string | null
  tool_name: string | null
  permission_decision: string | null
  sources: string[]
  validation_status: string | null
  human_decision: string | null
  safety_event: string
  latency_ms: number | null
  hash_ok: boolean
}

export interface PlainAuditRecord {
  event_id: string
  timestamp_utc: string
  operation: string
  night: string | null
  sentences: string[]
  detail: Record<string, unknown>
}

export interface AuditQueryResponse {
  events: AuditEventView[]
  plain: PlainAuditRecord[]
  count: number
  intact: boolean
  first_bad_event: string | null
  permitted_tools: string[]
}

export interface HandoverSummary {
  text: string
  situation: string[]
  background: string[]
  assessment: string[]
  recommendation: string[]
  questions: string[]
  what_this_is_not: string[]
}

export interface ConnectionCheck {
  ok: boolean
  detail: string
  latency_ms: number | null
}

export interface UrgencyState {
  urgency: 'none' | 'same_day' | 'urgent' | null
  reason: string | null
  set_on: string | null
  days_ago: number | null
  stale: boolean
  cleared: boolean
}

export type KnowledgeProvenance = Record<string, {
  provenance: string
  profile_sourced: string
  has_unevidenced_number?: string
  note: string
}>

export interface KnowledgeProvenanceSummary {
  unevidenced_entries: number
  total_entries: number
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
  headline: {
    level: DetectionLevel; flagged: boolean; rung: BaselineRung | null
    primary_cause: CauseId | null; primary_probability: number | null
    sleep_hours: number | null; coverage_minutes: number
    questions_asked: number; sources_read: number
  }
  steps: PipelineStepView[]
}

// ── Client ─────────────────────────────────────────────────────────────────

function search(params: Record<string, string | undefined>): string {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined) query.set(key, value)
  }
  const encoded = query.toString()
  return encoded ? `?${encoded}` : ''
}

export interface HistoryNightFilters {
  levels?: DetectionLevel[]
  investigatedOnly?: boolean
}

export const api = {
  config: () => request<SystemConfig>('/config'),

  listSubjects: () => request<Subject[]>('/subjects'),

  deleteSubject: (subjectId: string) =>
    request<{ status: string; subject_id: string }>(`/subjects/${subjectId}`, { method: 'DELETE' }),

  getStatus: (subjectId: string) => request<SystemStatus>(`/subjects/${subjectId}/status`),

  getDashboardSummary: (subjectId: string) =>
    request<DashboardSummary>(`/subjects/${subjectId}/dashboard-summary`),

  listNights: (subjectId: string, days = 28, filters: HistoryNightFilters = {}) => {
    const params = new URLSearchParams({ days: String(days) })
    for (const level of filters.levels ?? []) params.append('level', level)
    if (filters.investigatedOnly) params.set('investigated_only', 'true')
    return request<NightRow[]>(`/subjects/${subjectId}/nights?${params.toString()}`)
  },

  getNightDetail: (subjectId: string, nightDate: string) =>
    requestOptional<NightDetail>(`/subjects/${subjectId}/nights/${nightDate}`),

  listPipelineNights: (subjectId: string, days = 60) =>
    request<PipelineNightRef[]>(`/subjects/${subjectId}/pipeline/nights?days=${days}`),

  getNightPipeline: (subjectId: string, nightDate: string) =>
    requestOptional<NightPipeline>(`/subjects/${subjectId}/nights/${nightDate}/pipeline`),

  listOxygenReadings: (subjectId: string, days = 7) =>
    request<OxygenReading[]>(`/subjects/${subjectId}/oxygen?days=${days}`),

  listEpisodes: (subjectId: string) => request<EpisodeSummary[]>(`/subjects/${subjectId}/episodes`),

  getEpisode: (episodeId: string) => requestOptional<EpisodeDetail>(`/episodes/${episodeId}`),

  getPending: (subjectId: string) => request<PendingInteraction | null>(`/subjects/${subjectId}/pending`),

  submitAnswer: (episodeId: string, body: { probe_id: string; option_id?: string | null; free_text?: string | null; declined?: boolean }) =>
    request<{ status: string }>(`/episodes/${episodeId}/answer`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    }),

  submitReview: (episodeId: string, body: { decision: string; edited_prose?: string | null; rationale?: string | null }) =>
    request<{ status: string }>(`/episodes/${episodeId}/review`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    }),

  getConversationSessions: (subjectId: string, limitTurns = 400, sinceNight?: string) =>
    request<ConversationSession[]>(
      `/subjects/${subjectId}/conversation/sessions${search({ limit_turns: String(limitTurns), since_night: sinceNight })}`,
    ),

  postMessage: (subjectId: string, text: string, episodeId?: string | null) =>
    request<{ text: string; urgency: string | null; citations: Citation[]; uncited: string[] }>(
      `/subjects/${subjectId}/conversation`,
      { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text, episode_id: episodeId ?? null }) },
    ),

  getUrgency: (subjectId: string) => request<UrgencyState>(`/subjects/${subjectId}/urgency`),

  acknowledgeUrgency: (subjectId: string) =>
    request<{ status: string }>(`/subjects/${subjectId}/urgency/acknowledged`, { method: 'POST' }),

  getHandover: (subjectId: string, episodeId?: string) =>
    request<HandoverSummary>(`/subjects/${subjectId}/handover${search({ episode_id: episodeId })}`),

  getAudit: (subjectId: string, filters: AuditFilter = {}, limit = 100, offset = 0) =>
    request<AuditQueryResponse>(
      `/subjects/${subjectId}/audit${search({ ...filters, limit: String(limit), offset: String(offset) })}`,
    ),

  exportAudit: (subjectId: string, filters: AuditFilter = {}) =>
    request<{ content: string }>(`/subjects/${subjectId}/audit/export${search({ ...filters })}`),

  getKnowledgeProvenance: () => request<KnowledgeProvenance>('/knowledge/provenance'),

  getKnowledgeProvenanceSummary: () =>
    request<KnowledgeProvenanceSummary>('/knowledge/provenance/summary'),

  getSafetyProvenance: () => request<SafetyRuleProvenance[]>('/knowledge/safety-provenance'),

  getSettings: () => request<Settings>('/settings'),

  updateSettings: (patch: SettingsPatch) =>
    request<Settings>('/settings', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(patch),
    }),

  getSubjectProfile: (subjectId: string) =>
    request<SubjectProfile>(`/subjects/${subjectId}/profile`),

  updateSubjectProfile: (subjectId: string, patch: SubjectProfilePatch) =>
    request<SubjectProfile>(`/subjects/${subjectId}/profile`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(patch),
    }),

  testComponent: (component: 'bridge' | 'llm' | 'telegram', overrides: Record<string, unknown> = {}) =>
    request<ConnectionCheck>(`/diagnostics/${component}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(overrides),
    }),
}
