import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
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
    fireEvent.click(screen.getByRole('button', { name: 'Save all of the above' }))
    await waitFor(() => expect(api.updateSettings).toHaveBeenCalled())
    expect(api.updateSettings.mock.calls[0][0]).toMatchObject({ bridge_host: 'http://watch.local' })
    expect(api.updateSettings.mock.calls[0][0]).toMatchObject({ bridge_token: 'private-token' })
  })

  it('requires the exact disposable subject id before deletion and never offers deletion for me', async () => {
    const onDeleted = vi.fn()
    const { rerender } = render(<SettingsView subject={subject('me')} config={config} data={data} onDeleted={onDeleted} />)
    await screen.findByLabelText('Your age')
    expect(screen.queryByRole('heading', { name: 'Delete everything' })).not.toBeInTheDocument()
    rerender(<SettingsView subject={subject('demo')} config={config} data={data} onDeleted={onDeleted} />)
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
