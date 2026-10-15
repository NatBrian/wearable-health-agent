import type { PipelineStepView, SystemConfig } from '../api'
import { CitationPanel } from './CitationPanel'
import { LEGACY_COPY, legacyText } from '../content/legacyCopy'
import { dateLabel, measuredValue, signedValue, timeLabel } from '../lib/format'

const FIELD_NAMES: Record<string, string> = {
  heart_rate_samples: 'Readings stored', sleep_stage_rows: 'Sleep records', window_source: 'Window used',
  asleep_minutes: 'Minutes in the sleep window', start_utc: 'Window started', end_utc: 'Window ended',
  rhr_bpm: 'Your reading', coverage_minutes: 'Minutes measured', sleep_hours: 'Hours of sleep',
  usable: 'Good enough to use', implausible_dropped: 'Impossible readings dropped', centre_bpm: 'Your normal',
  scale_bpm: 'How much you vary', usable_nights: 'Nights it is built from', rung: 'How well your normal is known',
  explained_bpm: 'Explained by exercise', residual_bpm: 'Left after that', deviation_bpm: 'Above your normal',
  robust_z: 'How unusual, in your own units', level: 'Conclusion', flagged: 'Opened an investigation',
  reasons: 'Why', top_cause: 'Leading explanation', top_probability: 'How likely', p_illness: 'Chance infection is contributing',
  evsi: 'Value of asking you', interruption_cost: 'Cost of interrupting you', questions: 'Questions asked', replies: 'What you said',
  stripped_claims: 'Claims removed for having no source', tool_call_count: 'Tool calls', messages_checked: 'Messages checked',
  episode_id: 'Investigation', persisted_beyond_window: 'Symptoms still going', co_occurring_within_window: 'Symptoms close together in time',
  raised_something: 'This step raised something', cooccurrence_window_nights: 'How close two symptoms must be',
}

export function PipelineStepDetail({ step, totalSteps, config, timezone }: {
  step: PipelineStepView | null
  totalSteps: number
  config: SystemConfig
  timezone: string
}) {
  if (!step) return <section className="content-card step-detail"><span className="eyebrow">Step detail</span><p>Select a step to see exactly what it did.</p></section>

  const copy = LEGACY_COPY as Record<string, string>
  const whatKey = `step.${step.step_id}.what`
  const whyKey = `step.${step.step_id}.why`
  const reported = asArray(step.outputs.reported_symptoms)
  const marginals = asRecord(step.outputs.marginals)
  const questions = asArray(step.outputs.questions_considered)
  const arithmetic = arithmeticFor(step)

  return (
    <section className="content-card step-detail" aria-labelledby="step-detail-heading">
      <div className="step-detail__meta"><span className={`layer-badge layer-badge--${step.layer}`}>{step.layer}</span><span>Step {step.ordinal} of {totalSteps}</span><span className={`pipeline-status pipeline-status--${step.status}`}>{step.status}</span>{step.occurred_utc ? <span>Occurred {dateLabel(step.occurred_utc, timezone)} at {timeLabel(step.occurred_utc, timezone)}</span> : step.status === 'ran' ? <span>Time not recorded</span> : null}</div>
      <h2 id="step-detail-heading">{step.step_id.replace(/_/g, ' ')}</h2>
      <h3>What happened</h3><p>{step.reason || 'No explanation was recorded for this step.'}</p>
      {step.status === 'unrecorded' && <p className="inline-notice inline-notice--warning">{legacyText('pipeline.unrecorded')}</p>}
      {step.status !== 'ran' && step.status !== 'unrecorded' && <p className="supporting-copy">This step {step.status.replace(/_/g, ' ')} on this night.</p>}
      <h3>Why this step exists</h3><p>{copy[whyKey] ?? `This step is part of the recorded process. Its inputs and outputs are available below.`}</p>
      {copy[whatKey] && <p className="step-what-copy">{copy[whatKey]}</p>}
      {arithmetic && <section className="arithmetic-note"><h3>The numbers</h3><p>{arithmetic}</p></section>}
      {reported.length > 0 && <SymptomTimeline entries={reported} config={config} />}
      {Object.keys(marginals).length > 0 && <CauseMarginals values={marginals} pIllness={step.outputs.p_illness} />}
      {questions.length > 0 && <QuestionValues entries={questions} />}
      {Object.keys(step.outputs).length > 0 && <section><h3>What it produced</h3><dl className="step-output-list">{Object.entries(step.outputs).filter(([key, value]) => value !== null && !['marginals', 'questions_considered', 'reported_symptoms'].includes(key)).map(([key, value]) => <div key={key}><dt>{fieldName(step, key)}</dt><dd>{displayValue(value)}</dd></div>)}</dl></section>}
      {step.sources.length > 0 && <section><h3>Sources it read</h3><CitationPanel citations={step.sources} config={config} /></section>}
      <details className="raw-step"><summary>The raw record for this step</summary><pre>{JSON.stringify({ step_id: step.step_id, status: step.status, occurred_utc: step.occurred_utc, inputs: step.inputs, outputs: step.outputs }, null, 2)}</pre></details>
    </section>
  )
}

