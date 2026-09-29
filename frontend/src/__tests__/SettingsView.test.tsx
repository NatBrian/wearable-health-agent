import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { BackendData } from '../useBackend'
import type { Settings, Subject, SystemConfig, SubjectProfile } from '../api'
import { SettingsView } from '../views/SettingsView'

const { api } = vi.hoisted(() => ({
  api: {
    getSubjectProfile: vi.fn(), updateSubjectProfile: vi.fn(), updateSettings: vi.fn(),
    testComponent: vi.fn(), deleteSubject: vi.fn(),
  },
}))

vi.mock('../api', async () => {
  const actual = await vi.importActual<typeof import('../api')>('../api')
  return { ...actual, api }
})

const settings: Settings = {
  interruption_budget_per_week: 2, depth_budget_per_episode: 3, policy_cost_weight: 0.3,
  notify_channel: 'none', llm_provider: 'cassette', llm_model: 'recorded', llm_base_url: null, bridge_host: null,
}
const profile: SubjectProfile = {
  subject_id: 'demo', age_years: null, sex: null, known_vascular_disease: null,
  menstruates: null, rate_lowering_medicine: null, notes_for_doctor: null, updated_at_utc: null,
}
const config = {
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
} as SystemConfig
const subject = (subject_id: string): Subject => ({ subject_id, label: subject_id, source_kind: 'demo', timezone: 'UTC', usable_nights: 0, rung: 'COLD' })
const data = {
  settings,
  safetyRules: [{
    rule: 'marburg_heart_score', number: 'applies to chest pain; minimum age 35',
    provenance: 'CITED', basis: 'Bösner et al., CMAJ', minimum_age_years: 35,
  }],
  errors: {}, refresh: vi.fn(),
} as unknown as BackendData

