import { useCallback, useEffect, useMemo, useState } from 'react'
import { api, type HandoverSummary, type SystemConfig, type Subject, type SystemStatus, type UrgencyState } from '../api'
import { legacyText } from '../content/legacyCopy'
import type { BackendData } from '../useBackend'
import { dateLabel, measuredValue, timeLabel } from '../lib/format'
import { OxygenContext } from '../components/OxygenContext'
import { VerdictPanel } from '../components/VerdictPanel'
import type { DashboardViewId } from './HomeView'

const waitingCopy: Record<string, string> = {
  OPEN: 'The system is working through this now.',
  AWAITING_USER: 'Waiting for your answer to the question above.',
  AWAITING_MEASUREMENT: 'Waiting for a measurement from you.',
  AWAITING_HUMAN_REVIEW: 'Waiting for a person to check the draft conclusion.',
}

export function TodayView({
  subject, config, data, onNavigate, onOpenChat,
}: {
  subject: Subject
  config: SystemConfig
  data: BackendData
  onNavigate: (view: DashboardViewId, nightDate?: string) => void
  onOpenChat: () => void
}) {
  const [urgency, setUrgency] = useState<UrgencyState | null>(null)
  const [urgencyError, setUrgencyError] = useState<string | null>(null)
  const [acknowledging, setAcknowledging] = useState(false)
  const [handover, setHandover] = useState<HandoverSummary | null>(null)
  const [handoverLoading, setHandoverLoading] = useState(false)
  const [handoverError, setHandoverError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [whyNoQuestion, setWhyNoQuestion] = useState<string | null>(null)

  const latestDate = useMemo(() => [...data.nights]
    .filter((night) => night.usable)
    .sort((first, second) => first.night_date.localeCompare(second.night_date))
    .at(-1)?.night_date ?? null, [data.nights])

  const loadUrgency = useCallback(async () => {
    setUrgencyError(null)
    try { setUrgency(await api.getUrgency(subject.subject_id)) }
    catch (exc) { setUrgencyError(String(exc)) }
  }, [subject.subject_id])

  useEffect(() => { void loadUrgency() }, [loadUrgency])

  useEffect(() => {
    if (!latestDate) { setWhyNoQuestion(null); return }
    let active = true
    void api.getNightPipeline(subject.subject_id, latestDate).then((pipeline) => {
      if (!active || !pipeline) return
      const decision = pipeline.steps.find((step) => step.step_id === 'decide')
      if (!decision || decision.outputs.action === 'ASK') return
      const considered = decision.outputs.questions_considered
      const count = Array.isArray(considered) ? considered.length : 0
      setWhyNoQuestion(count
        ? `It did not ask you anything about this night. It scored ${count} possible questions and every one came out worth less than interrupting you for. The full scoring is on The record, under the step that made the decision.`
        : 'It did not ask you anything about this night. No question it could have put was worth the interruption.')
    }).catch(() => { if (active) setWhyNoQuestion(null) })
    return () => { active = false }
  }, [latestDate, subject.subject_id])

  const openEpisode = data.episodes.find((episode) => episode.state !== 'CLOSED') ?? null
  const activeEpisode = data.activeEpisode?.summary.state !== 'CLOSED' ? data.activeEpisode : null
  const urgencyActive = urgency?.urgency && urgency.urgency !== 'none' && !urgency.cleared

  const acknowledge = async () => {
    if (acknowledging) return
    setAcknowledging(true)
    setUrgencyError(null)
    try { await api.acknowledgeUrgency(subject.subject_id); await loadUrgency() }
    catch (exc) { setUrgencyError(String(exc)) }
    finally { setAcknowledging(false) }
  }

  const prepareHandover = async () => {
    setHandoverLoading(true)
    setHandoverError(null)
    setCopied(false)
    try { setHandover(await api.getHandover(subject.subject_id, openEpisode?.episode_id)) }
    catch (exc) { setHandoverError(String(exc)) }
    finally { setHandoverLoading(false) }
  }

  const copyHandover = async () => {
    if (!handover) return
    try {
      await navigator.clipboard.writeText(handover.text)
      setCopied(true)
      setHandoverError(null)
    } catch (exc) { setHandoverError(`Could not copy to the clipboard: ${String(exc)}`) }
  }

  const answered = activeEpisode?.interactions.filter((item) => item.status === 'ANSWERED').at(-1)
  const topCause = activeEpisode?.summary.top_cause
  const topProbability = activeEpisode?.summary.top_probability
  const displayWindow = typeof config.RECENT_NIGHTS_WINDOW === 'number' ? config.RECENT_NIGHTS_WINDOW : null

  return (
    <div className="page-stack">
      {urgencyActive && (
        <section className={`urgency-banner urgency-banner--${urgency?.urgency}`} role="alert">
          <div><span className="eyebrow">Safety rule</span><h1>{urgency?.urgency === 'urgent' ? 'This needs medical attention today.' : 'You should see a doctor today.'}</h1><p>{urgency?.reason || 'A fixed safety rule raised urgency from what was reported. The AI cannot lower it.'}</p><p className="supporting-copy">The system can raise urgency. It cannot make anything less urgent.</p></div>
          <button className="button button--secondary" disabled={acknowledging} onClick={() => void acknowledge()}>{acknowledging ? 'Saving…' : 'I have seen this'}</button>
        </section>
      )}
      {urgencyError && <p className="inline-notice inline-notice--warning" role="status">The urgency status could not be refreshed. {urgencyError}</p>}

      {data.errors.pending ? <section className="content-card inline-notice inline-notice--warning" role="alert"><strong>Could not check whether you need to answer.</strong><p>This is a fetch failure, not a confirmation that nothing is waiting. {data.errors.pending}</p><button className="button button--secondary" onClick={data.refresh}>Try again</button></section> : data.pending ? (
        <section className="content-card pending-summary" aria-label="Pending interaction">
          <div className="section-heading"><div><span className="eyebrow">Needs your attention</span><h2>{data.pending.kind === 'question' ? 'One question for you' : data.pending.kind === 'review' ? 'A summary is ready for you to check' : 'Something to measure'}</h2></div><span className="pending-pill">Waiting</span></div>
          <p>{data.pending.kind === 'question' ? data.pending.question?.text : data.pending.kind === 'measurement' ? data.pending.measurement?.instruction : data.pending.draft_outcome?.observation}</p>
          <button className="button button--primary" onClick={onOpenChat}>Open Agent Chat to respond</button>
        </section>
      ) : data.loading ? <section className="content-card" role="status">Checking whether anything needs your attention.</section> : (
        <section className={`inbox-state ${data.status?.rung === 'COLD' || data.status?.rung === 'PRIOR_DOMINATED' ? 'inbox-state--learning' : ''}`} aria-live="polite">
          {data.status && (data.status.rung === 'COLD' || data.status.rung === 'PRIOR_DOMINATED') ? (
            <><strong>Still learning your normal.</strong><p>{legacyText(`rung.${data.status.rung}`)}</p></>
          ) : !urgencyActive && <p>Nothing is waiting for you to answer right now.</p>}
          {!urgencyActive && data.status && data.status.quiet_nights_streak > 0 && <p>Your last {data.status.quiet_nights_streak} measured nights were in your usual range.</p>}
          {data.status && data.status.unmeasured_recent_nights > 0 && <p>{displayWindow ? `${data.status.unmeasured_recent_nights} of the last ${displayWindow} recent nights` : `${data.status.unmeasured_recent_nights} recent nights`} had no reading. A night without a reading is skipped rather than guessed at.</p>}
        </section>
      )}

      <section className="content-card observation-card" aria-labelledby="observation-heading">
        <div className="section-heading"><div><span className="eyebrow">The latest record</span><h2 id="observation-heading">Recent readings</h2></div></div>
        <div className="observation-grid">
          <Observation label="Sleep" value={measuredValue(data.summary?.latest_sleep_hours, 'hours')} date={data.summary?.latest_sleep_night ?? null} timezone={subject.timezone} />
          <Observation label="Steps" value={measuredValue(data.summary?.latest_steps, 'steps')} date={data.summary?.latest_steps_night ?? null} timezone={subject.timezone} />
          <Observation label="Average steps" value={measuredValue(data.summary?.steps_average, 'steps')} date={data.summary ? `${data.summary.steps_window_start}–${data.summary.steps_window_end}` : null} timezone={subject.timezone} />
        </div>
        {data.errors.summary && <p className="inline-notice inline-notice--warning" role="alert">Recent sleep and steps could not be loaded. The values above are unavailable, not zero. {data.errors.summary}</p>}
      </section>

      {data.loading && !data.latestDetail ? <div className="content-card" role="status">Loading the latest night.</div> : data.errors.nights || data.errors.latestDetail ? <section className="content-card inline-notice inline-notice--warning" role="alert"><strong>The latest night could not be checked.</strong><p>This is a fetch failure, not a night with no reading.</p><p>{data.errors.nights ?? data.errors.latestDetail}</p><button className="button button--secondary" onClick={data.refresh}>Try again</button></section> : (
        <VerdictPanel detail={data.latestDetail} status={data.status} config={config} subject={subject} investigating={Boolean(openEpisode)} onOpenRecord={(nightDate) => onNavigate('record', nightDate)} />
      )}

      {data.errors.episodes && <section className="content-card inline-notice inline-notice--warning" role="alert">Investigations could not be loaded. A missing result here does not mean there is no investigation. {data.errors.episodes}</section>}
      {data.errors.activeEpisode && <section className="content-card inline-notice inline-notice--warning" role="alert">The latest investigation detail could not be loaded. Its absence here is not a conclusion. {data.errors.activeEpisode}</section>}

      {openEpisode && (
        <section className="content-card investigation-card" aria-labelledby="investigation-heading">
          <div className="section-heading"><div><span className="eyebrow">Investigation</span><h2 id="investigation-heading">Being looked into</h2></div><span className="pending-pill">{openEpisode.state.replace(/_/g, ' ')}</span></div>
          <p>{waitingCopy[openEpisode.state] ?? 'In progress.'}</p>
          {answered && <div className="last-answer"><strong>It asked:</strong><p>{answered.question_text}</p><strong>You answered at {timeLabel(answered.answered_at_utc, subject.timezone)}:</strong><p>{answered.free_text || answered.answer_option_id || 'Answer recorded'}</p><span className="supporting-copy">Recorded. Whatever you said is used as evidence and never overridden.</span></div>}
          {topCause && <div className="cause-summary"><span className="eyebrow">Most likely explanation so far</span><strong>{topCause.replace(/_/g, ' ')}</strong><p>{topProbability == null ? 'The estimate moves as evidence arrives and is not a diagnosis.' : `${new Intl.NumberFormat(undefined, { style: 'percent', maximumFractionDigits: 0 }).format(topProbability)} likely at this point. This moves as evidence arrives and is not a diagnosis.`}</p></div>}
          <p className="supporting-copy">This investigation covers {dateLabel(openEpisode.night_span[0], subject.timezone)} to {dateLabel(openEpisode.night_span[1], subject.timezone)}. Every step is on The record.</p>
          {whyNoQuestion && <p className="decision-explanation">{whyNoQuestion}</p>}
          {activeEpisode?.outcome && <CauseEvidence detail={activeEpisode} knowledge={data.knowledgeProvenance} />}
        </section>
      )}

      <OxygenContext readings={data.oxygenReadings} subject={subject} error={data.errors.oxygenReadings} safetyRules={data.safetyRules} />

      <section className="content-card handover-card" aria-labelledby="handover-heading">
        <div className="section-heading"><div><span className="eyebrow">For a clinician</span><h2 id="handover-heading">Summary for your doctor</h2></div></div>
        <p>{legacyText('handover.what_it_is')}</p>
        <button className="button button--primary" onClick={() => void prepareHandover()} disabled={handoverLoading}>{handoverLoading ? 'Preparing…' : handover ? 'Refresh the summary' : 'Prepare the summary'}</button>
        {handoverError && <p className="inline-notice inline-notice--warning" role="alert">{handoverError}</p>}
        {handover && (
          <div className="handover-preview">
            <div className="handover-preview__toolbar"><strong>Read this before you send it. It is your health information, and where it goes is your decision.</strong><button className="button button--secondary" onClick={() => void copyHandover()}>{copied ? 'Copied' : 'Copy summary'}</button></div>
            <pre>{handover.text}</pre>
          </div>
        )}
      </section>
    </div>
  )
}

function Observation({ label, value, date, timezone }: { label: string; value: string; date: string | null; timezone: string }) {
  return <article className="observation-item"><span>{label}</span><strong>{value}</strong><small>{date ? `Recorded ${dateLabel(date, timezone)}` : 'No reading recorded'}</small></article>
}

function CauseEvidence({ detail, knowledge }: { detail: NonNullable<BackendData['activeEpisode']>; knowledge: BackendData['knowledgeProvenance'] }) {
  const differential = detail.outcome?.differential ?? []
  if (differential.length === 0) return null
  return (
    <details className="cause-evidence"><summary>Evidence considered and where its figures came from</summary>
      <div className="cause-list">
        {differential.map((item) => {
          const source = knowledge?.[item.cause]
          return <article className="cause-row" key={item.cause}>
            <div><strong>{item.cause.replace(/_/g, ' ')}</strong><span>{new Intl.NumberFormat(undefined, { style: 'percent', maximumFractionDigits: 0 }).format(item.probability)}</span><small>{source?.provenance ?? 'provenance unavailable'}{source?.profile_sourced === 'no' ? ' · not measured' : ''}</small></div>
            {item.supporting.length > 0 && <p>Supports: {item.supporting.join('; ')}</p>}
            {item.contradicting.length > 0 && <p>Against: {item.contradicting.join('; ')}</p>}
            {source?.note && <p className="supporting-copy">{source.note}</p>}
          </article>
        })}
      </div>
      <p className="supporting-copy">These are weighted explanations, not diagnoses. Several underlying figures are assumptions or are not measured; their provenance is shown beside each cause.</p>
    </details>
  )
}
