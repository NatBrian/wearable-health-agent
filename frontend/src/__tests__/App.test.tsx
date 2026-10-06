import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import App from '../App'
import { api, CAUSE_LABELS, type CauseId, type DashboardSummary, type EpisodeDetail, type EpisodeSummary, type NightDetail, type NightPipeline, type NightRow, type OxygenReading, type PendingInteraction, type PipelineNightRef, type SafetyRuleProvenance, type Subject, type SystemStatus } from '../api'
import { LEGACY_COPY } from '../content/legacyCopy'
import { ORIGINAL_VITE_INVENTORY as originalVite } from '../test/originalViteInventory'
import { PENDING_POLL_INTERVAL_MS } from '../useBackend'

const subjects: Subject[] = [
  { subject_id: 'subject-a', label: 'Participant A', source_kind: 'synthetic', timezone: 'Asia/Singapore', usable_nights: 0, rung: 'COLD' },
  { subject_id: 'subject-b', label: 'Participant B', source_kind: 'synthetic', timezone: 'Asia/Singapore', usable_nights: 0, rung: 'COLD' },
]

function setupApi(options: {
  configured?: string
  people?: Subject[]
  fail?: boolean
  pending?: PendingInteraction | null
  summary?: DashboardSummary
  status?: SystemStatus
  nights?: NightRow[]
  latestDetail?: NightDetail | null
  episodes?: EpisodeSummary[]
  episode?: EpisodeDetail | null
  pipelineRefs?: PipelineNightRef[]
  pipeline?: NightPipeline | null
  oxygen?: OxygenReading[]
  safetyRules?: SafetyRuleProvenance[]
} = {}) {
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
  vi.spyOn(api, 'getStatus').mockResolvedValue(options.status ?? {
    components: [], last_ingest_utc: null, last_nightly_utc: null, usable_nights: 0,
    rung: 'COLD', errors_24h: 0, quiet_nights_streak: 0, unmeasured_recent_nights: 0, detection_streak: null,
  })
  vi.spyOn(api, 'getDashboardSummary').mockResolvedValue(options.summary ?? {
    latest_sleep_hours: null, latest_sleep_night: null, latest_steps: null,
    latest_steps_night: null, steps_average: null,
    steps_window_start: '2026-09-22', steps_window_end: '2026-09-28',
  })
  vi.spyOn(api, 'getKnowledgeProvenanceSummary').mockResolvedValue({ unevidenced_entries: 2, total_entries: 4 })
  vi.spyOn(api, 'getSafetyProvenance').mockResolvedValue(options.safetyRules ?? [])
  vi.spyOn(api, 'getSettings').mockResolvedValue({
    interruption_budget_per_week: 3, depth_budget_per_episode: 3, policy_cost_weight: 0.2,
    notify_channel: 'none', llm_provider: 'cassette', llm_model: 'recorded',
    llm_base_url: null, bridge_host: null,
  })
  vi.spyOn(api, 'listNights').mockResolvedValue(options.nights ?? [])
  vi.spyOn(api, 'getNightDetail').mockResolvedValue(options.latestDetail ?? null)
  vi.spyOn(api, 'listEpisodes').mockResolvedValue(options.episodes ?? [])
  vi.spyOn(api, 'getEpisode').mockResolvedValue(options.episode ?? null)
  vi.spyOn(api, 'listPipelineNights').mockResolvedValue(options.pipelineRefs ?? [])
  vi.spyOn(api, 'getNightPipeline').mockResolvedValue(options.pipeline ?? null)
  vi.spyOn(api, 'getPending').mockResolvedValue(options.pending ?? null)
  vi.spyOn(api, 'getConversationSessions').mockResolvedValue([])
  vi.spyOn(api, 'listOxygenReadings').mockResolvedValue(options.oxygen ?? [])
}