describe('SettingsView', () => {
  afterEach(cleanup)

  beforeEach(() => {
    vi.clearAllMocks()
    api.getSubjectProfile.mockResolvedValue(profile)
    api.updateSubjectProfile.mockResolvedValue(profile)
    api.updateSettings.mockResolvedValue(settings)
    api.testComponent.mockResolvedValue({ ok: true, detail: 'Connection succeeded', latency_ms: 4 })
    api.deleteSubject.mockResolvedValue({ status: 'deleted', subject_id: 'demo' })
  })

  it('keeps every profile fact, explains what reads it, and saves blank age as unset', async () => {
    render(<SettingsView subject={subject('demo')} config={config} data={data} onDeleted={vi.fn()} />)
    expect(await screen.findByLabelText('Your age')).toBeInTheDocument()
    expect(screen.getByText(/tested only on people aged 35 and over/)).toBeInTheDocument()
    expect(screen.getByLabelText('Sex')).toBeInTheDocument()
    expect(screen.getByLabelText('I have a known heart or vascular condition')).toBeInTheDocument()
    expect(screen.getByLabelText('I menstruate')).toBeInTheDocument()
    expect(screen.getByLabelText('I take medicine that slows my heart rate')).toBeInTheDocument()
    expect(screen.getByLabelText('Anything you want a doctor to see')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Save these' }))
    await waitFor(() => expect(api.updateSubjectProfile).toHaveBeenCalledWith('demo', expect.objectContaining({ age_years: null, sex: null })))
    expect(screen.getByText('Goes into the summary for your doctor and into no AI prompt. Information for a doctor is not information for the model.')).toBeInTheDocument()
  })

  it('tests unsaved settings without showing or saving secrets', async () => {
    render(<SettingsView subject={subject('demo')} config={config} data={data} onDeleted={vi.fn()} />)
    await screen.findByLabelText('Your age')
    fireEvent.change(screen.getByLabelText("Your phone's address on this network"), { target: { value: 'http://watch.local' } })
    fireEvent.change(screen.getByLabelText('Phone access token'), { target: { value: 'private-token' } })
    fireEvent.click(screen.getByRole('button', { name: 'Test the connection to my phone' }))
    await waitFor(() => expect(api.testComponent).toHaveBeenCalledWith('bridge', { bridge_host: 'http://watch.local', bridge_token: 'private-token' }))
    expect(screen.queryByText('private-token')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Save all settings' }))
    await waitFor(() => expect(api.updateSettings).toHaveBeenCalled())
    expect(api.updateSettings.mock.calls[0][0]).toMatchObject({ bridge_host: 'http://watch.local' })
    expect(api.updateSettings.mock.calls[0][0]).toMatchObject({ bridge_token: 'private-token' })
    expect(screen.getByText(/Connection secrets saved; their values are not returned\./)).toBeInTheDocument()
    expect(screen.getByText(/Connection secrets saved; their values are not returned\./)).not.toHaveTextContent('private-token')
  })

  it('keeps every original settings section and exposes its controls in place', async () => {
    render(<SettingsView subject={subject('demo')} config={config} data={data} onDeleted={vi.fn()} />)
    await screen.findByLabelText('Your age')
    const navigation = screen.getByRole('navigation', { name: 'Settings sections' })
    for (const name of ['Device & Data', 'Agent Behavior', 'Model & RAG', 'Privacy']) {
      expect(within(navigation).getByRole('button', { name })).toBeInTheDocument()
    }

    fireEvent.click(within(navigation).getByRole('button', { name: 'Agent Behavior' }))
    expect(screen.getByLabelText(/Where questions should reach you/)).toBeVisible()
    expect(screen.getByRole('button', { name: 'Check Telegram bot connection' })).toBeVisible()
    const weekly = screen.getByLabelText(/Most questions in a week/)
    expect(weekly).toHaveAttribute('min', '0')
    expect(weekly).toHaveAttribute('max', '20')
    const depth = screen.getByLabelText(/Most questions in one investigation/)
    expect(depth).toHaveAttribute('min', '0')
    expect(depth).toHaveAttribute('max', '10')
    fireEvent.click(within(navigation).getByRole('button', { name: 'Model & RAG' }))
    expect(screen.getByLabelText(/Which kind of model/)).toBeVisible()
    expect(screen.getByLabelText(/Key for that service/)).toBeVisible()
    expect(screen.getByText(/verbatim span from a retrieved passage/)).toBeVisible()
    fireEvent.click(within(navigation).getByRole('button', { name: 'Privacy' }))
    expect(screen.getByRole('heading', { name: 'Where your data goes' })).toBeVisible()
    expect(screen.getByLabelText('Type the name of the person to delete')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Save all settings' })).toBeVisible()
  })

  it('retains changed settings after a failed save from the selected section', async () => {
    api.updateSettings.mockRejectedValue(new Error('save unavailable'))
    render(<SettingsView subject={subject('demo')} config={config} data={data} onDeleted={vi.fn()} />)
    const navigation = screen.getByRole('navigation', { name: 'Settings sections' })
    fireEvent.click(within(navigation).getByRole('button', { name: 'Agent Behavior' }))
    const weekly = await screen.findByLabelText(/Most questions in a week/)
    fireEvent.change(weekly, { target: { value: '5' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save all settings' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('save unavailable')
    expect(weekly).toHaveValue(5)
  })

  it('reports fields that changed from their loaded values after the API accepts them', async () => {
    const refresh = vi.fn()
    const accepted = { ...settings, interruption_budget_per_week: 5 }
    api.updateSettings.mockResolvedValue(accepted)
    render(<SettingsView subject={subject('demo')} config={config} data={{ ...data, refresh }} onDeleted={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: 'Agent Behavior' }))
    fireEvent.change(await screen.findByLabelText(/Most questions in a week/), { target: { value: '5' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save all settings' }))

    expect(await screen.findByRole('status')).toHaveTextContent('Saved. Changed: Weekly question limit.')
    expect(screen.getByRole('status')).not.toHaveTextContent('No setting values changed.')
    expect(api.updateSettings).toHaveBeenCalledWith(expect.objectContaining({ interruption_budget_per_week: 5 }))
    expect(refresh).toHaveBeenCalledOnce()
  })

  it('requires the exact disposable subject id before deletion and never offers deletion for me', async () => {
    const onDeleted = vi.fn()
    const { rerender } = render(<SettingsView subject={subject('me')} config={config} data={data} onDeleted={onDeleted} />)
    await screen.findByLabelText('Your age')
    expect(screen.queryByRole('heading', { name: 'Delete everything' })).not.toBeInTheDocument()
    rerender(<SettingsView subject={subject('demo')} config={config} data={data} onDeleted={onDeleted} />)
    fireEvent.click(screen.getByRole('button', { name: 'Privacy' }))
    const confirm = await screen.findByLabelText('Type the name of the person to delete')
    fireEvent.change(confirm, { target: { value: 'wrong' } })
    fireEvent.click(screen.getByRole('button', { name: 'Delete everything about this person' }))
    expect(api.deleteSubject).not.toHaveBeenCalled()
    fireEvent.change(confirm, { target: { value: 'demo' } })
    fireEvent.click(screen.getByRole('button', { name: 'Delete everything about this person' }))
    await waitFor(() => expect(api.deleteSubject).toHaveBeenCalledWith('demo'))
    expect(onDeleted).toHaveBeenCalledOnce()
  })
})
