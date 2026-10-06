import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import type { SystemConfig } from '../api'
import { HowItWorks } from '../components/HowItWorks'

const config = {
  today: '2026-09-28', configured_subject: 'demo',
  N_CAUSES: 12,
  SYMPTOM_FOLLOWUP_MAX_PER_EPISODE: 3,
  DETECT_PERSISTENCE_NIGHTS: 2,
  BASELINE_MIN_NIGHTS_PERSONAL: 7,
  dashboard: {
    history_windows_days: [30, 60, 90, 365], steps_average_days: 7,
    cause_combinations: 4096,
    settings_bounds: {
      age_years: { minimum: 0, maximum: 120 },
      interruption_budget_per_week: { minimum: 0, maximum: 20 },
      depth_budget_per_episode: { minimum: 0, maximum: 10 },
      policy_cost_weight: { minimum: 0, maximum: 1, step: 0.01 },
    },
  },
} as SystemConfig

afterEach(cleanup)

describe('How it works disclosures', () => {
  it('keeps cause-table provenance, presentation limits, and forecast status together', () => {
    render(<HowItWorks config={config} settings={null} safetyRules={[]} permittedTools={['read_nights']} />)
    fireEvent.click(screen.getByText('Working out the likely cause'))

    expect(screen.getByText(/assembled with language-model assistance/)).toBeInTheDocument()
    expect(screen.getByText(/cutoff for showing a cause.*presentation rule, not a clinical threshold/)).toBeInTheDocument()
    expect(screen.getByText(/Chronos forecast is not part of this pipeline/)).toBeInTheDocument()
  })

  it('explains direct escalation and the unevidenced reply limit beside safety rules', () => {
    render(<HowItWorks config={config} settings={null} safetyRules={[]} permittedTools={['read_nights']} />)
    fireEvent.click(screen.getByText('The safety rules, which run before anything else'))

    expect(screen.getByText(/Other presentations have no suitable rule and escalate without waiting for questions/)).toBeInTheDocument()
    expect(screen.getByText(/that limit is unevidenced/i)).toBeInTheDocument()
  })
})
