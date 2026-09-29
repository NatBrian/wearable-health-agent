import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { api, type AuditQueryResponse, type EpisodeDetail, type EpisodeSummary, type NightPipeline, type PipelineNightRef, type Subject, type SystemConfig } from '../api'
import type { BackendData } from '../useBackend'
import { RecordView } from '../views/RecordView'

const subject: Subject = { subject_id: 'demo', label: 'Demo', source_kind: 'synthetic', timezone: 'UTC', usable_nights: 2, rung: 'PERSONAL' }
const config: SystemConfig = {
  today: '2026-09-28', configured_subject: 'demo', BASELINE_MIN_NIGHTS_PERSONAL: 7,
  dashboard: {
    history_windows_days: [30, 60, 90, 365], steps_average_days: 7, cause_combinations: 4096,
    settings_bounds: {
      age_years: { minimum: 0, maximum: 120 },
      interruption_budget_per_week: { minimum: 0, maximum: 20 },
      depth_budget_per_episode: { minimum: 0, maximum: 10 },
      policy_cost_weight: { minimum: 0, maximum: 1, step: 0.01 },
    },
  },
}
const episode: EpisodeSummary = {
  episode_id: 'episode-a', opened_on: '2026-09-27', closed_on: null, state: 'OPEN',
  disposition: null, night_span: ['2026-09-27', '2026-09-27'], top_cause: null, top_probability: null,
}
const detail: EpisodeDetail = {
  summary: episode, outcome: null, stages: [{ name: 'investigate', status: 'RAN', reason: 'Evidence was gathered.', duration_ms: null, detail_json: {} }],
  belief_history: [], interactions: [], measurements: [], citations: [], stripped_claims: [],
}
const data = {
  status: null, summary: null, provenance: null, knowledgeProvenance: null, nights: [], latestDetail: null,
  episodes: [episode], activeEpisode: detail, pending: null, sessions: [], safetyRules: [
    { rule: 'example_rule', number: 'from API', provenance: 'CITED', basis: 'Named published source and population scope.' },
  ], settings: null, oxygenReadings: [], errors: {}, loading: false, error: null, refresh: vi.fn(),
} as unknown as BackendData
const refs: PipelineNightRef[] = [{ night_date: '2026-09-27', level: 'YELLOW', has_episode: true, usable: true }]
const pipeline: NightPipeline = {
  subject_id: 'demo', night_date: '2026-09-27', episode_id: 'episode-a',
  headline: { level: 'YELLOW', flagged: true, rung: 'PERSONAL', primary_cause: null, primary_probability: null, sleep_hours: 7, coverage_minutes: 420, questions_asked: 0, sources_read: 0 },
  steps: [],
}
const audit: AuditQueryResponse = {
  events: [{
    event_id: 'event-a', timestamp_utc: '2026-09-27T01:00:00Z', episode_id: 'episode-a', step_index: 2,
    actor: 'agent', operation: 'nightly', control_tier: 'deterministic', tool_name: null,
    permission_decision: null, sources: ['source-a'], validation_status: 'valid', human_decision: null,
    safety_event: '', latency_ms: 12, hash_ok: true,
  }],
  plain: [], count: 1, intact: false, first_bad_event: 'event-a', permitted_tools: ['read_episode'],
}
const integrityCases: [string, AuditQueryResponse, string][] = [
  ['an intact record', { ...audit, intact: true }, 'No. The record is intact.'],
  ['an empty record', { ...audit, events: [], plain: [], count: 0, intact: true }, 'Nothing has been recorded yet.'],
]

