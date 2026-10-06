import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { api, type NightRow, type Subject, type SystemConfig } from '../api'
import { HistoryView } from '../views/HistoryView'

const subject: Subject = { subject_id: 'sim', label: 'Demo', source_kind: 'synthetic', timezone: 'UTC', usable_nights: 1, rung: 'PERSONAL' }
const config: SystemConfig = {
  today: '2026-09-28', configured_subject: 'sim', BASELINE_MIN_NIGHTS_PERSONAL: 7,
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
const night: NightRow = {
  night_date: '2026-09-27', rhr_bpm: 64, centre_bpm: 60, band_lo: 55, band_hi: 65,
  deviation_bpm: 4, explained_bpm: 0, residual_bpm: 4, coverage_minutes: 380,
  usable: true, level: 'YELLOW', episode_id: null, rhr_window_source: 'sleep',
  forecast_bpm: null, forecast_lo_bpm: null, forecast_hi_bpm: null, forecast_status: null,
  sleep_hours: 7.2, steps_prev_day: 4200,
}

afterEach(() => { cleanup(); vi.restoreAllMocks() })

describe('History filters and trace navigation', () => {
  it('requests table filters from the API and can open a selected night on The record', async () => {
    const listNights = vi.spyOn(api, 'listNights').mockResolvedValue([night])
    vi.spyOn(api, 'listEpisodes').mockResolvedValue([])
    vi.spyOn(api, 'getNightDetail').mockResolvedValue(null)
    const onOpenRecord = vi.fn()
    render(<HistoryView subject={subject} config={config} initialNight="2026-09-27" onOpenRecord={onOpenRecord} />)

    await waitFor(() => expect(listNights).toHaveBeenCalledWith('sim', 60))
    fireEvent.click(screen.getByRole('checkbox', { name: 'Only nights that were looked into' }))
    await waitFor(() => expect(listNights).toHaveBeenCalledWith('sim', 60, { levels: [], investigatedOnly: true }))
  })

  it('reveals the full recorded fields and opens the selected night trace', async () => {
    vi.spyOn(api, 'listNights').mockResolvedValue([night])
    vi.spyOn(api, 'listEpisodes').mockResolvedValue([])
    vi.spyOn(api, 'getNightDetail').mockResolvedValue(null)
    const onOpenRecord = vi.fn()
    render(<HistoryView subject={subject} config={config} initialNight="2026-09-27" onOpenRecord={onOpenRecord} />)

    await waitFor(() => expect(api.listEpisodes).toHaveBeenCalledWith('sim'))
    expect(screen.getByText('Reading coverage')).toBeInTheDocument()
    fireEvent.click(screen.getByText('What this chart can and cannot tell you'))
    expect(screen.getByText(/needs 7 usable nights before it can alert/)).toBeInTheDocument()
    expect(screen.getByText(/Waking heart rate and naps are left out/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('checkbox', { name: /show every recorded field/i }))
    expect(screen.getByText('Explained by exercise')).toBeInTheDocument()
    expect(screen.getByText('Usual range')).toBeInTheDocument()
    expect(screen.queryByText(/forecast/i)).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Show me every step of that night' }))
    expect(onOpenRecord).toHaveBeenCalledWith('record', '2026-09-27')
  })
})
