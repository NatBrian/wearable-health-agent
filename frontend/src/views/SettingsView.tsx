import { useEffect, useState } from 'react'
import { api, type ConnectionCheck, type Settings, type SettingsPatch, type Subject, type SubjectProfile, type SubjectProfilePatch, type SystemConfig } from '../api'
import type { BackendData } from '../useBackend'

type DiagnosticId = 'bridge' | 'llm' | 'telegram'
type DiagnosticState = Partial<Record<DiagnosticId, { loading: boolean; result?: ConnectionCheck; error?: string }>>
type SettingsSection = 'device' | 'agent' | 'model' | 'privacy'

const sections: { id: SettingsSection; label: string }[] = [
  { id: 'device', label: 'Device & Data' },
  { id: 'agent', label: 'Agent Behavior' },
  { id: 'model', label: 'Model & RAG' },
  { id: 'privacy', label: 'Privacy' },
]

const diagnosticLabels: Record<DiagnosticId, string> = {
  bridge: 'phone connection', llm: 'model connection', telegram: 'message delivery',
}

export function SettingsView({ subject, config, data, onDeleted }: {
  subject: Subject
  config: SystemConfig
  data: BackendData
  onDeleted: () => void
}) {
  const [profileDraft, setProfileDraft] = useState<SubjectProfilePatch | null>(null)
  const [settingsDraft, setSettingsDraft] = useState<Settings | null>(data.settings)
  const [bridgeToken, setBridgeToken] = useState('')
  const [llmApiKey, setLlmApiKey] = useState('')
  const [telegramToken, setTelegramToken] = useState('')
  const [profileLoading, setProfileLoading] = useState(true)
  const [profileError, setProfileError] = useState<string | null>(null)
  const [profileSaveError, setProfileSaveError] = useState<string | null>(null)
  const [settingsError, setSettingsError] = useState<string | null>(null)
  const [profileSaving, setProfileSaving] = useState(false)
  const [settingsSaving, setSettingsSaving] = useState(false)
  const [profileSaved, setProfileSaved] = useState(false)
  const [settingsSaved, setSettingsSaved] = useState(false)
  const [changedSettings, setChangedSettings] = useState<string[]>([])
  const [adjustedSettings, setAdjustedSettings] = useState<string[]>([])
  const [savedSecrets, setSavedSecrets] = useState(false)
  const [diagnostics, setDiagnostics] = useState<DiagnosticState>({})
  const [section, setSection] = useState<SettingsSection>('device')
  const [deleteText, setDeleteText] = useState('')
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [deleteStatus, setDeleteStatus] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)
  const bounds = config.dashboard.settings_bounds
  const marburgMinimumAge = data.safetyRules.find((rule) => rule.rule === 'marburg_heart_score')?.minimum_age_years

  useEffect(() => {
    let active = true
    setProfileLoading(true)
    setProfileError(null)
    setProfileDraft(null)
    void api.getSubjectProfile(subject.subject_id)
      .then((value) => {
        if (!active) return
        setProfileDraft({
          age_years: value.age_years,
          sex: value.sex,
          known_vascular_disease: value.known_vascular_disease,
          menstruates: value.menstruates,
          rate_lowering_medicine: value.rate_lowering_medicine,
          notes_for_doctor: value.notes_for_doctor,
        })
      })
      .catch((exc: unknown) => { if (active) setProfileError(String(exc)) })
      .finally(() => { if (active) setProfileLoading(false) })
    return () => { active = false }
  }, [subject.subject_id])

  useEffect(() => {
    if (data.settings) setSettingsDraft(data.settings)
  }, [data.settings])

  const updateProfile = <K extends keyof SubjectProfilePatch>(key: K, value: SubjectProfilePatch[K]) => {
    setProfileDraft((current) => current ? { ...current, [key]: value } : current)
    setProfileSaved(false)
  }
  const updateSetting = <K extends keyof Settings>(key: K, value: Settings[K]) => {
    setSettingsDraft((current) => current ? { ...current, [key]: value } : current)
    setSettingsSaved(false)
  }

  const saveProfile = async () => {
    if (!profileDraft) return
    setProfileSaving(true)
    setProfileSaveError(null)
    setProfileSaved(false)
    try {
      const saved = await api.updateSubjectProfile(subject.subject_id, profileDraft)
      setProfileDraft({
        age_years: saved.age_years, sex: saved.sex,
        known_vascular_disease: saved.known_vascular_disease,
        menstruates: saved.menstruates, rate_lowering_medicine: saved.rate_lowering_medicine,
        notes_for_doctor: saved.notes_for_doctor,
      })
      setProfileSaved(true)
    } catch (exc) { setProfileSaveError(String(exc)) }
    finally { setProfileSaving(false) }
  }

  const saveSettings = async () => {
    if (!settingsDraft) return
    setSettingsSaving(true)
    setSettingsError(null)
    setSettingsSaved(false)
    setChangedSettings([])
    setAdjustedSettings([])
    setSavedSecrets(false)
    const secretSubmitted = Boolean(bridgeToken || llmApiKey || telegramToken)
    const patch: SettingsPatch = {
      ...settingsDraft,
      bridge_host: settingsDraft.bridge_host || null,
      llm_base_url: settingsDraft.llm_base_url || null,
      ...(bridgeToken ? { bridge_token: bridgeToken } : {}),
      ...(llmApiKey ? { llm_api_key: llmApiKey } : {}),
      ...(telegramToken ? { telegram_token: telegramToken } : {}),
    }
    try {
      const saved = await api.updateSettings(patch)
      const labels: [keyof Settings, string][] = [
        ['bridge_host', 'Phone address'], ['llm_provider', 'Model provider'], ['llm_model', 'Model name'],
        ['llm_base_url', 'Model address'], ['notify_channel', 'Message channel'],
        ['interruption_budget_per_week', 'Weekly question limit'],
        ['depth_budget_per_episode', 'Questions per investigation'], ['policy_cost_weight', 'Interruption cost'],
      ]
      setChangedSettings(data.settings
        ? labels.filter(([key]) => data.settings?.[key] !== saved[key]).map(([, label]) => label)
        : [])
      setAdjustedSettings(labels.filter(([key]) => settingsDraft[key] !== saved[key]).map(([, label]) => label))
      setSavedSecrets(secretSubmitted)
      setSettingsDraft(saved)
      setBridgeToken('')
      setLlmApiKey('')
      setTelegramToken('')
      setSettingsSaved(true)
      data.refresh()
    } catch (exc) { setSettingsError(String(exc)) }
    finally { setSettingsSaving(false) }
  }

  const testConnection = async (component: DiagnosticId) => {
    if (!settingsDraft) return
    setDiagnostics((current) => ({ ...current, [component]: { loading: true } }))
    const overrides: Record<string, unknown> = component === 'bridge'
      ? { bridge_host: settingsDraft.bridge_host || undefined, bridge_token: bridgeToken || undefined }
      : component === 'llm'
        ? { provider: settingsDraft.llm_provider, model: settingsDraft.llm_model, base_url: settingsDraft.llm_base_url || undefined, api_key: llmApiKey || undefined }
        : { token: telegramToken || undefined }
    try {
      const result = await api.testComponent(component, overrides)
      setDiagnostics((current) => ({ ...current, [component]: { loading: false, result } }))
    } catch (exc) {
      setDiagnostics((current) => ({ ...current, [component]: { loading: false, error: String(exc) } }))
    }
  }

  const deleteRecord = async () => {
    if (!['demo', 'sim'].includes(subject.subject_id)) return
    if (deleteText !== subject.subject_id) {
      setDeleteError('The subject id did not match, so nothing was deleted.')
      return
    }
    setDeleting(true)
    setDeleteError(null)
    setDeleteStatus(null)
    try {
      await api.deleteSubject(subject.subject_id)
      setDeleteStatus('The disposable record was deleted from this machine.')
      onDeleted()
    } catch (exc) { setDeleteError(String(exc)) }
    finally { setDeleting(false) }
  }

  return (
    <div className="page-stack settings-view">
      <section className="settings-heading"><div><span className="eyebrow">Your choices and the system they affect</span><p>Each setting below says what it changes. Secret values are never shown again after saving.</p></div></section>
      <div className="settings-layout">
        <nav className="settings-nav" aria-label="Settings sections">
          <span className="eyebrow">Sections</span>
          {sections.map((item) => <button key={item.id} type="button" className={section === item.id ? 'settings-nav__item settings-nav__item--active' : 'settings-nav__item'} aria-current={section === item.id ? 'page' : undefined} onClick={() => setSection(item.id)}>{item.label}</button>)}
        </nav>
        <div className="settings-content">

      <section hidden={section !== 'device'} className="content-card settings-section" aria-labelledby="settings-profile-title">
        <div className="section-heading"><div><span className="eyebrow">Your standing information</span><h2 id="settings-profile-title">About you</h2></div><span className="settings-step">Profile</span></div>
        <p className="supporting-copy">Only information used by the rules or included in a clinician handover is collected here.</p>
        {profileLoading && <p role="status">Loading your profile.</p>}
        {profileError && <p className="inline-notice inline-notice--warning" role="alert">Your profile could not be loaded. This is a fetch failure, not an empty profile. {profileError}</p>}
        {profileDraft && <>
          {profileSaveError && <p className="inline-notice inline-notice--warning" role="alert">Your profile could not be saved. Your entries are still here. {profileSaveError}</p>}
          <div className="settings-grid">
            <label className="field-label">Your age<input aria-label="Your age" type="number" min={bounds.age_years.minimum ?? undefined} max={bounds.age_years.maximum ?? undefined} value={profileDraft.age_years ?? ''} onChange={(event) => updateProfile('age_years', event.target.value === '' ? null : Number(event.target.value))} /><small>{typeof marburgMinimumAge === 'number' ? `The published chest-pain checklist was tested only on people aged ${marburgMinimumAge} and over. Without your age it is not applied. Its source is listed on The record under How this works.` : 'The checklist age limit and source are unavailable until safety-rule details load.'}</small></label>
            <label className="field-label">Sex<select aria-label="Sex" value={profileDraft.sex ?? ''} onChange={(event) => updateProfile('sex', event.target.value === '' ? null : event.target.value as 'female' | 'male')}><option value="">Not said</option><option value="female">Female</option><option value="male">Male</option></select><small>The same published checklist scores this as its study did.</small></label>
            <TriStateField label="I have a known heart or vascular condition" value={profileDraft.known_vascular_disease ?? null} onChange={(value) => updateProfile('known_vascular_disease', value)} help="Raises how cautiously the safety rules treat chest symptoms." />
            <TriStateField label="I menstruate" value={profileDraft.menstruates ?? null} onChange={(value) => updateProfile('menstruates', value)} help="Lets the cycle be considered as an ordinary explanation for a raised night, instead of it being treated as unexplained." />
            <TriStateField label="I take medicine that slows my heart rate" value={profileDraft.rate_lowering_medicine ?? null} onChange={(value) => updateProfile('rate_lowering_medicine', value)} help="Read by nothing, on purpose. It appears in your record as a disclosure so anyone reading it knows, rather than quietly changing a threshold." />
            <label className="field-label settings-field--wide">Anything you want a doctor to see<textarea aria-label="Anything you want a doctor to see" rows={4} value={profileDraft.notes_for_doctor ?? ''} onChange={(event) => updateProfile('notes_for_doctor', event.target.value || null)} /><small>Goes into the summary for your doctor and into no AI prompt. Information for a doctor is not information for the model.</small></label>
          </div>
          <div className="settings-actions"><button className="button button--primary" onClick={() => void saveProfile()} disabled={profileSaving}>{profileSaving ? 'Saving…' : 'Save these'}</button>{profileSaved && <span className="save-confirmation" role="status">Saved.</span>}</div>
        </>}
      </section>

      {!settingsDraft ? data.errors.settings ? <section className="content-card inline-notice inline-notice--warning" role="alert"><strong>Settings could not be loaded.</strong><p>This is a fetch failure, not a missing setting. {data.errors.settings}</p><button className="button button--secondary" onClick={data.refresh}>Try again</button></section> : <section className="content-card" role="status">Loading settings from the application.</section> : <>
        {section === 'device' && <section className="content-card device-status-summary" aria-label="Device and baseline status">
          <div className="section-heading"><div><span className="eyebrow">Current status</span><h2>Device &amp; Data</h2></div></div>
          {data.status ? <dl className="device-status-grid">
            <div><dt>Watch connection</dt><dd>{data.status.components.find((item) => item.component === 'bridge')?.detail ?? 'Status unavailable'}</dd></div>
            <div><dt>Baseline</dt><dd>{data.status.usable_nights} measured nights · {data.status.rung}</dd></div>
            <div><dt>Last sync</dt><dd>{data.status.last_ingest_utc ? new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short', timeZone: subject.timezone }).format(new Date(data.status.last_ingest_utc)) : 'not recorded'}</dd></div>
            <div><dt>Quiet streak</dt><dd>{data.status.quiet_nights_streak} measured nights</dd></div>
          </dl> : <p role="status">Device status is not available.</p>}
          <p className="supporting-copy">The baseline window and detection thresholds come from the backend and cannot be changed here. Their current operation is visible in the Pipeline explanations.</p>
        </section>}
        <section hidden={section !== 'device' || !settingsDraft} className="content-card settings-section" aria-labelledby="settings-source-title">
          <div className="section-heading"><div><span className="eyebrow">Watch data</span><h2 id="settings-source-title">Where your readings come from</h2></div></div>
          <div className="settings-grid">
            <label className="field-label settings-field--wide">Your phone's address on this network<input aria-label="Your phone's address on this network" value={settingsDraft.bridge_host ?? ''} onChange={(event) => updateSetting('bridge_host', event.target.value || null)} /><small>The app on your phone serves your watch data at this address. If it is wrong or the phone is asleep, no new night can be measured.</small></label>
            <label className="field-label">Phone access token<input aria-label="Phone access token" type="password" autoComplete="new-password" value={bridgeToken} onChange={(event) => setBridgeToken(event.target.value)} /><small>Stored on this machine only, and never shown again after you save it. Leave blank to keep a saved token.</small></label>
          </div>
          <DiagnosticButton component="bridge" label="Test the connection to my phone" diagnostics={diagnostics} onTest={testConnection} />
        </section>

        <section hidden={section !== 'model'} className="content-card settings-section" aria-labelledby="settings-model-title">
          <section className="model-endpoint-summary" aria-label="Current model endpoint">
            <div><span>Provider</span><strong>{settingsDraft.llm_provider}</strong></div>
            <div><span>Model</span><strong>{settingsDraft.llm_model}</strong></div>
            <div><span>Base address</span><strong>{settingsDraft.llm_base_url ?? 'not set'}</strong></div>
            <div><span>Connection status</span><strong>{data.status?.components.find((item) => item.component === 'llm')?.detail ?? 'not available'}</strong></div>
          </section>
          <div className="section-heading"><div><span className="eyebrow">Questions, summaries and chat</span><h2 id="settings-model-title">The AI model</h2></div></div>
          <p className="supporting-copy">Used for wording questions, writing summaries and chat. Nothing that decides whether a night is unusual uses AI at all.</p>
          <div className="settings-grid">
            <label className="field-label">Which kind of model<select value={settingsDraft.llm_provider} onChange={(event) => updateSetting('llm_provider', event.target.value as Settings['llm_provider'])}><option value="cassette">Recorded answers, stored on this machine</option><option value="ollama_native">Model running on this machine</option><option value="openai_compatible">Remote or self-hosted service</option></select><small>Recorded answers replay saved replies and never leave this machine. A local model runs here. A remote model service receives your question.</small></label>
            <label className="field-label">Model name<input aria-label="Model name" value={settingsDraft.llm_model} onChange={(event) => updateSetting('llm_model', event.target.value)} /><small>Changing this changes wording, not the rules that decide whether a night is unusual.</small></label>
            <label className="field-label settings-field--wide">Where that model lives<input aria-label="Where that model lives" value={settingsDraft.llm_base_url ?? ''} onChange={(event) => updateSetting('llm_base_url', event.target.value || null)} /><small>Required for a remote or self-hosted model. Leave empty for recorded answers.</small></label>
            <label className="field-label">Key for that service<input aria-label="Key for that service" type="password" autoComplete="new-password" value={llmApiKey} onChange={(event) => setLlmApiKey(event.target.value)} /><small>Stored on this machine only and never shown again. Leave blank to keep a saved key.</small></label>
          </div>
          <DiagnosticButton component="llm" label="Test the model" diagnostics={diagnostics} onTest={testConnection} />
        </section>

        <section hidden={section !== 'agent'} className="content-card settings-section" aria-labelledby="settings-contact-title">
          <div className="section-heading"><div><span className="eyebrow">When something needs you</span><h2 id="settings-contact-title">How you get asked</h2></div></div>
          <div className="settings-grid">
            <label className="field-label">Where questions should reach you<select value={settingsDraft.notify_channel} onChange={(event) => updateSetting('notify_channel', event.target.value as Settings['notify_channel'])}><option value="none">On this screen</option><option value="telegram">Telegram</option></select><small>With none, questions wait on this screen until you open it. With Telegram they arrive on your phone and you can answer there.</small></label>
            <label className="field-label">Telegram bot token<input aria-label="Telegram bot token" type="password" autoComplete="new-password" value={telegramToken} onChange={(event) => setTelegramToken(event.target.value)} /><small>Stored on this machine only. Never shown again after you save it. Leave blank to keep a saved token.</small></label>
          </div>
          <DiagnosticButton component="telegram" label="Check Telegram bot connection" diagnostics={diagnostics} onTest={testConnection} />
        </section>

        <section hidden={section !== 'agent'} className="content-card settings-section" aria-labelledby="settings-budget-title">
          <div className="section-heading"><div><span className="eyebrow">How often the system can interrupt you</span><h2 id="settings-budget-title">How often you get asked</h2></div></div>
          <div className="settings-grid">
            <label className="field-label">Most questions in a week<input type="number" min={bounds.interruption_budget_per_week.minimum ?? undefined} max={bounds.interruption_budget_per_week.maximum ?? undefined} value={settingsDraft.interruption_budget_per_week} onChange={(event) => updateSetting('interruption_budget_per_week', Number(event.target.value))} /><small>A hard ceiling. Lower it and the system stays quieter, at the cost of sometimes concluding without asking the one question that would have helped.</small></label>
            <label className="field-label">Most questions in one investigation<input type="number" min={bounds.depth_budget_per_episode.minimum ?? undefined} max={bounds.depth_budget_per_episode.maximum ?? undefined} value={settingsDraft.depth_budget_per_episode} onChange={(event) => updateSetting('depth_budget_per_episode', Number(event.target.value))} /><small>Stops a single investigation asking you repeatedly over several nights.</small></label>
            <label className="field-label">How much an interruption costs you<input type="number" min={bounds.policy_cost_weight.minimum ?? undefined} max={bounds.policy_cost_weight.maximum ?? undefined} step={bounds.policy_cost_weight.step ?? 'any'} value={settingsDraft.policy_cost_weight} onChange={(event) => updateSetting('policy_cost_weight', Number(event.target.value))} /><small>Raise it and only the most useful questions get asked. Lower it and you are asked more often. This is weighed against how much an answer would change the conclusion.</small></label>
          </div>
        </section>
      </>}

      {section === 'privacy' && <section className="content-card privacy-summary" aria-labelledby="privacy-summary-title">
        <div><span className="eyebrow">Local first · single person</span><h2 id="privacy-summary-title">Where your data goes</h2><p>Wearable readings and the recorded history are stored by this local application. The configured language model receives question or summary text when it is used.</p>
          {settingsDraft && <p className="provider-status">Current model provider: <strong>{settingsDraft.llm_provider}</strong>. Model name: <strong>{settingsDraft.llm_model}</strong>. Configured endpoint: <strong>{settingsDraft.llm_base_url ?? 'not set'}</strong>.</p>}
          {settingsDraft?.llm_base_url && settingsDraft.llm_provider !== 'cassette' && <p className="inline-notice inline-notice--warning">Question and summary text is sent to this configured endpoint. Whether it stays on this machine depends on where that endpoint runs: <strong>{settingsDraft.llm_base_url}</strong>.</p>}
          <p className="supporting-copy">The disposable demo and simulation records can be deleted below. The real subject is protected from deletion in this screen.</p>
        </div>
      </section>}
      {['demo', 'sim'].includes(subject.subject_id) && <section hidden={section !== 'privacy'} className="content-card settings-delete" aria-labelledby="settings-delete-title">
        <div><span className="eyebrow">Disposable records only</span><h2 id="settings-delete-title">Delete everything</h2><p>This erases everything held about you on this machine: every heart rate reading, every night, every investigation, every message and the record of all of it. It cannot be undone and nothing is kept elsewhere.</p></div>
        <label className="field-label">Type the name of the person to delete, which is {subject.subject_id}<input aria-label="Type the name of the person to delete" value={deleteText} onChange={(event) => { setDeleteText(event.target.value); setDeleteError(null) }} /></label>
        <button className="button button--danger" onClick={() => void deleteRecord()} disabled={deleting || deleteText !== subject.subject_id}>{deleting ? 'Deleting…' : 'Delete everything about this person'}</button>
        {deleteError && <p role="alert" className="inline-notice inline-notice--warning">{deleteError}</p>}
        {deleteStatus && <p role="status" className="save-confirmation">{deleteStatus}</p>}
      </section>}
      {section === 'agent' && settingsDraft && <section className="content-card safety-settings-note"><h2>Safety rules stay in control</h2><p>The deterministic safety floor runs before the model and cannot be disabled or lowered through settings. The model can only add caution.</p></section>}
      {section === 'model' && settingsDraft && <section className="content-card retrieval-settings-note"><h2>Retrieval grounding</h2><p>A supported clinical sentence must contain a verbatim span from a retrieved passage. That check confirms the words exist in the passage; it does not prove the sentence around them is fair to the source. The full passage and its source stay available in the Pipeline record.</p></section>}
      {settingsDraft && <div className="settings-savebar">
        <div className="settings-actions"><button className="button button--primary" onClick={() => void saveSettings()} disabled={settingsSaving}>{settingsSaving ? 'Saving…' : 'Save all settings'}</button>{settingsSaved && <span className="save-confirmation" role="status">Saved.{changedSettings.length > 0 ? ` Changed: ${changedSettings.join(', ')}.` : null}{savedSecrets ? ' Connection secrets saved; their values are not returned.' : null}{changedSettings.length === 0 && !savedSecrets && adjustedSettings.length === 0 ? ' No setting values changed.' : null}{adjustedSettings.length > 0 ? ` The application did not apply your requested values for: ${adjustedSettings.join(', ')}.` : null}</span>}</div>
        {settingsError && <p className="inline-notice inline-notice--warning" role="alert">Settings could not be saved. Your entries are still here. {settingsError}</p>}
      </div>}
        </div>
      </div>
    </div>
  )
}

function TriStateField({ label, value, onChange, help }: {
  label: string
  value: boolean | null
  onChange: (value: boolean | null) => void
  help: string
}) {
  return <label className="field-label">{label}<select aria-label={label} value={value === null ? '' : String(value)} onChange={(event) => onChange(event.target.value === '' ? null : event.target.value === 'true')}><option value="">Not said</option><option value="true">Yes</option><option value="false">No</option></select><small>{help}</small></label>
}

function DiagnosticButton({ component, label, diagnostics, onTest }: {
  component: DiagnosticId
  label: string
  diagnostics: DiagnosticState
  onTest: (component: DiagnosticId) => void
}) {
  const state = diagnostics[component]
  return <div className="diagnostic-row"><button className="button button--secondary" onClick={() => onTest(component)} disabled={state?.loading}>{state?.loading ? 'Checking…' : label}</button>{state?.result && <span className={state.result.ok ? 'diagnostic-result diagnostic-result--ok' : 'diagnostic-result diagnostic-result--error'} role="status">{state.result.detail}</span>}{state?.error && <span className="diagnostic-result diagnostic-result--error" role="alert">The {diagnosticLabels[component]} check failed. {state.error}</span>}</div>
}
