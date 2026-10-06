import type { NightPipeline, PipelineStepView } from '../api'
import { legacyText } from '../content/legacyCopy'
import { dateLabel, measuredValue, timeLabel } from '../lib/format'

const STEP_NAMES: Record<string, string> = {
  collect: 'Collect from watch', store: 'Store the readings', sleep_window: 'Find your sleep',
  features: 'One number for the night', baseline: 'Your normal', subtract_explained: 'Subtract what is explained',
  detect: 'Judge the night', safety_floor: 'Check what you told us', episode_open: 'Open an investigation',
  preload: 'Fixed first readings', investigate: 'AI gathers evidence', believe: 'Weigh possible causes',
  decide: 'Worth asking you?', ask: 'Ask you', answer: 'Your answer', conclude: 'Draft a conclusion',
  critique: 'Remove unsourced claims', review: 'A person checks it', deliver: 'Send and save',
  safety_phrase_rules: 'Phrase rules', safety_triage: 'Published checklist',
}

export function PipelineTrace({ pipeline, selectedId, onSelect, timezone }: {
  pipeline: NightPipeline
  selectedId: string | null
  onSelect: (stepId: string) => void
  timezone: string
}) {
  const ordinary = pipeline.steps.filter((step) => step.layer !== 'safety')
  const safety = pipeline.steps.filter((step) => step.layer === 'safety')
  const sleepWindow = pipeline.steps.find((step) => step.step_id === 'sleep_window')
  const clockFallback = sleepWindow?.outputs.window_source === 'clock'
  const coverage = measuredValue(pipeline.headline.coverage_minutes, 'minutes')
  return (
    <section className="content-card pipeline-card" aria-labelledby="pipeline-heading">
      <div className="section-heading"><div><span className="eyebrow">Stored processing trace</span><h2 id="pipeline-heading">From your watch to the conclusion</h2></div></div>
      <p className="pipeline-intro">{legacyText('pipeline.how_to_read')}</p>
      <p className="supporting-copy">The watch readings and night score belong to the selected date. Agent and user steps belong to its investigation and may have happened on another date; their recorded dates are shown when available.</p>
      <div className="pipeline-legend" aria-label="Pipeline layers"><span><i className="layer-dot layer-dot--deterministic" />Arithmetic and fixed rules</span><span><i className="layer-dot layer-dot--agentic" />AI inside a fixed boundary</span><span><i className="layer-dot layer-dot--user" />Your action</span><span><i className="layer-dot layer-dot--safety" />Safety floor</span></div>
      <div className="pipeline-grid">{ordinary.map((step) => <StepButton key={step.step_id} step={step} selected={step.step_id === selectedId} onSelect={onSelect} timezone={timezone} />)}</div>
      {safety.length > 0 && <section className="safety-floor" aria-label="Safety floor"><div><span className="eyebrow">Always runs before anything else</span><h3>Safety floor</h3><p>Runs on anything you type, before the AI sees it, and can only raise urgency.</p></div><div className="pipeline-grid">{safety.map((step) => <StepButton key={step.step_id} step={step} selected={step.step_id === selectedId} onSelect={onSelect} timezone={timezone} />)}</div></section>}
      <div className="pipeline-headline-grid">
        <article><span>What this night was</span><strong>{pipeline.headline.level}</strong><small>{pipeline.headline.rung ? legacyText(`rung.${pipeline.headline.rung}`) : legacyText('level.immature_note')}</small></article>
        <article><span>Most likely explanation</span><strong>{pipeline.headline.primary_cause?.replace(/_/g, ' ') ?? 'not worked out'}</strong><small>{pipeline.headline.primary_probability == null ? 'Only worked out for nights that were investigated.' : `${new Intl.NumberFormat(undefined, { style: 'percent', maximumFractionDigits: 0 }).format(pipeline.headline.primary_probability)} likely on the evidence so far.`}</small></article>
        <article><span>Watch-reported sleep</span><strong>{measuredValue(pipeline.headline.sleep_hours, 'hours')}</strong><small>{pipeline.headline.sleep_hours === null
          ? `No sleep duration was reported by the watch.${clockFallback ? ' The system used a clock fallback.' : ''} Heart-rate measurements covered ${coverage}.`
          : `${legacyText('metric.sleep_hours')} Heart-rate measurements covered ${coverage} of that window.`}</small></article>
        <article><span>Questions asked</span><strong>{pipeline.headline.questions_asked}</strong><small>You are only asked where your answer would change the outcome.</small></article>
        <article><span>Sources read</span><strong>{pipeline.headline.sources_read}</strong><small>Passages quoted while working this night out.</small></article>
      </div>
      <p className="supporting-copy">Trace for the night of {dateLabel(pipeline.night_date)}. A step marked unrecorded is a gap in the record, not a claim that it was skipped.</p>
    </section>
  )
}

function StepButton({ step, selected, onSelect, timezone }: { step: PipelineStepView; selected: boolean; onSelect: (id: string) => void; timezone: string }) {
  const name = step.step_id === 'sleep_window' && step.outputs.window_source === 'clock'
    ? 'Use the clock fallback'
    : STEP_NAMES[step.step_id] ?? step.step_id.replace(/_/g, ' ')
  const eventContext = step.occurred_utc
    ? `Occurred ${dateLabel(step.occurred_utc, timezone)} at ${timeLabel(step.occurred_utc, timezone)}`
    : step.status === 'ran' ? 'Time not recorded' : null
  return (
    <button className={`pipeline-step pipeline-step--${step.layer} ${selected ? 'pipeline-step--selected' : ''} pipeline-step--${step.status}`} onClick={() => onSelect(step.step_id)} aria-pressed={selected}>
      <span className="pipeline-step__heading"><strong>{name}</strong><span className={`pipeline-status pipeline-status--${step.status}`}>{step.status.replace(/_/g, ' ')}</span></span>
      <small>{step.headline_figure ?? step.reason}</small>
      {eventContext && <small className="pipeline-step__meta">{eventContext}</small>}
      {step.status === 'unrecorded' && <small>{legacyText('pipeline.unrecorded')}</small>}
      <span className="pipeline-step__layer">{step.layer}</span>
      <span className="visually-hidden">Step {step.ordinal}</span>
    </button>
  )
}
