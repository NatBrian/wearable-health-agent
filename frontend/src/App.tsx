import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api, CAUSE_LABELS, type Subject, type SystemConfig } from './api'
import { ChatPanel } from './components/ChatPanel'
import { legacyText } from './content/legacyCopy'
import { dateLabel } from './lib/format'
import { resolveSubject } from './subject/resolveSubject'
import { useBackend } from './useBackend'
import { type DashboardViewId } from './views/HomeView'
import { RecordView } from './views/RecordView'
import { SettingsView } from './views/SettingsView'
import { DashboardView, type DashboardSection } from './views/DashboardView'

type PrimaryView = 'dashboard' | 'pipeline' | 'settings'

const navigation: { id: PrimaryView; label: string; mark: string }[] = [
  { id: 'dashboard', label: 'Dashboard', mark: '▦' },
  { id: 'pipeline', label: 'Pipeline', mark: '⌘' },
  { id: 'settings', label: 'Settings', mark: '⚙' },
]

const titles: Record<PrimaryView, string> = {
  dashboard: 'Health Overview',
  pipeline: 'System Pipeline',
  settings: 'Settings',
}

function SidebarSession({ subject, data }: { subject: Subject; data: ReturnType<typeof useBackend> }) {
  const openEpisode = data.episodes.find((episode) => episode.state !== 'CLOSED')
  const lastClosed = data.episodes.find((episode) => episode.state === 'CLOSED')
  const episode = openEpisode ?? lastClosed
  const initials = subject.label.split(/\s+/).map((word) => word[0]).join('').slice(0, 2).toUpperCase()

  return (
    <>
      <div className="subject-summary" aria-label="Selected subject and baseline">
        <div className="subject-summary__avatar" aria-hidden="true">{initials}</div>
        <div className="subject-summary__copy">
          <strong>{subject.label}</strong>
          <span>{data.status?.usable_nights ?? subject.usable_nights} measured nights · {data.status?.rung ?? subject.rung}</span>
        </div>
      </div>
      <section className={`sidebar-session ${openEpisode ? 'sidebar-session--active' : ''}`} aria-label="Session summary">
        <div className="sidebar-session__eyebrow">
          <span className="sidebar-session__dot" aria-hidden="true" />
          {openEpisode ? 'Open session' : 'Last closed'}
        </div>
        {openEpisode ? (
          <>
            <p>{dateLabel(openEpisode.night_span[0], subject.timezone)} to {dateLabel(openEpisode.night_span[1], subject.timezone)}</p>
            <span>{openEpisode.state.replace(/_/g, ' ').toLowerCase()}</span>
            {openEpisode.top_cause && openEpisode.top_probability !== null && <div className="sidebar-session__belief">
              <span>{CAUSE_LABELS[openEpisode.top_cause]} · {new Intl.NumberFormat(undefined, { style: 'percent', maximumFractionDigits: 0 }).format(openEpisode.top_probability)}</span>
              <div aria-hidden="true"><span style={{ width: `${Math.max(0, Math.min(100, openEpisode.top_probability * 100))}%` }} /></div>
            </div>}
          </>
        ) : lastClosed ? (
          <>
            <p>{lastClosed.disposition?.replace(/_/g, ' ').toLowerCase() ?? 'Unresolved'}</p>
            <span>{dateLabel(lastClosed.night_span[0], subject.timezone)} to {dateLabel(lastClosed.night_span[1], subject.timezone)}</span>
          </>
        ) : <p>No investigation has run yet.</p>}
      </section>
    </>
  )
}

