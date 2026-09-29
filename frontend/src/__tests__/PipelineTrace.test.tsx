import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import type { NightPipeline, PipelineStepView, SystemConfig } from '../api'
import { PipelineStepDetail } from '../components/PipelineStepDetail'
import { PipelineTrace } from '../components/PipelineTrace'

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

function sleepStep(source: 'clock' | 'sleep'): PipelineStepView {
  return {
    step_id: 'sleep_window', ordinal: 3, layer: 'deterministic', status: 'ran',
    reason: source === 'clock'
      ? 'Your watch recorded no sleep for this night, so the reading used the clock window instead.'
      : 'The reading used the sleep window your watch recorded.',
    headline_figure: '7.0 hours measured', occurred_utc: null,
    inputs: {}, outputs: { window_source: source, asleep_minutes: 420 }, sources: [],
  }
}

function pipeline(source: 'clock' | 'sleep'): NightPipeline {
  return {
    subject_id: 'demo', night_date: '2026-09-23', episode_id: null,
    headline: {
      level: 'GREEN', flagged: false, rung: 'MATURE', primary_cause: null,
      primary_probability: null, sleep_hours: source === 'clock' ? null : 7,
      coverage_minutes: 420, questions_asked: 0, sources_read: 0,
    },
    steps: [sleepStep(source)],
  }
}

afterEach(cleanup)

describe('sleep-window disclosures in The record', () => {
  it('describes a clock fallback as a measurement window rather than sleep', () => {
    const recorded = pipeline('clock')
    render(<><PipelineTrace pipeline={recorded} selectedId="sleep_window" onSelect={() => undefined} timezone="UTC" /><PipelineStepDetail step={recorded.steps[0]} totalSteps={21} config={config} timezone="UTC" /></>)

    expect(screen.getByRole('button', { name: /Use the clock fallback/ })).toBeInTheDocument()
    expect(screen.getByText(/No sleep duration was reported by the watch\. The system used a clock fallback\./)).toBeInTheDocument()
    expect(screen.getByText('Minutes in the clock window')).toBeInTheDocument()
    expect(screen.queryByText('Minutes in the sleep window')).not.toBeInTheDocument()
  })

  it('keeps watch-reported sleep wording for a recorded sleep window', () => {
    const recorded = pipeline('sleep')
    render(<><PipelineTrace pipeline={recorded} selectedId="sleep_window" onSelect={() => undefined} timezone="UTC" /><PipelineStepDetail step={recorded.steps[0]} totalSteps={21} config={config} timezone="UTC" /></>)

    expect(screen.getByRole('button', { name: /Find your sleep/ })).toBeInTheDocument()
    expect(screen.getByText(/How long your watch says you slept/)).toBeInTheDocument()
    expect(screen.getByText('Minutes in the sleep window')).toBeInTheDocument()
    expect(screen.queryByText('Minutes in the clock window')).not.toBeInTheDocument()
  })
})
