import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { api, type PendingInteraction, type SystemConfig } from '../api'
import { PendingInteraction as PendingCard } from '../components/PendingInteraction'
import { CitationPanel } from '../components/CitationPanel'

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

const questionPending: PendingInteraction = {
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
const chestPainPending: PendingInteraction = {
  ...questionPending,
  question: {
    ...questionPending.question!,
    probe: { ...questionPending.question!.probe, probe_id: 'mhs_worse_with_exercise' },
  },
}

afterEach(() => { cleanup(); vi.restoreAllMocks() })

describe('pending interaction controls', () => {
  it('submits the chosen answer and optional free text together', async () => {
    const onComplete = vi.fn()
    const submit = vi.spyOn(api, 'submitAnswer').mockResolvedValue({ status: 'recorded' })
    render(<PendingCard pending={questionPending} config={config} safetyRules={[]} onComplete={onComplete} />)
    fireEvent.change(screen.getByLabelText(/anything else/i), { target: { value: 'Since yesterday' } })
    fireEvent.click(screen.getByRole('button', { name: 'Yes' }))
    expect(await screen.findByRole('heading', { name: 'One question for you' })).toBeInTheDocument()
    expect(submit).toHaveBeenCalledWith('episode-a', { probe_id: 'probe-a', option_id: 'yes', free_text: 'Since yesterday' })
    expect(onComplete).toHaveBeenCalledOnce()
  })

  it('submits a written answer without requiring an option', async () => {
    const onComplete = vi.fn()
    const submit = vi.spyOn(api, 'submitAnswer').mockResolvedValue({ status: 'recorded' })
    render(<PendingCard pending={questionPending} config={config} safetyRules={[]} onComplete={onComplete} />)
    fireEvent.change(screen.getByLabelText(/anything else/i), { target: { value: '  Since yesterday  ' } })
    fireEvent.click(screen.getByRole('button', { name: 'Send written answer' }))
    expect(submit).toHaveBeenCalledWith('episode-a', { probe_id: 'probe-a', option_id: null, free_text: 'Since yesterday' })
    await waitFor(() => expect(onComplete).toHaveBeenCalledOnce())
  })

  it('keeps typed text when the answer request fails', async () => {
    vi.spyOn(api, 'submitAnswer').mockRejectedValue(new Error('offline'))
    render(<PendingCard pending={questionPending} config={config} safetyRules={[]} onComplete={() => undefined} />)
    const input = screen.getByLabelText(/anything else/i)
    fireEvent.change(input, { target: { value: 'Still sore' } })
    fireEvent.click(screen.getByRole('button', { name: 'Yes' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not save that response')
    expect(input).toHaveValue('Still sore')
  })

  it('shows the cited rule beside chest-pain questions', () => {
    render(<PendingCard pending={chestPainPending} config={config} safetyRules={[{
      rule: 'marburg_heart_score', number: 'applies to chest pain', provenance: 'CITED',
      basis: 'Bösner et al., CMAJ; external validation by Haasenritter et al., Br J Gen Pract', minimum_age_years: 35,
    }]} onComplete={() => undefined} />)
    expect(screen.getByText(/These chest-pain questions follow the Marburg Heart Score/)).toHaveTextContent('Bösner')
    expect(screen.getByText(/Haasenritter/)).toBeInTheDocument()
  })

  it('preserves the legacy measurement instruction without promising an unavailable result action', () => {
    const pending: PendingInteraction = {
      ...questionPending, kind: 'measurement', question: null,
      measurement: { measurement_id: 'measurement-a', kind: 'spot_resting_hr', instruction: 'Take a resting pulse.', expires_at_utc: '2026-09-28T12:00:00Z' },
    }
    render(<PendingCard pending={pending} config={config} safetyRules={[]} onComplete={() => undefined} />)
    expect(screen.getByText('Take a resting pulse.')).toBeInTheDocument()
    expect(screen.getByText('This is asked only where the reading would change what happens next.')).toBeInTheDocument()
    expect(screen.queryByText(/show the result when it is recorded/i)).not.toBeInTheDocument()
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('shows source cards without an uncited notice', () => {
    render(<CitationPanel citations={[{
      source_id: 'local:source', title: 'Example source', uri: null,
      passage: 'A cited passage.', retrieval_score: 1,
    }]} config={config} />)
    expect(screen.getByRole('region', { name: 'Sources behind this reply' })).toBeInTheDocument()
    expect(screen.queryByRole('complementary', { name: /statements have no citation/i })).not.toBeInTheDocument()
  })

  it('marks a review draft unverified when it has no source metadata', () => {
    const pending: PendingInteraction = {
      ...questionPending, kind: 'review', question: null,
      draft_outcome: {
        schema_version: '1', episode_id: 'episode-a', subject_id: 'sim',
        opened_on: '2026-09-27', closed_on: '2026-09-28', disposition: 'UNRESOLVED',
        observation: 'A draft with no attached source metadata.', baseline_nights: 7,
        baseline_rung: 'PERSONAL', differential: [], evidence_used: [], ruled_out: [],
        citations: [], unsupported_claims: 0, action: '', escalation_criteria: [],
        confidence: 'moderate', interruptions_used_this_week: 0, depth_used_this_episode: 0,
      },
    }
    render(<PendingCard pending={pending} config={config} safetyRules={[]} onComplete={() => undefined} />)

    expect(screen.getByRole('complementary', { name: 'Source status unavailable' }))
      .toHaveTextContent('Treat any health information here as unverified.')
  })

  it('shows the full passage and warns when the supplied quote cannot be found', () => {
    render(<CitationPanel citations={[{
      source_id: 'local:source', title: 'Example source', uri: null, passage: 'The full passage remains available.', retrieval_score: 1, quoted_span: 'missing words',
    }]} config={config} />)
    fireEvent.click(screen.getByRole('button', { name: /Example source/ }))
    expect(screen.getByText(/quoted words could not be found/i)).toBeInTheDocument()
    expect(screen.getByText('The full passage remains available.')).toBeInTheDocument()
  })

  it('warns when a citation has no quoted span to verify', () => {
    render(<CitationPanel citations={[{
      source_id: 'local:source', title: 'Example source', uri: null, passage: 'The full passage remains available.', retrieval_score: 1, quoted_span: null,
    }]} config={config} />)
    fireEvent.click(screen.getByRole('button', { name: /Example source/ }))
    expect(screen.getByText(/quoted words could not be found/i)).toBeInTheDocument()
  })

  it('verifies a quote using the same case and whitespace normalization as the backend', () => {
    render(<CitationPanel citations={[{
      source_id: 'local:source', title: 'Example source', uri: null,
      passage: 'It is important to drink enough liquids, to prevent dehydration.',
      retrieval_score: 1, quoted_span: 'IMPORTANT   TO DRINK ENOUGH liquids, to prevent dehydration.',
    }]} config={config} />)
    fireEvent.click(screen.getByRole('button', { name: /Example source/ }))
    expect(screen.queryByText(/quoted words could not be found/i)).not.toBeInTheDocument()
    expect(screen.getByText(/Quoted words:/)).toBeInTheDocument()
  })
})