export default function App() {
  const [config, setConfig] = useState<SystemConfig | null>(null)
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [rememberedSubjectId, setRememberedSubjectId] = useState<string | null>(null)
  const [view, setView] = useState<PrimaryView>('dashboard')
  const [dashboardSection, setDashboardSection] = useState<DashboardSection>('overview')
  const [recordNight, setRecordNight] = useState<string | null>(null)
  const [chatOpen, setChatOpen] = useState(false)
  const [shellLoading, setShellLoading] = useState(true)
  const [shellError, setShellError] = useState<string | null>(null)
  const [retryIndex, setRetryIndex] = useState(0)

  const loadShell = useCallback(async () => {
    setShellLoading(true)
    setShellError(null)
    try {
      const [nextConfig, nextSubjects] = await Promise.all([api.config(), api.listSubjects()])
      setConfig(nextConfig)
      setSubjects(nextSubjects)
    } catch (exc) {
      setShellError(String(exc))
    } finally {
      setShellLoading(false)
    }
  }, [])

  useEffect(() => { void loadShell() }, [loadShell, retryIndex])

  const resolution = useMemo(
    () => resolveSubject(subjects, config?.configured_subject, rememberedSubjectId),
    [subjects, config, rememberedSubjectId],
  )
  const selectedSubject = resolution.kind === 'selected' ? resolution.subject : null
  const data = useBackend(selectedSubject?.subject_id ?? null, config?.dashboard.history_windows_days[0] ?? 28)
  const hasUnread = Boolean(data.pending || data.errors.pending) && !chatOpen
  const pendingIdentity = data.pending
    ? JSON.stringify([
        selectedSubject?.subject_id,
        data.pending.kind,
        data.pending.episode_id,
        data.pending.question?.probe.probe_id ?? null,
        data.pending.measurement?.measurement_id ?? null,
      ])
    : null
  const lastOpenedPending = useRef<string | null>(null)

  useEffect(() => {
    if (!pendingIdentity) {
      lastOpenedPending.current = null
      return
    }
    if (lastOpenedPending.current !== pendingIdentity) {
      lastOpenedPending.current = pendingIdentity
      setChatOpen(true)
    }
  }, [pendingIdentity])

  const navigate = (next: DashboardViewId, nightDate?: string) => {
    window.scrollTo(0, 0)
    if (next === 'home') {
      setView('dashboard')
      setDashboardSection('overview')
    } else if (next === 'today') {
      setView('dashboard')
      setDashboardSection('today')
    } else if (next === 'history') {
      setView('dashboard')
      setDashboardSection('history')
    } else if (next === 'record') {
      if (nightDate) setRecordNight(nightDate)
      setView('pipeline')
    } else {
      setView('settings')
    }
  }

  const handleSubjectChange = (subjectId: string) => setRememberedSubjectId(subjectId || null)
  const openPrimaryView = (next: PrimaryView) => {
    window.scrollTo(0, 0)
    setView(next)
    if (next === 'dashboard') setDashboardSection('overview')
  }
  const subtitle = view === 'dashboard'
    ? data.status?.last_nightly_utc
      ? `Last scored ${dateLabel(data.status.last_nightly_utc, selectedSubject?.timezone ?? 'UTC')} · ${data.episodes.some((episode) => episode.state !== 'CLOSED') ? 'investigation active' : 'no open investigation'}`
      : 'Waiting for the first night'
    : view === 'pipeline' ? 'Architecture and recorded activity' : 'Configure your agent'

  return (
    <div className="app-shell app-shell--vital">
      <aside className="sidebar">
        <a className="brand" href="#dashboard" aria-label="Vital Agent, health triage" onClick={(event) => { event.preventDefault(); navigate('home') }}>
          <span className="brand__glyph" aria-hidden="true"><svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 1.5L10.5 6H8V9.5H6V6H3.5L7 1.5Z" fill="#f59e0b" /><path d="M2 11h10" stroke="#22d3ee" strokeWidth="1.2" strokeLinecap="round" /><circle cx="7" cy="12.5" r="0.8" fill="#22d3ee" /></svg></span>
          <span><strong>Vital Agent</strong><small>health triage</small></span>
        </a>
        {selectedSubject && <SidebarSession subject={selectedSubject} data={data} />}
        <nav aria-label="Main navigation" className="main-nav">
          {navigation.map((item) => (
            <button className={`nav-item ${view === item.id ? 'nav-item--active' : ''}`} key={item.id} onClick={() => openPrimaryView(item.id)} aria-current={view === item.id ? 'page' : undefined}>
              <span className="nav-item__mark" aria-hidden="true">{item.mark}</span><span>{item.label}</span>
              {item.id === 'dashboard' && hasUnread && <span className="nav-item__unread" aria-label={data.pending ? 'Reply waiting' : 'Pending status unavailable'}>!</span>}
            </button>
          ))}
        </nav>
        <div className="sidebar__bottom">
          <span className="eyebrow">Private by design</span>
          <p>Your dashboard reads from the local application API.</p>
        </div>
      </aside>

      <div className="app-main">
        <main className="workspace">
          <header className="topbar">
            <div className="topbar__page"><h1 className="topbar__title">{titles[view]}</h1><span className="topbar__subtitle">{subtitle}</span></div>
            <div className="topbar__actions">
              {subjects.length > 1 ? (
                <label className="subject-picker">Whose data
                  <select aria-label="Whose data" value={selectedSubject?.subject_id ?? ''} onChange={(event) => handleSubjectChange(event.target.value)}>
                    {resolution.kind === 'choose' && <option value="">Choose a person</option>}
                    {subjects.map((subject) => <option key={subject.subject_id} value={subject.subject_id}>{subject.label}</option>)}
                  </select>
                </label>
              ) : selectedSubject ? <div className="subject-identity"><span className="subject-identity__dot" /><span>{selectedSubject.label}</span></div> : null}
              <button className="button button--quiet" onClick={() => selectedSubject ? data.refresh() : setRetryIndex((index) => index + 1)} disabled={shellLoading || data.loading}>
                {shellLoading || data.loading ? 'Refreshing…' : 'Refresh'}
              </button>
            </div>
          </header>

          <div className={`workspace-scroll${view === 'dashboard' && selectedSubject ? ' workspace-scroll--dashboard' : ''}`}>
            {selectedSubject && view === 'dashboard' && (
              <div className="dashboard-context" role="region" aria-label="Dashboard safety guidance">
                <section className="emergency-notice" aria-labelledby="emergency-title">
                  <span className="emergency-notice__icon" aria-hidden="true">!</span>
                  <div className="emergency-notice__copy"><h2 id="emergency-title">If you feel unwell now</h2><p>{legacyText('home.emergency')}</p></div>
                </section>
                <section className="dashboard-disclaimer" aria-labelledby="dashboard-disclaimer-title">
                  <div className="dashboard-disclaimer__mark" aria-hidden="true">i</div>
                  <div className="dashboard-disclaimer__copy"><h2 id="dashboard-disclaimer-title">What this system cannot do</h2><p>{legacyText('home.cannot')}</p></div>
                </section>
              </div>
            )}

            {shellLoading ? (
              <div className="state-card" role="status"><span className="loading-orbit" aria-hidden="true" />Loading your dashboard.</div>
            ) : shellError ? (
              <div className="state-card state-card--error" role="alert">
                <h2>Could not reach the application</h2><p>{shellError}</p><p>This is a connection problem, not a statement about your health.</p>
                <button className="button button--primary" onClick={() => setRetryIndex((index) => index + 1)}>Try again</button>
              </div>
            ) : resolution.kind === 'none' ? (
              <div className="state-card state-card--empty"><span className="eyebrow">Waiting for watch data</span><h2>There is nobody to show yet.</h2><p>Once your watch data has been pulled in for the first time, this screen will show it.</p></div>
            ) : resolution.kind === 'choose' ? (
              <div className="state-card state-card--empty"><span className="eyebrow">Choose a person</span><h2>Whose data would you like to see?</h2><p>Several people are available. Choose one above to continue.</p></div>
            ) : selectedSubject && config ? (
              <div className="page-stack">
                {view === 'dashboard' && (
                  <DashboardView subject={selectedSubject} config={config} data={data} section={dashboardSection} initialNight={recordNight} onSectionChange={(next) => { window.scrollTo(0, 0); setDashboardSection(next) }} onNavigate={navigate} onOpenChat={() => setChatOpen(true)} />
                )}
                {view === 'pipeline' && <RecordView subject={selectedSubject} config={config} data={data} initialNight={recordNight} onNavigate={navigate} />}
                {view === 'settings' && <SettingsView subject={selectedSubject} config={config} data={data} onDeleted={() => { setRememberedSubjectId(null); navigate('home'); setRetryIndex((index) => index + 1) }} />}
              </div>
            ) : null}
          </div>

          <nav className="mobile-nav" aria-label="Mobile navigation">
            {navigation.map((item) => <button className={`mobile-nav__item ${view === item.id ? 'mobile-nav__item--active' : ''}`} key={item.id} onClick={() => openPrimaryView(item.id)} aria-current={view === item.id ? 'page' : undefined}><span aria-hidden="true">{item.mark}</span><span>{item.label}</span></button>)}
          </nav>
        </main>

        {chatOpen && selectedSubject && config && (
          <aside className="chat-rail" id="chat-rail" aria-label="Agent chat">
            <ChatPanel subject={selectedSubject} nightDate={data.latestDetail?.row.night_date ?? null} episodeId={data.activeEpisode?.summary.episode_id ?? null} pending={data.pending} pendingError={data.errors.pending ?? null} config={config} settings={data.settings} safetyRules={data.safetyRules} refreshAfterSend={data.refresh} onClose={() => setChatOpen(false)} />
          </aside>
        )}
      </div>

      {selectedSubject && config && !chatOpen && (
        <button className="chat-toggle" aria-label={hasUnread ? `Open Agent Chat, ${data.pending ? 'reply waiting' : 'pending status unavailable'}` : 'Open Agent Chat'} aria-expanded={chatOpen} aria-controls="chat-rail" onClick={() => setChatOpen(true)}>
          <span aria-hidden="true"><svg width="26" height="26" viewBox="0 0 26 26" fill="none"><path d="M4 6a3 3 0 013-3h12a3 3 0 013 3v10a3 3 0 01-3 3H15l-3 3-3-3H7a3 3 0 01-3-3V6z" fill="rgb(255 255 255 / 25%)" /><circle cx="13" cy="3.5" r="1.2" fill="#fff" /><line x1="13" y1="4.7" x2="13" y2="6.5" stroke="#fff" strokeWidth="1.2" strokeLinecap="round" /><rect x="8" y="9" width="10" height="7" rx="3" fill="#fff" opacity=".9" /><circle cx="10.5" cy="12" r="1.3" fill="#f59e0b" /><circle cx="15.5" cy="12" r="1.3" fill="#f59e0b" /></svg></span>
          {hasUnread && <span className="chat-toggle__unread"><span className="visually-hidden">{data.pending ? 'Reply waiting' : 'Pending status unavailable'}</span></span>}
        </button>
      )}
    </div>
  )
}
