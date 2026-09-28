import type { NightDetail, SystemConfig, SystemStatus, Subject } from '../api'
import { legacyText } from '../content/legacyCopy'
import { dateLabel, measuredValue, signedValue } from '../lib/format'

export function VerdictPanel({
  detail, status, config, subject, investigating, onOpenRecord,
}: {
  detail: NightDetail | null
  status: SystemStatus | null
  config: SystemConfig
  subject: Subject
  investigating: boolean
  onOpenRecord: (nightDate: string) => void
}) {
  if (!detail) {
    return (
      <section className="content-card verdict-card" aria-labelledby="verdict-heading">
        <div className="section-heading"><div><span className="eyebrow">Latest night</span><h2 id="verdict-heading">No night has been measured yet</h2></div></div>
        <p>No reading is missing data, not a result. Nothing here says anything about your health.</p>
      </section>
    )
  }

  const row = detail.row
  const level = row.level
  const rung = detail.baseline.rung
  const immature = rung === 'COLD' || rung === 'PRIOR_DOMINATED'
  const levelKey = level === 'NA' ? 'level.NA' : `level.${level}` as 'level.GREEN' | 'level.YELLOW' | 'level.RED'
  const nextKey = level === 'NA' ? 'level.NA.next' : `level.${level}.next` as 'level.GREEN.next' | 'level.YELLOW.next' | 'level.RED.next'
  const recentWindow = typeof config.RECENT_NIGHTS_WINDOW === 'number' ? config.RECENT_NIGHTS_WINDOW : null

  return (
    <section className="content-card verdict-card" aria-labelledby="verdict-heading">
      <div className="section-heading">
        <div><span className="eyebrow">Last measured night</span><h2 id="verdict-heading">{dateLabel(row.night_date, subject.timezone)}</h2></div>
        <span className={`level-badge level-badge--${level.toLowerCase()}`}>{level}</span>
      </div>
      {immature && <aside className="maturity-note"><strong>Still learning your normal.</strong><p>{legacyText('level.immature_note')} {legacyText(`rung.${rung}`)}</p></aside>}
      <p className="verdict-explanation">{legacyText(levelKey)}</p>
      <div className="next-step"><span className="eyebrow">What happens now</span><p>{investigating ? legacyText('level.investigating') : legacyText(nextKey)}</p></div>
      <p className="clinical-limit">{legacyText('level.not_a_diagnosis')}</p>
      <div className="metric-grid">
        <Metric label="Your reading" value={measuredValue(row.rhr_bpm, 'bpm')} copy={legacyText('metric.rhr')} />
        <Metric label="Your normal" value={measuredValue(row.centre_bpm, 'bpm')} copy={`${legacyText('metric.baseline')} Usual range ${measuredValue(row.band_lo, 'bpm')} to ${measuredValue(row.band_hi, 'bpm')}.`} />
        <Metric label="The difference" value={signedValue(row.deviation_bpm, 'bpm')} copy={legacyText('metric.gap')} />
      </div>
      <div className="verdict-details">
        <p>{legacyText(`metric.window_source.${row.rhr_window_source === 'sleep' ? 'sleep' : 'clock'}`)} Your watch measured {measuredValue(row.coverage_minutes, 'minutes')} of this night. {legacyText('metric.coverage')}</p>
        {row.explained_bpm > 0 && <p>A recorded evening workout explained {measuredValue(row.explained_bpm, 'bpm')} of the rise, and that was subtracted before this night was judged.</p>}
      </div>
      <div className="safety-disclosures">
        <details><summary>What symptom rules can miss</summary><p>{legacyText('safety.what_it_cannot_catch')}</p><p>{legacyText('safety.no_local_guidance')}</p></details>
      </div>
      {status && (status.quiet_nights_streak > 0 || status.unmeasured_recent_nights > 0) && (
        <div className="night-counts">
          {status.quiet_nights_streak > 0 && <p>{status.quiet_nights_streak} measured nights in a row were in the usual range.</p>}
          {status.unmeasured_recent_nights > 0 && <p>{recentWindow ? `${status.unmeasured_recent_nights} of the last ${recentWindow} recent nights` : `${status.unmeasured_recent_nights} recent nights`} had no reading. A night without a reading is not counted as quiet.</p>}
        </div>
      )}
      <button className="button button--secondary" onClick={() => onOpenRecord(row.night_date)}>See every step of this night</button>
    </section>
  )
}

function Metric({ label, value, copy }: { label: string; value: string; copy: string }) {
  return <article className="metric-card"><span>{label}</span><strong>{value}</strong><p>{copy}</p></article>
}