const demoNights: NightRow[] = [
  {
    night_date: '2026-09-26', rhr_bpm: 64, centre_bpm: 61, band_lo: 58, band_hi: 64,
    deviation_bpm: 3, explained_bpm: 0, residual_bpm: 3, coverage_minutes: 420,
    usable: true, level: 'GREEN', episode_id: null, rhr_window_source: 'sleep',
    forecast_bpm: null, forecast_lo_bpm: null, forecast_hi_bpm: null, forecast_status: 'NOT_RUN',
    sleep_hours: 7.1, steps_prev_day: 5100,
  },
  {
    night_date: '2026-09-27', rhr_bpm: 66, centre_bpm: 61, band_lo: 58, band_hi: 64,
    deviation_bpm: 5, explained_bpm: 0, residual_bpm: 5, coverage_minutes: 430,
    usable: true, level: 'YELLOW', episode_id: 'episode-a', rhr_window_source: 'sleep',
    forecast_bpm: null, forecast_lo_bpm: null, forecast_hi_bpm: null, forecast_status: 'NOT_RUN',
    sleep_hours: 6.8, steps_prev_day: 6300,
  },
]
const demoSummary: DashboardSummary = {
  latest_sleep_hours: 6.8, latest_sleep_night: '2026-09-27', latest_steps: 6300,
  latest_steps_night: '2026-09-27', steps_average: 5700,
  steps_window_start: '2026-09-21', steps_window_end: '2026-09-27',
}
const demoLatestDetail: NightDetail = {
  row: demoNights[1],
  features: { sleep_hours: 6.8, steps_prev_day: 6300, exercise_end_offset_h: null },
  baseline: { centre_bpm: 61, scale_bpm: 3.2, usable_nights: 14, rung: 'PERSONAL', shrink_weight: 0.8 },
  detection: { robust_z: 1.56, reasons: ['above personal band'] },
}
const demoEpisodeSummary: EpisodeSummary = {
  episode_id: 'episode-a', opened_on: '2026-09-27', closed_on: null, state: 'OPEN',
  disposition: null, night_span: ['2026-09-27', '2026-09-27'], top_cause: 'infection', top_probability: 0.28,
}
const demoMarginals = Object.fromEntries(Object.keys(CAUSE_LABELS).map((cause, index) => [cause, (12 - index) / 100])) as Record<CauseId, number>
const demoEpisode = {
  summary: demoEpisodeSummary,
  outcome: null,
  stages: [],
  belief_history: [[0, '2026-09-27T00:00:00Z', { marginals: demoMarginals, p_illness: 0.28, state_logprob: [] }]],
  interactions: [], measurements: [], citations: [], stripped_claims: [],
} as unknown as EpisodeDetail
const demoStatus: SystemStatus = {
  components: [], last_ingest_utc: null, last_nightly_utc: '2026-09-28T00:00:00Z', usable_nights: 14,
  rung: 'PERSONAL', errors_24h: 0, quiet_nights_streak: 1, unmeasured_recent_nights: 0,
  detection_streak: { length: 2, level: 'YELLOW', direction: 'rising' },
}

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

beforeEach(() => {
  vi.spyOn(window, 'scrollTo').mockImplementation(() => undefined)
})