function mockRecordApi(auditResult = audit) {
  vi.spyOn(api, 'listPipelineNights').mockResolvedValue(refs)
  vi.spyOn(api, 'getNightPipeline').mockResolvedValue(pipeline)
  vi.spyOn(api, 'getAudit').mockResolvedValue(auditResult)
  vi.spyOn(api, 'getConversationSessions').mockResolvedValue([{
    started_utc: '2026-09-27T00:30:00Z',
    turns: [{
      id: 'turn-a', episode_id: 'episode-a', subject_id: 'demo', seq: 1, role: 'agent',
      text: 'This reply contains a sourced statement.',
      citations_json: JSON.stringify([{ source_id: 'source-a', title: 'Example paper', uri: null, passage: 'The source passage stays visible here.', retrieval_score: 0.8, quoted_span: 'The source passage' }]),
      uncited_json: '[]', urgency: null, triggered_flags_json: '[]', asked_item_id: null,
      presentation: null, created_at_utc: '2026-09-27T01:00:00Z',
    }],
  }])
}

afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals() })

describe('Pipeline destination', () => {
  it('keeps the three original architecture layers, active stage, and API rule provenance', async () => {
    mockRecordApi()
    render(<RecordView subject={subject} config={config} data={data} initialNight={null} onNavigate={() => undefined} />)

    expect(await screen.findByRole('heading', { name: 'Detection layer' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Reasoning layer' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Retrieval layer' })).toBeInTheDocument()
    expect(screen.getByText('Evidence was gathered.')).toBeInTheDocument()
    expect(screen.getByText('Named published source and population scope.')).toBeInTheDocument()
  })

  it.each([
    ['CITED', 'cited'],
    ['ASSUMED', 'assumed'],
    ['DERIVED', 'derived'],
  ])('color-codes %s safety-rule provenance', async (provenance, tone) => {
    mockRecordApi()
    const safetyRules = [{ ...data.safetyRules[0], provenance }]
    render(<RecordView subject={subject} config={config} data={{ ...data, safetyRules }} initialNight={null} onNavigate={() => undefined} />)

    expect(await screen.findByText(provenance)).toHaveClass(`provenance-badge--${tone}`)
  })

  it('opens the selected night in the trace and keeps its date in the selector', async () => {
    mockRecordApi()
    render(<RecordView subject={subject} config={config} data={data} initialNight="2026-09-27" onNavigate={() => undefined} />)

    expect(await screen.findByRole('tab', { name: 'This night, step by step' })).toHaveAttribute('aria-selected', 'true')
    await waitFor(() => expect(api.getNightPipeline).toHaveBeenCalledWith('demo', '2026-09-27'))
    expect(screen.getByRole('combobox', { name: 'Which night' })).toHaveValue('2026-09-27')
  })

  it.each(integrityCases)('distinguishes %s from a broken record', async (_label, result, expectedHeading) => {
    mockRecordApi(result)
    render(<RecordView subject={subject} config={config} data={data} initialNight={null} onNavigate={() => undefined} />)
    fireEvent.click(screen.getByRole('tab', { name: 'Everything the system did' }))

    expect(await screen.findByRole('heading', { name: expectedHeading })).toBeInTheDocument()
  })

  it('shows broken integrity, archived citations, and filtered audit export', async () => {
    mockRecordApi()
    const exportAudit = vi.spyOn(api, 'exportAudit').mockResolvedValue({ content: '{"event_id":"event-a"}\n' })
    vi.stubGlobal('URL', { createObjectURL: vi.fn(() => 'blob:record'), revokeObjectURL: vi.fn() })
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined)
    render(<RecordView subject={subject} config={config} data={data} initialNight={null} onNavigate={() => undefined} />)

    fireEvent.click(screen.getByRole('tab', { name: 'Everything the system did' }))
    expect(await screen.findByRole('heading', { name: 'The record has been altered.' })).toBeInTheDocument()
    expect(await screen.findByText('Conversations')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /Example paper/ }))
    expect(screen.getByText('The source passage stays visible here.')).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Who did it'), { target: { value: 'agent' } })
    await waitFor(() => expect(api.getAudit).toHaveBeenLastCalledWith('demo', expect.objectContaining({ actor: 'agent' }), 100, 0))
    fireEvent.click(screen.getByRole('button', { name: 'Prepare a copy of the record' }))
    await waitFor(() => expect(exportAudit).toHaveBeenCalledWith('demo', expect.objectContaining({ actor: 'agent' })))
  })
})
