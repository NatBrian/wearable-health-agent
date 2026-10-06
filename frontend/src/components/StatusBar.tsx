import type { BaselineRung, Subject, SystemStatus } from '../api'
import { legacyText } from '../content/legacyCopy'

type StatusLine = { label: string; state: string; explanation: string; degraded: boolean }

function localTime(value: string | null, timeZone: string): string {
  if (!value) return 'not recorded yet'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'time unavailable'
  return new Intl.DateTimeFormat(undefined, {
    hour: 'numeric', minute: '2-digit', timeZone,
  }).format(date)
}

function component(status: SystemStatus, name: string) {
  return status.components.find((item) => item.component === name)
}

function linesFor(status: SystemStatus, subject: Subject): StatusLine[] {
  const bridge = component(status, 'bridge')
  const scheduler = component(status, 'scheduler')
  const model = component(status, 'llm')
  const telegram = component(status, 'telegram')

  const watch: StatusLine = bridge?.severity === 'error'
    ? { label: 'Watch data', state: 'not arriving', explanation: 'Nothing new is coming from your phone, so nights from now on will not be judged.', degraded: true }
    : bridge?.severity === 'warn'
      ? { label: 'Watch data', state: 'delayed', explanation: bridge.detail, degraded: true }
      : { label: 'Watch data', state: `arrived ${localTime(status.last_ingest_utc, subject.timezone)}`, explanation: 'Your phone is handing over readings.', degraded: false }

  const baseline: StatusLine = {
    label: 'Your normal',
    state: `${status.usable_nights} nights measured`,
    explanation: legacyText(`rung.${status.rung}` as `rung.${BaselineRung}`),
    degraded: status.rung === 'COLD' || status.rung === 'PRIOR_DOMINATED',
  }

  const nightly: StatusLine = scheduler && !scheduler.ok
    ? { label: 'Nightly check', state: 'not running', explanation: 'Nights are not being judged until this is running again.', degraded: true }
    : { label: 'Nightly check', state: `last ran ${localTime(status.last_nightly_utc, subject.timezone)}`, explanation: 'Runs on its own, several times a day.', degraded: false }

  const ai: StatusLine = model && !model.ok
    ? { label: 'AI model', state: 'not reachable', explanation: 'Questions and written summaries are unavailable. Nights are still measured and judged, because that half uses no AI at all.', degraded: true }
    : { label: 'AI model', state: 'reachable', explanation: 'Used only for questions, summaries and chat.', degraded: false }

  const contact: StatusLine = !telegram || !telegram.ok
    ? { label: 'How you get asked', state: 'this screen only', explanation: 'No messaging is set up, so questions wait here until you open the dashboard.', degraded: false }
    : { label: 'How you get asked', state: 'Telegram', explanation: 'Questions reach you on your phone.', degraded: false }

  return [watch, baseline, nightly, ai, contact]
}

export function StatusBar({
  status, subject, loading, error, onOpenRecord,
}: {
  status: SystemStatus | null
  subject: Subject
  loading: boolean
  error: string | null
  onOpenRecord: () => void
}) {
  if (!status) {
    return (
      <section className="status-panel" aria-label="System status" aria-live="polite">
        <div className="status-panel__heading"><span>System status</span><span className="status-tag">{loading ? 'Checking' : 'Unavailable'}</span></div>
        <p>{error ? 'The system status could not be loaded. This is not a statement about your health.' : 'Checking whether each part of the system is working.'}</p>
      </section>
    )
  }

  const lines = linesFor(status, subject)
  const degraded = lines.filter((line) => line.degraded)
  return (
    <section className="status-panel" aria-label="System status">
      <div className="status-panel__heading">
        <div><span className="eyebrow">System status</span><h2>What is working right now</h2></div>
        <span className={`status-tag ${degraded.length ? 'status-tag--attention' : 'status-tag--ok'}`}>
          {degraded.length ? 'Needs attention' : 'Running'}
        </span>
      </div>
      <p className="supporting-copy">{legacyText('status.what_it_is')}</p>
      {error && <p className="inline-notice inline-notice--warning">Some information could not be refreshed. The details shown may be out of date. {error}</p>}
      <div className="status-grid">
        {lines.map((line) => (
          <article className={`status-item ${line.degraded ? 'status-item--attention' : ''}`} key={line.label}>
            <span className="status-item__label">{line.label}</span>
            <strong>{line.state}</strong>
            <p>{line.explanation}</p>
          </article>
        ))}
      </div>
      {degraded.length > 0 && (
        <p className="status-footnote">Some parts need attention: {degraded.map((line) => line.label).join(', ')}. Each line says what stops working.</p>
      )}
      {status.errors_24h > 0 && (
        <button className="text-link" onClick={onOpenRecord}>
          The system recorded {status.errors_24h} problems in the last day. See them on The record.
        </button>
      )}
    </section>
  )
}
