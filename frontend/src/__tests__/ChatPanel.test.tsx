import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Subject, SystemConfig } from '../api'
import { ChatPanel } from '../components/ChatPanel'

const { api } = vi.hoisted(() => ({
  api: { getConversationSessions: vi.fn(), postMessage: vi.fn() },
}))

vi.mock('../api', async () => {
  const actual = await vi.importActual<typeof import('../api')>('../api')
  return { ...actual, api }
})

const subject: Subject = { subject_id: 'demo', label: 'Demo', source_kind: 'demo', timezone: 'UTC', usable_nights: 1, rung: 'PERSONAL' }
const config = {
  today: '2026-09-28', configured_subject: 'demo', BASELINE_MIN_NIGHTS_PERSONAL: 7,
  SOURCE_LABEL_PREFIXES: {}, SOURCE_LABEL_FALLBACK: 'source',
  CONVERSATION_MAX_TURNS: 10, ESCALATION_REPEAT_ROBUST_Z_RISE: 1, ESCALATION_REPEAT_NIGHTS: 2,
  TRIAGE_MAX_TURNS_BEFORE_ESCALATE: 3,
  dashboard: {
    history_windows_days: [30, 60, 90, 365], steps_average_days: 7, cause_combinations: 4096,
    settings_bounds: {
      age_years: { minimum: 0, maximum: 120 },
      interruption_budget_per_week: { minimum: 0, maximum: 20 },
      depth_budget_per_episode: { minimum: 0, maximum: 10 },
      policy_cost_weight: { minimum: 0, maximum: 1, step: 0.01 },
    },
  },
} as SystemConfig
const settings = {
  interruption_budget_per_week: 3, depth_budget_per_episode: 3, policy_cost_weight: 0.2,
  notify_channel: 'none', llm_provider: 'cassette', llm_model: 'demo', llm_base_url: null, bridge_host: null,
} as const

describe('ChatPanel', () => {
  afterEach(cleanup)
  beforeEach(() => {
    vi.clearAllMocks()
    api.getConversationSessions.mockResolvedValue([])
    api.postMessage.mockResolvedValue({ text: 'Saved', urgency: null, citations: [], uncited: [] })
  })

  it('does not turn a failed conversation request into an empty conversation', async () => {
    api.getConversationSessions.mockRejectedValueOnce(new Error('network unavailable'))
    render(<ChatPanel subject={subject} nightDate="2026-09-20" episodeId={null} pending={null} config={config} settings={settings} refreshAfterSend={vi.fn()} />)
    expect(await screen.findByText(/This is a fetch failure, not an empty conversation/)).toBeInTheDocument()
    expect(screen.queryByText(/No conversation has been recorded for this night/)).not.toBeInTheDocument()
  })

  it('retains a message only when sending it failed', async () => {
    render(<ChatPanel subject={subject} nightDate="2026-09-20" episodeId={null} pending={null} config={config} settings={settings} refreshAfterSend={vi.fn()} />)
    await screen.findByText(/No conversation has been recorded/)
    fireEvent.change(screen.getByLabelText('Say anything, or ask a question'), { target: { value: 'I feel unwell' } })
    api.postMessage.mockRejectedValueOnce(new Error('send failed'))
    fireEvent.click(screen.getByRole('button', { name: 'Send message' }))
    expect(await screen.findByText(/could not be sent/)).toBeInTheDocument()
    expect(screen.getByLabelText('Say anything, or ask a question')).toHaveValue('I feel unwell')
  })

  it('does not claim a successfully sent message stayed in the box when reload fails', async () => {
    api.getConversationSessions
      .mockResolvedValueOnce([])
      .mockRejectedValueOnce(new Error('reload failed'))
    const refreshAfterSend = vi.fn()
    render(<ChatPanel subject={subject} nightDate="2026-09-20" episodeId={null} pending={null} config={config} settings={settings} refreshAfterSend={refreshAfterSend} />)
    await screen.findByText(/No conversation has been recorded/)
    const input = screen.getByLabelText('Say anything, or ask a question')
    fireEvent.change(input, { target: { value: 'I feel unwell' } })
    fireEvent.click(screen.getByRole('button', { name: 'Send message' }))
    expect(await screen.findByText(/Your message was sent, but the refreshed conversation could not be loaded/)).toBeInTheDocument()
    await waitFor(() => expect(input).toHaveValue(''))
    expect(screen.queryByText(/still in the box/)).not.toBeInTheDocument()
    expect(refreshAfterSend).toHaveBeenCalledOnce()
  })

  it('shows live conversation, notification, and repeat-notice limits', async () => {
    render(<ChatPanel subject={subject} nightDate="2026-09-20" episodeId={null} pending={null} config={config} settings={settings} refreshAfterSend={vi.fn()} />)
    await screen.findByText(/No conversation has been recorded/)
    fireEvent.click(screen.getByText('Conversation and notification limits'))
    expect(screen.getByText(/10 back-and-forth exchanges/)).toBeInTheDocument()
    expect(screen.getByText(/3 unsolicited interruptions/)).toBeInTheDocument()
    expect(screen.getByText(/1 robust deviations/)).toBeInTheDocument()
    expect(screen.getByText(/2 nights/)).toBeInTheDocument()
    expect(screen.getByText(/If the system cannot collect enough information/).textContent).toContain('within 3 replies')
  })
})
