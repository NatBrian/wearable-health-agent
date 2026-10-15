import { useEffect, useMemo, useState } from 'react'
import { api, type AuditFilter, type AuditQueryResponse, type ConversationSession, type NightPipeline, type PipelineNightRef, type Subject, type SystemConfig } from '../api'
import { legacyText } from '../content/legacyCopy'
import { dateLabel, localDateBoundaryUtc, timeLabel } from '../lib/format'
import { CitationPanel } from '../components/CitationPanel'
import { HowItWorks } from '../components/HowItWorks'
import { PipelineStepDetail } from '../components/PipelineStepDetail'
import { PipelineTrace } from '../components/PipelineTrace'
import { PipelineOverview } from '../components/PipelineOverview'
import type { BackendData } from '../useBackend'
import type { DashboardViewId } from './HomeView'

type RecordTab = 'overview' | 'pipeline' | 'audit' | 'how'
const actors = ['anyone', 'system', 'agent', 'human', 'monitor']
const operations = ['anything', 'ingest', 'nightly', 'chat', 'execute_tool', 'human_decision', 'settings']

export function RecordView({ subject, config, data, initialNight, onNavigate }: {
  subject: Subject
  config: SystemConfig
  data: BackendData
  initialNight: string | null
  onNavigate: (view: DashboardViewId, nightDate?: string) => void
}) {
  const [tab, setTab] = useState<RecordTab>(initialNight ? 'pipeline' : 'overview')
  const [refs, setRefs] = useState<PipelineNightRef[]>([])
  const [refsLoading, setRefsLoading] = useState(true)
  const [refsError, setRefsError] = useState<string | null>(null)
  const [nightDate, setNightDate] = useState<string | null>(initialNight)
  const [pipeline, setPipeline] = useState<NightPipeline | null>(null)
  const [pipelineLoading, setPipelineLoading] = useState(false)
  const [pipelineError, setPipelineError] = useState<string | null>(null)
  const [selectedStep, setSelectedStep] = useState<string | null>(null)
  const [audit, setAudit] = useState<AuditQueryResponse | null>(null)
  const [auditLoading, setAuditLoading] = useState(false)
  const [auditError, setAuditError] = useState<string | null>(null)
  const [actor, setActor] = useState('anyone')
  const [operation, setOperation] = useState('anything')
  const [safetyEvent, setSafetyEvent] = useState('')
  const [episodeId, setEpisodeId] = useState('')
  const [sinceDate, setSinceDate] = useState('')
  const [untilDate, setUntilDate] = useState('')
  const [archive, setArchive] = useState<ConversationSession[]>([])
  const [archiveLoading, setArchiveLoading] = useState(false)
  const [archiveError, setArchiveError] = useState<string | null>(null)
  const [exportError, setExportError] = useState<string | null>(null)
  const [exporting, setExporting] = useState(false)

  useEffect(() => {
    let active = true
    setRefsLoading(true)
    setRefsError(null)
    void api.listPipelineNights(subject.subject_id, 60)
      .then((rows) => {
        if (!active) return
        const sorted = [...rows].sort((a, b) => b.night_date.localeCompare(a.night_date))
        setRefs(sorted)
        setNightDate((current) => current && sorted.some((row) => row.night_date === current)
          ? current
          : sorted.find((row) => row.usable)?.night_date ?? sorted[0]?.night_date ?? null)
      })
      .catch((exc: unknown) => { if (active) setRefsError(String(exc)) })
      .finally(() => { if (active) setRefsLoading(false) })
    return () => { active = false }
  }, [subject.subject_id])

  useEffect(() => {
    if (!nightDate) {
      setPipeline(null)
      setSelectedStep(null)
      setPipelineLoading(false)
      return
    }
    let active = true
    setPipeline(null)
    setPipelineLoading(true)
    setPipelineError(null)
    setSelectedStep(null)
    void api.getNightPipeline(subject.subject_id, nightDate)
      .then((value) => {
        if (!active) return
        setPipeline(value)
        setSelectedStep(value?.steps[0]?.step_id ?? null)
      })
      .catch((exc: unknown) => { if (active) { setPipeline(null); setPipelineError(String(exc)) } })
      .finally(() => { if (active) setPipelineLoading(false) })
    return () => { active = false }
  }, [nightDate, subject.subject_id])

  const filters = useMemo<AuditFilter>(() => ({
    actor: actor === 'anyone' ? undefined : actor,
    operation: operation === 'anything' ? undefined : operation,
    safety_event: safetyEvent.trim() || undefined,
    episode_id: episodeId.trim() || undefined,
    since_utc: sinceDate ? localDateBoundaryUtc(sinceDate, subject.timezone) : undefined,
    until_utc: untilDate ? localDateBoundaryUtc(untilDate, subject.timezone, true) : undefined,
  }), [actor, operation, safetyEvent, episodeId, sinceDate, subject.timezone, untilDate])

  useEffect(() => {
    if (tab !== 'audit' && tab !== 'how') return
    let active = true
    setAuditLoading(true)
    setAuditError(null)
    void api.getAudit(subject.subject_id, filters, 100, 0)
      .then((value) => { if (active) setAudit(value) })
      .catch((exc: unknown) => { if (active) setAuditError(String(exc)) })
      .finally(() => { if (active) setAuditLoading(false) })
    return () => { active = false }
  }, [tab, subject.subject_id, filters])

  useEffect(() => {
    if (tab !== 'audit') return
    let active = true
    setArchiveLoading(true)
    setArchiveError(null)
    void api.getConversationSessions(subject.subject_id, 1000)
      .then((value) => { if (active) setArchive(value) })
      .catch((exc: unknown) => { if (active) setArchiveError(String(exc)) })
      .finally(() => { if (active) setArchiveLoading(false) })
    return () => { active = false }
  }, [tab, subject.subject_id])

  const selectedIndex = refs.findIndex((ref) => ref.night_date === nightDate)
  const currentPipeline = pipeline?.night_date === nightDate ? pipeline : null
  const selectEarlier = () => { if (selectedIndex >= 0 && selectedIndex < refs.length - 1) setNightDate(refs[selectedIndex + 1].night_date) }
  const selectLater = () => { if (selectedIndex > 0) setNightDate(refs[selectedIndex - 1].night_date) }

  const exportRecord = async () => {
    setExporting(true)
    setExportError(null)
    try {
      const { content } = await api.exportAudit(subject.subject_id, filters)
      const blob = new Blob([content], { type: 'application/x-ndjson' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `record-${subject.subject_id}.jsonl`
      link.click()
      URL.revokeObjectURL(url)
    } catch (exc) { setExportError(String(exc)) }
    finally { setExporting(false) }
  }

  return (
    <div className="page-stack">
      <section className="record-heading"><div><span className="eyebrow">A reviewable history</span><p>{legacyText('record.what_it_is')}</p></div></section>
      <div className="record-tabs" role="tablist" aria-label="Pipeline sections">
        <button role="tab" aria-selected={tab === 'overview'} onClick={() => setTab('overview')}>System overview</button>
        <button role="tab" aria-selected={tab === 'pipeline'} onClick={() => setTab('pipeline')}>This night, step by step</button>
        <button role="tab" aria-selected={tab === 'audit'} onClick={() => setTab('audit')}>Everything the system did</button>
        <button role="tab" aria-selected={tab === 'how'} onClick={() => setTab('how')}>How this works</button>
      </div>

      {tab === 'overview' && <PipelineOverview data={data} timezone={subject.timezone} />}

      {tab === 'pipeline' && (
        <div className="page-stack">
          <section className="content-card night-navigation">
            <div className="night-navigation__arrows"><button className="button button--secondary" onClick={selectEarlier} disabled={selectedIndex < 0 || selectedIndex >= refs.length - 1}>Earlier</button><button className="button button--secondary" onClick={selectLater} disabled={selectedIndex <= 0}>Later</button></div>
            <label className="field-label">Which night<select value={nightDate ?? ''} onChange={(event) => setNightDate(event.target.value || null)} disabled={refsLoading || refs.length === 0}><option value="">Choose a night</option>{refs.map((ref) => <option key={ref.night_date} value={ref.night_date}>{dateLabel(ref.night_date, subject.timezone)} ({ref.usable ? ref.level : 'not measured'})</option>)}</select></label>
          </section>
          {refsLoading && <div className="content-card" role="status">Loading recorded nights.</div>}
          {refsError && <div className="content-card inline-notice inline-notice--warning" role="alert">Recorded nights could not be loaded. That is a fetch failure, not an empty record. {refsError}</div>}
          {!refsLoading && !refsError && refs.length === 0 && <div className="content-card empty-record"><strong>No nights are recorded yet.</strong><p>This is an empty record, not a failed check.</p></div>}
          {pipelineLoading && <div className="content-card" role="status">Loading the pipeline for this night.</div>}
          {pipelineError && <div className="content-card inline-notice inline-notice--warning" role="alert">This night could not be loaded. That is a failure to fetch it, not a statement that nothing happened. {pipelineError}</div>}
          {!pipelineLoading && !pipelineError && nightDate && !currentPipeline && <div className="content-card">No pipeline detail was recorded for this night.</div>}
          {currentPipeline && (
            <>
              <PipelineTrace pipeline={currentPipeline} selectedId={selectedStep} onSelect={setSelectedStep} timezone={subject.timezone} />
              <PipelineStepDetail step={currentPipeline.steps.find((step) => step.step_id === selectedStep) ?? null} totalSteps={currentPipeline.steps.length} config={config} timezone={subject.timezone} />
              <button className="text-link" onClick={() => onNavigate('history')}>Return to History</button>
            </>
          )}
        </div>
      )}

      {tab === 'audit' && (
        <div className="page-stack">
          <IntegrityPanel audit={audit} loading={auditLoading} error={auditError} />
          <section className="content-card">
            <div className="section-heading"><div><span className="eyebrow">Readable record</span><h2>What happened, in sentences</h2></div></div>
            {auditError && <p className="inline-notice inline-notice--warning">The record could not be loaded. {auditError}</p>}
            {auditLoading && <p role="status">Loading the record.</p>}
            {!auditLoading && !auditError && (!audit?.plain.length) && <p>{legacyText('record.empty')}</p>}
            <div className="plain-record-list">{audit?.plain.map((record) => <article className="plain-record" key={record.event_id}>
              <div className="plain-record__heading"><div><span className="eyebrow">{record.operation === 'nightly' && record.night ? `Night of ${dateLabel(record.night, subject.timezone)}` : record.operation === 'ingest' ? 'Data arrived from your watch' : record.operation}</span><small>Recorded {timeLabel(record.timestamp_utc, subject.timezone)}</small></div><span>{record.operation.replace(/_/g, ' ')}</span></div>
              {record.sentences.map((sentence, index) => <p key={`${record.event_id}-${index}`}>{sentence}</p>)}
              <details><summary>The exact figures behind this</summary><pre>{JSON.stringify(record.detail, null, 2)}</pre></details>
            </article>)}</div>
          </section>
          <ConversationArchive sessions={archive} loading={archiveLoading} error={archiveError} subject={subject} config={config} />
          <section className="content-card">
            <div className="section-heading"><div><span className="eyebrow">Filter and export</span><h2>Every recorded action</h2></div><button className="button button--primary" disabled={exporting} onClick={() => void exportRecord()}>{exporting ? 'Preparing…' : 'Prepare a copy of the record'}</button></div>
            <div className="audit-filters">
              <label className="field-label">Who did it<select value={actor} onChange={(event) => setActor(event.target.value)}>{actors.map((value) => <option key={value}>{value}</option>)}</select></label>
              <label className="field-label">What kind of action<select value={operation} onChange={(event) => setOperation(event.target.value)}>{operations.map((value) => <option key={value}>{value}</option>)}</select></label>
              <label className="field-label">Safety event<input value={safetyEvent} onChange={(event) => setSafetyEvent(event.target.value)} placeholder="Optional" /></label>
              <label className="field-label">Investigation id<input value={episodeId} onChange={(event) => setEpisodeId(event.target.value)} placeholder="Optional" /></label>
              <label className="field-label">From date<input type="date" value={sinceDate} onChange={(event) => setSinceDate(event.target.value)} /></label>
              <label className="field-label">To date<input type="date" value={untilDate} onChange={(event) => setUntilDate(event.target.value)} /></label>
            </div>
            <p className="supporting-copy">“Who” is you, the scheduled nightly job, or the AI. “Allowed” records whether a tool request was permitted or refused.</p>
            {exportError && <p className="inline-notice inline-notice--warning" role="alert">The record could not be exported. {exportError}</p>}
            {auditLoading && <p role="status">Applying record filters.</p>}
            {!auditLoading && !auditError && audit?.events.length === 0 && <p>No actions match those filters. The record itself is not empty.</p>}
            {!auditError && audit && audit.events.length > 0 && <div className="table-scroll" role="region" aria-label="Recorded actions" tabIndex={0}><table className="history-table"><thead><tr><th>When</th><th>Who</th><th>What</th><th>Tool used</th><th>Allowed</th><th>Safety</th><th>Unaltered</th><th>Investigation</th><th>Entry id</th><th>Control tier</th><th>Validation</th><th>Human decision</th><th>Latency</th><th>Step</th><th>Sources</th></tr></thead><tbody>{audit.events.map((event) => <tr key={event.event_id}><td>{timeLabel(event.timestamp_utc, subject.timezone)}</td><td>{event.actor}</td><td>{event.operation}</td><td>{event.tool_name ?? 'not recorded'}</td><td>{event.permission_decision ?? 'not applicable'}</td><td>{event.safety_event}</td><td>{event.hash_ok ? 'yes' : 'no'}</td><td>{event.episode_id ?? 'none'}</td><td>{event.event_id}</td><td>{event.control_tier ?? 'not recorded'}</td><td>{event.validation_status ?? 'not recorded'}</td><td>{event.human_decision ?? 'not recorded'}</td><td>{event.latency_ms == null ? 'not recorded' : `${event.latency_ms} ms`}</td><td>{event.step_index ?? 'not recorded'}</td><td>{event.sources.join(', ') || 'none'}</td></tr>)}</tbody></table></div>}
          </section>
        </div>
      )}

      {tab === 'how' && <HowItWorks config={config} settings={data.settings} safetyRules={data.safetyRules} permittedTools={audit?.permitted_tools ?? []} />}
    </div>
  )
}

function IntegrityPanel({ audit, loading, error }: { audit: AuditQueryResponse | null; loading: boolean; error: string | null }) {
  if (loading && !audit) return <section className="content-card" role="status">Checking whether the record is intact.</section>
  if (error && !audit) return <section className="content-card integrity-card integrity-card--error"><h2>The record could not be checked</h2><p>This is a fetch failure, not an empty record. {error}</p></section>
  if (!audit) return null
  if (audit.intact && audit.count === 0) return <section className="content-card integrity-card integrity-card--empty"><h2>Nothing has been recorded yet.</h2><p>{legacyText('record.empty')}</p></section>
  if (audit.intact) return <section className="content-card integrity-card integrity-card--ok"><span className="integrity-mark" aria-hidden="true">✓</span><div><h2>No. The record is intact.</h2><p>Every entry still matches the fingerprint taken when it was written, and each fingerprint includes the one before it, so changing any entry after the fact would break the sequence from that point on.</p></div></section>
  return <section className="content-card integrity-card integrity-card--error"><span className="integrity-mark" aria-hidden="true">!</span><div><h2>The record has been altered.</h2><p>The sequence breaks at entry <code>{audit.first_bad_event ?? 'not identified'}</code>. Everything before that point is still intact; nothing after it can be trusted.</p></div></section>
}

function ConversationArchive({ sessions, loading, error, subject, config }: {
  sessions: ConversationSession[]
  loading: boolean
  error: string | null
  subject: Subject
  config: SystemConfig
}) {
  return <section className="content-card"><div className="section-heading"><div><span className="eyebrow">Read only archive</span><h2>Conversations</h2></div></div>
    {loading && <p role="status">Loading conversations.</p>}
    {error && <p className="inline-notice inline-notice--warning" role="alert">Conversations could not be loaded. {error}</p>}
    {!loading && !error && sessions.length === 0 && <p>You have not written to the system yet. This is an empty record, not a failed check.</p>}
    {!loading && !error && sessions.length > 0 && <><p className="supporting-copy">{sessions.length} conversation(s), newest first. A gap of several hours starts a new one, which is the same rule the system itself uses.</p><div className="archive-list">{sessions.map((session, index) => {
      const turns = [...session.turns].sort((a, b) => a.seq - b.seq)
      const urgency = turns.filter((turn) => turn.urgency).at(-1)?.urgency
      return <details className="archive-session" key={`${session.started_utc}-${turns[0]?.id ?? index}`} open={index === 0}><summary>{timeLabel(session.started_utc, subject.timezone)} · {turns.length} turns{urgency ? ` · safety rules reached ${urgency.replace('_', ' ')}` : ''}</summary>{turns.map((turn) => {
        const citations = parseJsonArray(turn.citations_json)
        const hasUncited = parseJsonArray(turn.uncited_json).some((item) => typeof item === 'string')
        return <article className="archive-turn" key={turn.id}><strong>{turn.role === 'user' ? 'You' : 'The system'}</strong><time>{timeLabel(turn.created_at_utc, subject.timezone)}</time><p>{turn.text}</p><CitationPanel citations={citations} hasUncited={hasUncited} config={config} showMissingStatus={turn.role === 'agent'} /></article>
      })}</details>
    })}</div></>}
  </section>
}

function parseJsonArray(value: string) {
  try { const parsed: unknown = JSON.parse(value); return Array.isArray(parsed) ? parsed : [] } catch { return [] }
}
