import { useCallback, useEffect, useRef, useState } from 'react'
import { api, type ConversationSession, type PendingInteraction as PendingModel, type SafetyRuleProvenance, type Settings, type SystemConfig, type Subject } from '../api'
import { CitationPanel } from './CitationPanel'
import { dateLabel, timeLabel } from '../lib/format'
import { PendingInteraction as PendingControls } from './PendingInteraction'

function parseList<T>(value: string): T[] {
  try {
    const parsed: unknown = JSON.parse(value)
    return Array.isArray(parsed) ? parsed as T[] : []
  } catch { return [] }
}

export function ChatPanel({
  subject, nightDate, episodeId, pending, pendingError, config, settings, safetyRules, refreshAfterSend, onClose,
}: {
  subject: Subject
  nightDate: string | null
  episodeId: string | null
  pending: PendingModel | null
  pendingError?: string | null
  config: SystemConfig
  settings: Settings | null
  safetyRules: SafetyRuleProvenance[]
  refreshAfterSend: () => void
  onClose: () => void
}) {
  const [sessions, setSessions] = useState<ConversationSession[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [sendError, setSendError] = useState<string | null>(null)
  const [sentRefreshError, setSentRefreshError] = useState(false)
  const [loadedScope, setLoadedScope] = useState('')
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const requestSequence = useRef(0)
  const scopeKey = `${subject.subject_id}:${nightDate ?? 'current'}`

  const loadSessions = useCallback(async () => {
    const sequence = ++requestSequence.current
    setLoading(true)
    setLoadError(null)
    try {
      const value = await api.getConversationSessions(subject.subject_id, 400, nightDate ?? undefined)
      if (sequence === requestSequence.current) {
        setSessions(value)
        setLoadedScope(scopeKey)
        setSentRefreshError(false)
      }
      return true
    } catch (exc) {
      if (sequence === requestSequence.current) setLoadError(String(exc))
      return false
    } finally {
      if (sequence === requestSequence.current) setLoading(false)
    }
  }, [nightDate, scopeKey, subject.subject_id])

  useEffect(() => {
    setSessions([])
    setLoadedScope('')
    void loadSessions()
  }, [loadSessions])

  const send = async () => {
    const message = input.trim()
    if (!message || sending) return
    setSending(true)
    setSendError(null)
    setSentRefreshError(false)
    try {
      await api.postMessage(subject.subject_id, message, pending?.episode_id ?? episodeId)
      setInput('')
      refreshAfterSend()
      if (!await loadSessions()) setSentRefreshError(true)
    } catch (exc) { setSendError(String(exc)) }
    finally { setSending(false) }
  }

  const turns = (loadedScope === scopeKey ? sessions : []).flatMap((session) => session.turns)
    .sort((first, second) => first.seq - second.seq)
  const turnCount = turns.length
  const exchangeLimit = configuredNumber(config, 'CONVERSATION_MAX_TURNS')
  const worseningStep = configuredNumber(config, 'ESCALATION_REPEAT_ROBUST_Z_RISE')
  const repeatDelay = configuredNumber(config, 'ESCALATION_REPEAT_NIGHTS')
  const triageReplyLimit = configuredNumber(config, 'TRIAGE_MAX_TURNS_BEFORE_ESCALATE')

  return (
    <div className="chat-rail__inner">
      <div className="chat-rail__header"><span>Agent chat</span><button type="button" className="chat-rail__close" aria-label="Close chat" onClick={onClose}>×</button></div>
      <section className="content-card chat-card" aria-labelledby="chat-heading">
      <div className="section-heading"><div><span className="eyebrow">Your current conversation</span><h2 id="chat-heading">Ask about any of this</h2></div><span className="chat-status">{pending ? 'Awaiting your reply' : pendingError ? 'Unable to check' : 'Available'}</span></div>
      <p className="chat-intro">Ask about your readings, or say how you feel. Anything you write is checked by fixed rules before any AI sees it. Those rules can raise how urgent this is, and the AI can never lower it.</p>
      {pending && <PendingControls pending={pending} config={config} safetyRules={safetyRules} onComplete={refreshAfterSend} />}
      {pendingError && <p className="inline-notice inline-notice--warning" role="alert"><strong>Could not check whether you need to answer.</strong> This is a fetch failure, not a confirmation that nothing is waiting. {pendingError} <button className="text-link" onClick={refreshAfterSend}>Try again</button></p>}
      {nightDate && <p className="supporting-copy">This conversation is about the night of {dateLabel(nightDate, subject.timezone)}. Earlier conversations stay on The record.</p>}
      <details className="chat-limits"><summary>Conversation and notification limits</summary><div className="disclosure-card__body">
        <p>{exchangeLimit === null ? 'The conversation length limit is not available.' : <>A conversation ends after <strong>{formatConfigNumber(exchangeLimit)} back-and-forth exchanges</strong>. After chat ends, the fixed safety rules still check what you tell the system and can still raise urgency.</>}</p>
        <p>{settings ? <>The current weekly cap is <strong>{settings.interruption_budget_per_week} unsolicited interruptions</strong>. This is a configurable operating limit, not a clinical threshold.</> : 'The weekly interruption setting is not available.'}</p>
        <p>{triageReplyLimit === null ? 'The reply limit for completing a safety-rule conversation is not available.' : <>If the system cannot collect enough information to complete a safety rule within <strong>{formatConfigNumber(triageReplyLimit)} replies</strong>, it escalates. This is an unevidenced safety limit. Some presentations also escalate immediately without questions when no suitable validated rule is available.</>}</p>
        <p>{worseningStep === null || repeatDelay === null ? 'Repeat-notification settings are not available.' : <>A repeat notice may be sent if the reading worsens by at least <strong>{formatConfigNumber(worseningStep)} robust deviations</strong>, or if it has not improved by that amount after <strong>{formatConfigNumber(repeatDelay)} nights</strong>. These are notification settings, not clinical thresholds.</>}</p>
      </div></details>
      {loadError && <p className="inline-notice inline-notice--warning" role="alert">The conversation could not be loaded. This is a fetch failure, not an empty conversation. <button className="text-link" onClick={() => void loadSessions()}>Try again</button> {loadError}</p>}
      {sentRefreshError && <p className="inline-notice inline-notice--warning" role="alert">Your message was sent, but the refreshed conversation could not be loaded. Try again to see whether it appears here.</p>}
      {sendError && <p className="inline-notice inline-notice--warning" role="alert">Your message could not be sent. It is still in the box so you can try again. {sendError}</p>}
      <div className="chat-transcript" aria-live="polite">
        {loading && loadedScope !== scopeKey ? <p className="supporting-copy">Loading this conversation.</p> : loadError && loadedScope !== scopeKey ? null : turns.length === 0 ? (
          <p className="chat-empty">No conversation has been recorded for this night. The agent speaks only when it has something worth an interruption.</p>
        ) : turns.map((turn) => {
          const citations = parseList<ConversationCitation>(turn.citations_json)
          const hasUncited = parseList<string>(turn.uncited_json).length > 0
          return (
            <article className={`chat-turn ${turn.role === 'user' ? 'chat-turn--user' : 'chat-turn--agent'}`} key={turn.id}>
              <div className="chat-turn__meta"><strong>{turn.role === 'user' ? 'You' : 'Agent'}</strong><time dateTime={turn.created_at_utc}>{timeLabel(turn.created_at_utc, subject.timezone)}</time>{turn.urgency && <span className="urgency-inline">{turn.urgency.replace('_', ' ')}</span>}</div>
              <p>{turn.text}</p>
              <CitationPanel citations={citations} hasUncited={hasUncited} config={config} showMissingStatus={turn.role === 'agent'} />
            </article>
          )
        })}
      </div>
      <label className="field-label">Say anything, or ask a question<textarea value={input} onChange={(event) => setInput(event.target.value)} rows={3} placeholder="Write a message" onKeyDown={(event) => { if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') void send() }} /></label>
      <div className="chat-actions"><span className="supporting-copy">{turnCount} turns in this conversation</span><button className="button button--primary" onClick={() => void send()} disabled={!input.trim() || sending}>{sending ? 'Sending…' : 'Send message'}</button></div>
      <p className="supporting-copy">This sorting is done by the AI itself and can miss things. A sentence with a source shown can still misdescribe that source; open and read the whole passage.</p>
      </section>
    </div>
  )
}

function configuredNumber(config: SystemConfig, key: string): number | null {
  const value = config[key]
  return typeof value === 'number' ? value : null
}

function formatConfigNumber(value: number): string {
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: 3 }).format(value)
}

interface ConversationCitation {
  source_id: string
  title: string
  uri: string | null
  passage: string
  retrieval_score: number
  quoted_span?: string | null
}