function arithmeticFor(step: PipelineStepView): string | null {
  const output = step.outputs
  if (step.step_id === 'detect' && typeof output.deviation_bpm === 'number') {
    return `Your reading minus your normal is ${signedValue(output.deviation_bpm, 'bpm')}. After subtracting what a recorded workout explains, ${measuredValue(asNumber(output.residual_bpm), 'bpm')} was left, and that is what was judged.`
  }
  if (step.step_id === 'baseline' && typeof output.centre_bpm === 'number') {
    return `The middle of your recent nights is ${measuredValue(output.centre_bpm, 'bpm')}, and you vary by about ${measuredValue(asNumber(output.scale_bpm), 'bpm')} from night to night. That is built from ${displayValue(output.usable_nights)} of your own nights.`
  }
  if (step.step_id === 'decide' && output.action) {
    if (output.action === 'ASK' && typeof output.value_of_asking === 'number' && typeof output.interruption_cost === 'number') return `Asking you was worth ${output.value_of_asking.toFixed(3)} against a cost of interrupting you of ${output.interruption_cost.toFixed(3)}. A question is only asked when the first is larger, and it was.`
    if (asArray(output.questions_considered).length > 0) return `Every question it could have asked was scored. Each recorded value is shown below. A negative value means the answer would be worth less than the cost of interrupting you, so it asked nothing.`
    return 'No question scored high enough to be worth interrupting you.'
  }
  if (step.step_id === 'believe' && typeof output.top_probability === 'number') return `The possible causes were weighed against the evidence using exact arithmetic. The leading cause is ${String(output.top_cause ?? 'not recorded').replace(/_/g, ' ')} at ${new Intl.NumberFormat(undefined, { style: 'percent', maximumFractionDigits: 1 }).format(output.top_probability)}.`
  return null
}

function fieldName(step: PipelineStepView, key: string): string {
  if (step.step_id === 'sleep_window' && key === 'asleep_minutes' && step.outputs.window_source === 'clock') {
    return 'Minutes in the clock window'
  }
  return FIELD_NAMES[key] ?? key.replace(/_/g, ' ')
}

function SymptomTimeline({ entries, config }: { entries: unknown[]; config: SystemConfig }) {
  const days = typeof config.SYMPTOM_RUN_GAP_DAYS === 'number' ? config.SYMPTOM_RUN_GAP_DAYS : null
  return <section className="special-step-data"><h3>What you have told the system, and for how long</h3><div className="table-scroll"><table className="history-table"><thead><tr><th>Symptom</th><th>Nights so far</th><th>Raises it after</th><th>Still going</th><th>First said</th><th>Last said</th></tr></thead><tbody>{entries.filter(isRecord).map((entry, index) => <tr key={`${String(entry.symptom)}-${index}`}><td>{displayValue(entry.symptom)}</td><td>{displayValue(entry.nights_so_far)}</td><td>{entry.escalates_after_nights == null ? 'does not raise on its own' : `${displayValue(entry.escalates_after_nights)} nights`}</td><td>{entry.still_going ? 'yes' : 'you said it had gone'}</td><td>{displayValue(entry.first_reported)}</td><td>{displayValue(entry.last_reported)}</td></tr>)}</tbody></table></div><p className="supporting-copy">Counted from the first night you mentioned something to the most recent. A night you said nothing does not reset the count, because saying nothing is not the same as being better. A symptom stops counting when you say it has gone, or after {days ?? 'the configured interval'} days with no mention. Symptoms marked as not raising anything on their own are recorded so the system can ask about them, not to route your care.</p></section>
}

function CauseMarginals({ values, pIllness }: { values: Record<string, unknown>; pIllness: unknown }) {
  const rows = Object.entries(values).filter((entry): entry is [string, number] => typeof entry[1] === 'number').sort((a, b) => b[1] - a[1])
  return <section className="special-step-data"><h3>All causes it weighed</h3><div className="cause-marginals">{rows.map(([cause, probability]) => <div key={cause}><span>{cause.replace(/_/g, ' ')}</span><strong>{new Intl.NumberFormat(undefined, { style: 'percent', maximumFractionDigits: 1 }).format(probability)}</strong></div>)}</div><p className="supporting-copy">These do not add up to a hundred, and that is deliberate: more than one of them can be true on the same night, so each carries its own probability. They are probabilities on the evidence so far, not a diagnosis.</p>{typeof pIllness === 'number' && <p>Chance an infection is contributing: {new Intl.NumberFormat(undefined, { style: 'percent', maximumFractionDigits: 1 }).format(pIllness)}. This is the single number the decision after this step is based on.</p>}</section>
}

function QuestionValues({ entries }: { entries: unknown[] }) {
  return <section className="special-step-data"><h3>Every question it weighed</h3><div className="table-scroll"><table className="history-table"><thead><tr><th>Question</th><th>Worth asking</th><th>Interruption cost</th><th>Target cause</th></tr></thead><tbody>{entries.filter(isRecord).map((entry, index) => <tr key={`${String(entry.probe_id)}-${index}`}><td>{String(entry.probe_id ?? 'not recorded').replace(/_/g, ' ')}</td><td>{typeof entry.value_of_asking === 'number' ? entry.value_of_asking.toFixed(3) : displayValue(entry.value_of_asking)}</td><td>{displayValue(entry.interruption_cost)}</td><td>{displayValue(entry.target_cause)}</td></tr>)}</tbody></table></div><p className="supporting-copy">Higher is worth more. A negative number means the answer would change what the system concludes by less than the cost of interrupting you, so it is not asked.</p></section>
}

function asRecord(value: unknown): Record<string, unknown> { return isRecord(value) ? value : {} }
function asArray(value: unknown): unknown[] { return Array.isArray(value) ? value : [] }
function isRecord(value: unknown): value is Record<string, unknown> { return typeof value === 'object' && value !== null && !Array.isArray(value) }
function asNumber(value: unknown): number | null { return typeof value === 'number' ? value : null }
function displayValue(value: unknown): string {
  if (value === null || value === undefined) return 'not recorded'
  if (typeof value === 'boolean') return value ? 'yes' : 'no'
  if (Array.isArray(value)) return value.length ? value.map(displayValue).join(', ') : 'none'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}
