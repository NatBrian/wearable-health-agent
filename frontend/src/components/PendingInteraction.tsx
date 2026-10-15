import { useState } from 'react'
import { api, type PendingInteraction as PendingModel, type SafetyRuleProvenance, type SystemConfig } from '../api'
import { CitationPanel } from './CitationPanel'

export function PendingInteraction({
  pending, config, safetyRules, onComplete,
}: {
  pending: PendingModel
  config: SystemConfig
  safetyRules: SafetyRuleProvenance[]
  onComplete: () => void
}) {
  const [freeText, setFreeText] = useState('')
  const [prose, setProse] = useState(pending.draft_outcome?.observation ?? '')
  const [rationale, setRationale] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const chestPainRule = pending.question?.probe.probe_id.startsWith('mhs_')
    ? safetyRules.find((rule) => rule.rule === 'marburg_heart_score')
    : undefined

  const run = async (action: () => Promise<unknown>) => {
    if (busy) return
    setBusy(true)
    setError(null)
    try {
      await action()
      onComplete()
    } catch (exc) {
      setError(String(exc))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="content-card pending-card" aria-labelledby="pending-title">
      <div className="section-heading"><div><span className="eyebrow">Needs your attention</span><h2 id="pending-title">{pending.kind === 'question' ? 'One question for you' : pending.kind === 'review' ? 'A summary is ready for you to check' : 'Something to measure'}</h2></div><span className="pending-pill">Waiting</span></div>
      {pending.kind === 'question' && pending.question && (
        <>
          <p className="pending-question">{pending.question.text}</p>
          <p className="supporting-copy">Several things could explain last night. This is the single question whose answer would most change what the system concludes, which is why it is the only one being asked.</p>
          {chestPainRule && <p className="supporting-copy">These chest-pain questions follow the Marburg Heart Score. Source: {chestPainRule.basis}</p>}
          {pending.question.allows_free_text && <label className="field-label">Anything else you want to add (optional)<textarea value={freeText} onChange={(event) => setFreeText(event.target.value)} placeholder="For example: sore throat since yesterday" rows={3} /></label>}
          <div className="button-row">
            {pending.question.options.map((option) => (
              <button className="button button--primary" key={option.option_id} disabled={busy} onClick={() => void run(() => api.submitAnswer(pending.episode_id, { probe_id: pending.question!.probe.probe_id, option_id: option.option_id, free_text: freeText.trim() || null }))}>{option.label}</button>
            ))}
            {pending.question.allows_free_text && <button className="button button--secondary" disabled={busy || !freeText.trim()} onClick={() => void run(() => api.submitAnswer(pending.episode_id, { probe_id: pending.question!.probe.probe_id, option_id: null, free_text: freeText.trim() }))}>Send written answer</button>}
            <button className="button button--secondary" disabled={busy} onClick={() => void run(() => api.submitAnswer(pending.episode_id, { probe_id: pending.question!.probe.probe_id, option_id: pending.question!.options[0]?.option_id ?? null, declined: true }))}>Skip</button>
          </div>
          <p className="supporting-copy">Skipping is fine. You will not be asked this again for this investigation.</p>
        </>
      )}
      {pending.kind === 'measurement' && pending.measurement && (
        <>
          <p className="pending-question">{pending.measurement.instruction}</p>
          <p className="supporting-copy">This is asked only where the reading would change what happens next.</p>
          <div className="measurement-meta"><span>{pending.measurement.kind.replace(/_/g, ' ')}</span><span>Expires {pending.measurement.expires_at_utc}</span></div>
        </>
      )}
      {pending.kind === 'review' && pending.draft_outcome && (
        <>
          <div className="review-draft"><span className="eyebrow">What it concluded</span><strong>{pending.draft_outcome.disposition.replace(/_/g, ' ').toLowerCase()}</strong><p>{pending.draft_outcome.observation}</p></div>
          <p className="supporting-copy">Nothing here is settled until you decide. You can change the wording, say it is wrong, or send it on to a clinician.</p>
          <CitationPanel citations={pending.draft_outcome.citations} config={config} showMissingStatus />
          <label className="field-label">Change the wording (optional)<textarea value={prose} onChange={(event) => setProse(event.target.value)} rows={5} /></label>
          <label className="field-label">Why (optional)<input value={rationale} onChange={(event) => setRationale(event.target.value)} /></label>
          <div className="button-row">
            <button className="button button--primary" disabled={busy} onClick={() => void run(() => api.submitReview(pending.episode_id, { decision: prose !== pending.draft_outcome!.observation ? 'edit' : 'approve', edited_prose: prose !== pending.draft_outcome!.observation ? prose : null, rationale: rationale || null }))}>Looks right</button>
            <button className="button button--secondary" disabled={busy} onClick={() => void run(() => api.submitReview(pending.episode_id, { decision: 'reject', rationale: rationale || 'Rejected on review' }))}>Not right</button>
            <button className="button button--secondary" disabled={busy} onClick={() => void run(() => api.submitReview(pending.episode_id, { decision: 'escalate', rationale: rationale || 'Escalated on review' }))}>This needs a doctor</button>
          </div>
        </>
      )}
      {error && <p className="inline-notice inline-notice--warning" role="alert">Could not save that response. Your text is still here. {error}</p>}
    </section>
  )
}
