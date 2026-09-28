import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import App from '../App'
import { api, type Subject } from '../api'
import { LEGACY_COPY } from '../content/legacyCopy'

const subjects: Subject[] = [
  { subject_id: 'subject-a', label: 'Participant A', source_kind: 'synthetic', timezone: 'Asia/Singapore', usable_nights: 0, rung: 'COLD' },
  { subject_id: 'subject-b', label: 'Participant B', source_kind: 'synthetic', timezone: 'Asia/Singapore', usable_nights: 0, rung: 'COLD' },
]

function setupApi(options: { configured?: string; people?: Subject[]; fail?: boolean } = {}) {
  vi.spyOn(api, 'config').mockResolvedValue({
    today: '2026-09-28',
    configured_subject: options.configured ?? 'subject-b',
    BASELINE_MIN_NIGHTS_PERSONAL: 7,
    dashboard: {
      history_windows_days: [30, 60, 90, 365],
      steps_average_days: 7,
      cause_combinations: 4096,
      settings_bounds: {
        age_years: { minimum: 0, maximum: 120 },
        interruption_budget_per_week: { minimum: 0, maximum: 20 },
        depth_budget_per_episode: { minimum: 0, maximum: 10 },
        policy_cost_weight: { minimum: 0, maximum: 1, step: 0.01 },
      },
    },
  })
  vi.spyOn(api, 'listSubjects').mockImplementation(() =>
    options.fail ? Promise.reject(new Error('connection unavailable')) : Promise.resolve(options.people ?? subjects),
  )
  vi.spyOn(api, 'getStatus').mockResolvedValue({
    components: [], last_ingest_utc: null, last_nightly_utc: null, usable_nights: 0,
    rung: 'COLD', errors_24h: 0, quiet_nights_streak: 0, unmeasured_recent_nights: 0,
  })
  vi.spyOn(api, 'getDashboardSummary').mockResolvedValue({
    latest_sleep_hours: null, latest_sleep_night: null, latest_steps: null,
    latest_steps_night: null, steps_average: null,
    steps_window_start: '2026-09-22', steps_window_end: '2026-09-28',
  })
  vi.spyOn(api, 'getKnowledgeProvenanceSummary').mockResolvedValue({ unevidenced_entries: 2, total_entries: 4 })
  vi.spyOn(api, 'getSafetyProvenance').mockResolvedValue([])
  vi.spyOn(api, 'getSettings').mockResolvedValue({
    interruption_budget_per_week: 3, depth_budget_per_episode: 3, policy_cost_weight: 0.2,
    notify_channel: 'none', llm_provider: 'cassette', llm_model: 'recorded',
    llm_base_url: null, bridge_host: null,
  })
  vi.spyOn(api, 'listNights').mockResolvedValue([])
  vi.spyOn(api, 'listEpisodes').mockResolvedValue([])
  vi.spyOn(api, 'getPending').mockResolvedValue(null)
  vi.spyOn(api, 'getConversationSessions').mockResolvedValue([])
  vi.spyOn(api, 'listOxygenReadings').mockResolvedValue([])
}

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

describe('dashboard subject boundary', () => {
  it('uses the configured subject instead of the first API row', async () => {
    setupApi()

    render(<App />)

    expect(await screen.findByText('Participant B')).toBeInTheDocument()
    await waitFor(() => expect(api.getStatus).toHaveBeenCalledWith('subject-b'))
  })

  it('returns each screen to its beginning when navigating', async () => {
    setupApi({ people: [subjects[1]] })
    render(<App />)
    await screen.findByRole('heading', { name: 'What this is' })

    const scrollTo = vi.spyOn(window, 'scrollTo').mockImplementation(() => undefined)
    fireEvent.click(screen.getAllByRole('button', { name: 'Today' })[0])
    await screen.findByText('Recent readings')
    expect(scrollTo).toHaveBeenCalledWith(0, 0)

    fireEvent.click(screen.getAllByRole('button', { name: 'Home' })[0])
    await screen.findByRole('heading', { name: 'What this is' })
    expect(scrollTo).toHaveBeenCalledTimes(2)
  })

  it('asks for a choice when several subjects exist without a usable configured subject', async () => {
    setupApi({ configured: 'not-listed' })

    render(<App />)

    expect(await screen.findByRole('combobox', { name: /whose data/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Participant A' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Participant B' })).toBeInTheDocument()
  })

  it('distinguishes an empty subject list from a backend failure', async () => {
    setupApi({ people: [] })
    const { unmount } = render(<App />)
    expect(await screen.findByText(/there is nobody to show yet/i)).toBeInTheDocument()

    unmount()
    vi.restoreAllMocks()
    setupApi({ fail: true })
    render(<App />)
    expect(await screen.findByText(/could not reach the application/i)).toBeInTheDocument()
  })

  it('shows the standing disclaimer, emergency guidance, explanations and evidence count on Home', async () => {
    setupApi({ people: [subjects[1]] })

    render(<App />)

    expect(await screen.findByRole('heading', { name: 'What this is' })).toBeInTheDocument()
    expect(screen.getByText(LEGACY_COPY['home.emergency'])).toBeInTheDocument()
    expect(screen.getByText(LEGACY_COPY['home.cannot'])).toBeInTheDocument()
    expect(screen.getByText(LEGACY_COPY['home.judging'])).toBeInTheDocument()
    expect(await screen.findByText(/of the 4 causes and questions.*2 rest on/i)).toBeInTheDocument()
  })

  it('puts emergency guidance before the status panel on Home', async () => {
    setupApi({ people: [subjects[1]] })

    render(<App />)

    const emergency = await screen.findByRole('region', { name: 'If you feel unwell now' })
    const status = await screen.findByRole('region', { name: 'System status' })
    expect(emergency.compareDocumentPosition(status) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(0)
  })
})
