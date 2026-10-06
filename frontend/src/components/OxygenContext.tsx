import type { OxygenReading, SafetyRuleProvenance, Subject } from '../api'
import { dateLabel, measuredValue, timeLabel } from '../lib/format'

export function OxygenContext({ readings, subject, error, safetyRules = [], title = 'Blood oxygen context' }: {
  readings: OxygenReading[]
  subject: Subject
  error?: string
  safetyRules?: SafetyRuleProvenance[]
  title?: string
}) {
  const oxygenRules = safetyRules.filter((rule) => rule.rule === 'oxygen_threshold')
  return (
    <section className="content-card oxygen-card" aria-labelledby="oxygen-heading">
      <div className="section-heading"><div><span className="eyebrow">Spot readings</span><h2 id="oxygen-heading">{title}</h2></div></div>
      {error ? <p className="inline-notice inline-notice--warning" role="alert">Blood oxygen readings could not be loaded. This is a fetch failure, not a period with no readings. {error}</p> : readings.length === 0 ? (
        <p>No spot reading is recorded in this period. The system has no opinion about blood oxygen without a reading.</p>
      ) : (
        <ul className="oxygen-list">
          {readings.map((reading) => (
            <li key={reading.ts_utc}><strong>{measuredValue(reading.percentage)}%</strong><span>{dateLabel(reading.ts_utc, subject.timezone)} at {timeLabel(reading.ts_utc, subject.timezone)}</span></li>
          ))}
        </ul>
      )}
      <p className="supporting-copy">Pulse oximeters can overestimate oxygen saturation for everyone, and by more on darker skin. A spot reading cannot say what is wrong. Blood oxygen can raise urgency but never lowers it.</p>
      <details className="oxygen-rule-disclosure">
        <summary>How the overnight oxygen rule works and where it comes from</summary>
        {oxygenRules.length > 0 ? <ul>{oxygenRules.map((rule, index) => <li key={`${rule.number}-${index}`}><strong>{rule.number}.</strong> {rule.basis}</li>)}</ul> : <p>The source and scope for the overnight rule could not be loaded.</p>}
        <p>These are occasional readings. They are not treated as overnight measurements and do not run the overnight rule by themselves.</p>
      </details>
    </section>
  )
}