describe('dashboard subject boundary', () => {
  it('uses the configured subject instead of the first API row', async () => {
    setupApi()

    render(<App />)

    expect(await screen.findByRole('combobox', { name: 'Whose data' })).toHaveValue('subject-b')
    await waitFor(() => expect(api.getStatus).toHaveBeenCalledWith('subject-b'))
  })

  it('requests the API-configured history window for the Dashboard trend', async () => {
    setupApi({ people: [subjects[1]], nights: demoNights })

    render(<App />)

    await screen.findByRole('heading', { name: originalVite.shell.dashboardTitle })
    await waitFor(() => expect(api.listNights).toHaveBeenCalledWith('subject-b', 30))
  })

  it('returns each screen to its beginning when navigating', async () => {
    setupApi({ people: [subjects[1]] })
    render(<App />)
    fireEvent.click(await screen.findByText('What this is, and how the system works'))
    await screen.findByRole('heading', { name: 'What this is' })

    const scrollTo = window.scrollTo
    fireEvent.click(screen.getByRole('tab', { name: 'Today' }))
    await screen.findByText('Recent readings')
    expect(scrollTo).toHaveBeenCalledWith(0, 0)

    fireEvent.click(screen.getByRole('tab', { name: 'Overview' }))
    fireEvent.click(await screen.findByText('What this is, and how the system works'))
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

  it('shows the standing disclaimer, emergency guidance, explanations and evidence count on Dashboard', async () => {
    setupApi({ people: [subjects[1]] })

    render(<App />)

    expect(await screen.findByRole('heading', { name: 'What this system cannot do' })).toBeInTheDocument()
    fireEvent.click(screen.getByText('What this is, and how the system works'))
    expect(await screen.findByRole('heading', { name: 'What this is' })).toBeInTheDocument()
    expect(screen.getByText(LEGACY_COPY['home.emergency'])).toBeInTheDocument()
    expect(screen.getByText(LEGACY_COPY['home.cannot'])).toBeInTheDocument()
    expect(screen.getByText(LEGACY_COPY['home.judging'])).toBeInTheDocument()
    expect(await screen.findByText(/of the 4 causes and questions.*2 rest on/i)).toBeInTheDocument()
  })

  it('keeps emergency guidance on Overview and service status in Today', async () => {
    setupApi({ people: [subjects[1]] })

    render(<App />)

    const emergency = await screen.findByRole('region', { name: 'If you feel unwell now' })
    expect(emergency).toHaveTextContent(LEGACY_COPY['home.emergency'])
    fireEvent.click(screen.getByRole('tab', { name: 'Today' }))
    expect(await screen.findByRole('region', { name: 'System status' })).toBeInTheDocument()
  })

  it('keeps complete safety guidance visible in the Dashboard context', async () => {
    setupApi({ people: [subjects[1]] })

    render(<App />)

    const context = await screen.findByRole('region', { name: 'Dashboard safety guidance' })
    const emergency = within(context).getByRole('region', { name: 'If you feel unwell now' })
    const disclaimer = within(context).getByRole('region', { name: 'What this system cannot do' })

    expect(emergency).toBeVisible()
    expect(disclaimer).toBeVisible()
    expect(emergency).toHaveTextContent(LEGACY_COPY['home.emergency'])
    expect(disclaimer).toHaveTextContent(LEGACY_COPY['home.cannot'])
  })

  it('keeps metric selection accents and sleep value precision', async () => {
    const nights = demoNights.map((night, index) => index === demoNights.length - 1
      ? { ...night, sleep_hours: 10.25 }
      : night)
    setupApi({ people: [subjects[1]], status: demoStatus, nights })

    render(<App />)

    const restingHeartRate = await screen.findByRole('button', { name: /Resting HR/ })
    const sleep = screen.getByRole('button', { name: /Sleep/ })

    await waitFor(() => expect(sleep).toHaveTextContent('10.25 h'))
    expect(restingHeartRate).toHaveAttribute('aria-pressed', 'true')
    expect(restingHeartRate).toHaveStyle({ '--vital-accent': '#f59e0b' })

    fireEvent.click(sleep)
    expect(sleep).toHaveAttribute('aria-pressed', 'true')
    expect(sleep).toHaveStyle({ '--vital-accent': '#c5f041' })
    expect(restingHeartRate).toHaveAttribute('aria-pressed', 'false')
  })

  it('preserves the original sleep streak wording and severity color', async () => {
    const status: SystemStatus = {
      ...demoStatus,
      detection_streak: { length: 3, level: 'GREEN', direction: 'falling' },
    }
    setupApi({ people: [subjects[1]], status, nights: demoNights })

    render(<App />)

    const sleep = await screen.findByRole('button', { name: /Sleep/ })
    await waitFor(() => expect(sleep.querySelector('.vital-card__streak')).not.toBeNull())

    expect(sleep).toHaveTextContent('3 green nights')
    expect(sleep).toHaveTextContent('resolving')
    expect(sleep.querySelector('.vital-card__streak')).toHaveClass('vital-card__streak--green')
  })
})

describe('original Vite preservation contract', () => {
  it('keeps the Vital Agent identity, original titles, and three primary destinations', async () => {
    setupApi({ people: [subjects[1]] })
    render(<App />)

    expect(await screen.findByRole('heading', { name: originalVite.shell.dashboardTitle })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Vital Agent, health triage' })).toBeInTheDocument()
    expect(screen.getByText(originalVite.shell.tagline)).toBeInTheDocument()

    const navigation = within(screen.getByRole('navigation', { name: 'Main navigation' }))
    for (const destination of originalVite.shell.destinations) {
      expect(navigation.getByRole('button', { name: destination })).toBeInTheDocument()
    }
  })

  it('keeps the selected subject, baseline, and open-session summary in the sidebar', async () => {
    setupApi({ people: [subjects[1]], status: demoStatus, episodes: [demoEpisodeSummary] })
    render(<App />)

    const subjectSummary = await screen.findByLabelText(originalVite.shell.subjectSummary)
    expect(within(subjectSummary).getByText('Participant B')).toBeInTheDocument()
    await waitFor(() => expect(within(subjectSummary).getByText(/14 measured nights.*PERSONAL/)).toBeInTheDocument())
    expect(screen.getByRole('region', { name: originalVite.shell.sessionSummary })).toHaveTextContent(originalVite.shell.openSession)
  })

  it('keeps the last-closed session summary when no investigation is open', async () => {
    const closedEpisode: EpisodeSummary = {
      ...demoEpisodeSummary, state: 'CLOSED', closed_on: '2026-09-28', disposition: 'UNRESOLVED',
    }
    setupApi({ people: [subjects[1]], episodes: [closedEpisode] })
    render(<App />)

    expect(await screen.findByRole('region', { name: originalVite.shell.sessionSummary })).toHaveTextContent(originalVite.shell.lastClosedSession)
    expect(screen.getByRole('region', { name: originalVite.dashboard.episodeStatus })).toHaveTextContent(/Nothing is waiting/)
  })

  it('keeps the original Dashboard metric selection, chart, last-night details, and oxygen panel', async () => {
    setupApi({ people: [subjects[1]] })
    render(<App />)

    expect(await screen.findByRole('heading', { name: originalVite.shell.dashboardTitle })).toBeInTheDocument()
    for (const metric of originalVite.dashboard.metrics) {
      expect(screen.getByRole('button', { name: new RegExp(metric.replace(/[()]/g, '\\$&'), 'i') })).toBeInTheDocument()
      expect(screen.getByRole('img', { name: `${metric} sparkline` })).toBeInTheDocument()
    }
    expect(screen.getByRole('img', { name: originalVite.dashboard.chart })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: originalVite.dashboard.latestNight })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: originalVite.dashboard.differential })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: originalVite.dashboard.oxygenSpotChecks })).toBeInTheDocument()
  })

  it('uses backend readings for the selected chart, full differential, streak, and oxygen details', async () => {
    setupApi({
      people: [subjects[1]], status: demoStatus, nights: demoNights, summary: demoSummary,
      latestDetail: demoLatestDetail, episodes: [demoEpisodeSummary], episode: demoEpisode,
      oxygen: [{ ts_utc: '2026-09-28T01:00:00Z', percentage: 97 }],
    })
    render(<App />)

    await screen.findByRole('heading', { name: originalVite.shell.dashboardTitle })
    expect(await screen.findByText('2 yellow nights')).toBeInTheDocument()
    const restingHr = screen.getByRole('button', { name: /resting hr/i })
    expect(restingHr).toHaveAttribute('aria-pressed', 'true')
    expect(restingHr).toHaveTextContent('Base 61 bpm')
    expect(restingHr).toHaveTextContent('14 usable nights · PERSONAL')
    expect(restingHr).toHaveTextContent('Deviation +5 bpm · robust z 1.56')
    expect(screen.getByRole('img', { name: originalVite.dashboard.chart })).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Resting HR sparkline' })).toBeInTheDocument()
    expect(screen.getByText('2 yellow nights')).toBeInTheDocument()
    expect(screen.getByText(new RegExp(originalVite.dashboard.sleepStreak, 'i'))).toBeInTheDocument()
    expect(screen.getByText(originalVite.dashboard.differentialChange)).toBeInTheDocument()
    expect(screen.getByRole('region', { name: originalVite.dashboard.episodeStatus })).toHaveTextContent(/Investigation open/)

    fireEvent.click(screen.getByRole('button', { name: /sleep/i }))
    expect(screen.getByRole('button', { name: /sleep/i })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('img', { name: 'Sleep trend' })).toBeInTheDocument()

    expect(screen.getByRole('heading', { name: originalVite.dashboard.latestNight })).toBeInTheDocument()
    expect(screen.getByText('Usual range')).toBeInTheDocument()
    const differential = screen.getByRole('region', { name: originalVite.dashboard.differential })
    for (const label of Object.values(CAUSE_LABELS)) expect(within(differential).getByText(label)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: originalVite.dashboard.oxygenSpotChecks })).toBeInTheDocument()
    expect(screen.getByText('97%')).toBeInTheDocument()
    expect(screen.getByText(/Pulse oximeters can overestimate oxygen saturation/)).toBeInTheDocument()
  })

  it('distinguishes a failed night-history request from an empty dashboard', async () => {
    setupApi({ people: [subjects[1]] })
    vi.spyOn(api, 'listNights').mockRejectedValue(new Error('night service offline'))

    render(<App />)

    expect(await screen.findByRole('alert')).toHaveTextContent(/night service offline/)
    expect(screen.queryByText(/0 bpm/)).not.toBeInTheDocument()
    expect(screen.queryByText(/No nights are available/)).not.toBeInTheDocument()
  })

  it('keeps the original Pipeline overview and live safety provenance', async () => {
    setupApi({ people: [subjects[1]], status: demoStatus, episodes: [demoEpisodeSummary], episode: demoEpisode, safetyRules: [{ rule: 'example_rule', number: 'from API', provenance: 'ASSUMED', basis: 'Display only test source.' }] })
    render(<App />)

    await screen.findByRole('heading', { name: originalVite.shell.dashboardTitle })
    fireEvent.click(within(screen.getByRole('navigation', { name: 'Main navigation' })).getByRole('button', { name: 'Pipeline' }))
    expect(await screen.findByRole('heading', { name: originalVite.shell.pipelineTitle })).toBeInTheDocument()
    for (const layer of originalVite.pipeline.layers) {
      expect(screen.getByRole('heading', { name: layer })).toBeInTheDocument()
    }
    expect(await screen.findByText(/episode-a/)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: originalVite.pipeline.safetyRules })).toBeInTheDocument()
    expect(screen.getByText('Display only test source.')).toBeInTheDocument()
  })

  it('carries the selected History date into the Pipeline trace', async () => {
    setupApi({
      people: [subjects[1]], nights: demoNights,
      pipelineRefs: demoNights.map((night) => ({ night_date: night.night_date, level: night.level, has_episode: night.episode_id !== null, usable: night.usable })),
      pipeline: {
        subject_id: 'subject-b', night_date: '2026-09-27', episode_id: 'episode-a',
        headline: { level: 'YELLOW', flagged: true, rung: 'PERSONAL', primary_cause: 'infection', primary_probability: 0.28, sleep_hours: 6.8, coverage_minutes: 430, questions_asked: 0, sources_read: 0 },
        steps: [],
      },
    })
    render(<App />)

    await screen.findByRole('heading', { name: originalVite.shell.dashboardTitle })
    fireEvent.click(screen.getByRole('tab', { name: 'History' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Show me every step of that night' }))

    expect(await screen.findByRole('tab', { name: 'This night, step by step' })).toHaveAttribute('aria-selected', 'true')
    await waitFor(() => expect(api.getNightPipeline).toHaveBeenCalledWith('subject-b', '2026-09-27'))
    expect(screen.getByRole('combobox', { name: 'Which night' })).toHaveValue('2026-09-27')
  })

  it('keeps the original Settings section organization', async () => {
    setupApi({ people: [subjects[1]] })
    render(<App />)
    await screen.findByRole('heading', { name: originalVite.shell.dashboardTitle })
    fireEvent.click(within(screen.getByRole('navigation', { name: 'Main navigation' })).getByRole('button', { name: 'Settings' }))
    for (const section of originalVite.settings.sections) {
      expect(await screen.findByRole('button', { name: section })).toBeInTheDocument()
    }
  })

  it.each(originalVite.shell.destinations)('keeps global chat available from %s', async (destination) => {
    setupApi({ people: [subjects[1]] })
    render(<App />)

    await screen.findByRole('heading', { name: originalVite.shell.dashboardTitle })
    if (destination !== 'Dashboard') fireEvent.click(within(screen.getByRole('navigation', { name: 'Main navigation' })).getByRole('button', { name: destination }))

    fireEvent.click(screen.getByRole('button', { name: originalVite.chat.open }))
    expect(await screen.findByRole('complementary', { name: originalVite.chat.panel })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: originalVite.chat.close })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: originalVite.chat.close }))
    expect(screen.queryByRole('complementary', { name: originalVite.chat.panel })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: originalVite.chat.open })).toHaveAttribute('aria-expanded', 'false')
  })

  it.each(originalVite.shell.destinations)('keeps pending answers reachable from %s', async (destination) => {
    const pending: PendingInteraction = {
      kind: 'question', episode_id: 'episode-a', measurement: null, draft_outcome: null,
      question: {
        probe: {
          probe_id: 'probe-a', target_cause: 'infection',
          answer_space: [{ option_id: 'yes', label: 'Yes' }, { option_id: 'no', label: 'No' }],
          evsi: 0.2, interruption_cost: 0.1, fallback_text: 'Question',
        },
        text: 'Have you noticed a sore throat?', text_source: 'fallback',
        options: [{ option_id: 'yes', label: 'Yes' }, { option_id: 'no', label: 'No' }], allows_free_text: true,
      },
    }
    setupApi({ people: [subjects[1]], pending })
    const submit = vi.spyOn(api, 'submitAnswer').mockResolvedValue({ status: 'recorded' })
    render(<App />)

    await screen.findByRole('heading', { name: originalVite.shell.dashboardTitle })
    expect(await screen.findByRole('heading', { name: 'One question for you' })).toBeInTheDocument()
    if (destination !== 'Dashboard') fireEvent.click(within(screen.getByRole('navigation', { name: 'Main navigation' })).getByRole('button', { name: destination }))
    expect(screen.getByRole('complementary', { name: originalVite.chat.panel })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Yes' }))
    await waitFor(() => expect(submit).toHaveBeenCalledWith('episode-a', {
      probe_id: 'probe-a', option_id: 'yes', free_text: null,
    }))
  })

  it('opens chat for a newly polled question and respects closing it while that question remains pending', async () => {
    const pending: PendingInteraction = {
      kind: 'question', episode_id: 'episode-a', measurement: null, draft_outcome: null,
      question: {
        probe: {
          probe_id: 'probe-a', target_cause: 'infection',
          answer_space: [{ option_id: 'yes', label: 'Yes' }],
          evsi: 0.2, interruption_cost: 0.1, fallback_text: 'Question',
        },
        text: 'Did the agent ask you anything?', text_source: 'fallback',
        options: [{ option_id: 'yes', label: 'Yes' }], allows_free_text: false,
      },
    }
    setupApi({ people: [subjects[1]] })
    const getPending = vi.spyOn(api, 'getPending')
    getPending.mockReset().mockResolvedValueOnce(null).mockResolvedValue(pending)
    let pollPending: (() => void) | undefined
    vi.spyOn(window, 'setInterval').mockImplementation(((handler: TimerHandler, delay?: number) => {
      if (delay === PENDING_POLL_INTERVAL_MS && typeof handler === 'function') pollPending = handler as () => void
      return 1
    }) as typeof window.setInterval)
    vi.spyOn(window, 'clearInterval').mockImplementation(() => undefined)
    render(<App />)

    await screen.findByRole('heading', { name: originalVite.shell.dashboardTitle })
    await waitFor(() => expect(getPending).toHaveBeenCalledTimes(1))
    expect(screen.queryByRole('complementary', { name: originalVite.chat.panel })).not.toBeInTheDocument()
    expect(pollPending).toBeDefined()
    await act(async () => { pollPending?.() })
    expect(await screen.findByText('Did the agent ask you anything?')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: originalVite.chat.close }))
    expect(screen.queryByRole('complementary', { name: originalVite.chat.panel })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Open Agent Chat, reply waiting/ })).toBeInTheDocument()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Refresh' })).toBeEnabled())
    fireEvent.click(screen.getByRole('button', { name: 'Refresh' }))
    await waitFor(() => expect(getPending).toHaveBeenCalledTimes(3))
    expect(screen.queryByRole('complementary', { name: originalVite.chat.panel })).not.toBeInTheDocument()
  })
})
