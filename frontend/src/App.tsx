import { useCallback, useEffect, useMemo, useState } from 'react'
import { api, type Subject, type SystemConfig } from './api'
import { StatusBar } from './components/StatusBar'
import { HomeView, type DashboardViewId } from './views/HomeView'
import { resolveSubject } from './subject/resolveSubject'
import { useBackend } from './useBackend'
import { TodayView } from './views/TodayView'
import { HistoryView } from './views/HistoryView'
import { RecordView } from './views/RecordView'
import { SettingsView } from './views/SettingsView'
import { legacyText } from './content/legacyCopy'

const navigation: { id: DashboardViewId; label: string; mark: string }[] = [
  { id: 'home', label: 'Home', mark: '◒' },
  { id: 'today', label: 'Today', mark: '◷' },
  { id: 'history', label: 'History', mark: '⌁' },
  { id: 'record', label: 'The record', mark: '▤' },
  { id: 'settings', label: 'Settings', mark: '⚙' },
]

const viewTitles: Record<DashboardViewId, string> = {
  home: 'Home', today: 'Today', history: 'History', record: 'The record', settings: 'Settings',
}

function WorkspaceView({ view }: { view: DashboardViewId }) {
  return (
    <section className="content-card route-placeholder" aria-labelledby="route-title">
      <span className="eyebrow">{viewTitles[view]}</span>
      <h1 id="route-title">{viewTitles[view]}</h1>
      <p>This screen is being restored from the original dashboard.</p>
    </section>
  )
}

export default function App() {
  const [config, setConfig] = useState<SystemConfig | null>(null)
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [rememberedSubjectId, setRememberedSubjectId] = useState<string | null>(null)
  const [view, setView] = useState<DashboardViewId>('home')
  const [recordNight, setRecordNight] = useState<string | null>(null)
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
  const data = useBackend(selectedSubject?.subject_id ?? null)
  const selectedView = navigation.find((item) => item.id === view) ?? navigation[0]

  const handleSubjectChange = (subjectId: string) => {
    setRememberedSubjectId(subjectId || null)
  }

  const navigate = (next: DashboardViewId, nightDate?: string) => {
    if (next === 'record') setRecordNight(nightDate ?? null)
    window.scrollTo(0, 0)
    setView(next)
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#home" onClick={(event) => { event.preventDefault(); navigate('home') }}>
          <span className="brand__glyph" aria-hidden="true">◒</span>
          <span><strong>Night watch</strong><small>Wearable health journal</small></span>
        </a>
        <div className="sidebar__section-label">Workspace</div>
        <nav aria-label="Main navigation" className="main-nav">
          {navigation.map((item) => (
            <button className={`nav-item ${view === item.id ? 'nav-item--active' : ''}`} key={item.id} onClick={() => navigate(item.id)} aria-current={view === item.id ? 'page' : undefined}>
              <span className="nav-item__mark" aria-hidden="true">{item.mark}</span><span>{item.label}</span>
              {view === item.id && <span className="nav-item__active-mark" aria-hidden="true" />}
            </button>
          ))}
        </nav>
        <div className="sidebar__bottom">
          <span className="eyebrow">Private by design</span>
          <p>Your dashboard reads from the local application API.</p>
        </div>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div className="topbar__page"><span className="eyebrow">Your night watch</span><span className="topbar__title">{selectedView.label}</span></div>
          <div className="topbar__actions">
            {subjects.length > 1 ? (
              <label className="subject-picker">Whose data
                <select aria-label="Whose data" value={selectedSubject?.subject_id ?? ''} onChange={(event) => handleSubjectChange(event.target.value)}>
                  {resolution.kind === 'choose' && <option value="">Choose a person</option>}
                  {subjects.map((subject) => <option key={subject.subject_id} value={subject.subject_id}>{subject.label}</option>)}
                </select>
              </label>
            ) : selectedSubject ? (
              <div className="subject-identity"><span className="subject-identity__dot" /><span>{selectedSubject.label}</span></div>
            ) : null}
            <button className="button button--quiet" onClick={() => selectedSubject ? data.refresh() : setRetryIndex((index) => index + 1)} disabled={shellLoading || data.loading}>
              {shellLoading || data.loading ? 'Refreshing…' : 'Refresh'}
            </button>
          </div>
        </header>

        {view === 'home' && (
          <section className="emergency-notice emergency-notice--priority" aria-labelledby="emergency-title">
            <div className="emergency-notice__icon" aria-hidden="true">!</div>
            <div><h2 id="emergency-title">If you feel unwell now</h2><p>{legacyText('home.emergency')}</p></div>
          </section>
        )}

        {selectedSubject && (
          <div className="status-wrap">
          <StatusBar status={data.status} subject={selectedSubject} loading={data.loading} error={data.errors.status ?? null} onOpenRecord={() => navigate('record')} />
          </div>
        )}

        <div className="workspace-scroll">
          {shellLoading ? (
            <div className="state-card" role="status"><span className="loading-orbit" aria-hidden="true" />Loading your dashboard.</div>
          ) : shellError ? (
            <div className="state-card state-card--error" role="alert">
              <h1>Could not reach the application</h1>
              <p>{shellError}</p>
              <p>This is a connection problem, not a statement about your health.</p>
              <button className="button button--primary" onClick={() => setRetryIndex((index) => index + 1)}>Try again</button>
            </div>
          ) : resolution.kind === 'none' ? (
            <div className="state-card state-card--empty">
              <span className="eyebrow">Waiting for watch data</span>
              <h1>There is nobody to show yet.</h1>
              <p>Once your watch data has been pulled in for the first time, this screen will show it.</p>
            </div>
          ) : resolution.kind === 'choose' ? (
            <div className="state-card state-card--empty">
              <span className="eyebrow">Choose a person</span>
              <h1>Whose data would you like to see?</h1>
              <p>Several people are available. Choose one above to continue.</p>
            </div>
          ) : (
            <div className="page-stack">
              {view === 'home' ? (
                <HomeView
                  provenance={data.provenance ?? null}
                  summary={data.summary}
                  baselineMinimum={config?.BASELINE_MIN_NIGHTS_PERSONAL ?? 0}
                  errors={data.errors}
                  onNavigate={navigate}
                />
              ) : view === 'today' && selectedSubject && config ? (
                <TodayView subject={selectedSubject} config={config} data={data} onNavigate={navigate} />
              ) : view === 'history' && selectedSubject && config ? (
                <HistoryView subject={selectedSubject} config={config} initialNight={recordNight} onOpenRecord={navigate} />
              ) : view === 'record' && selectedSubject && config ? (
                <RecordView subject={selectedSubject} config={config} data={data} initialNight={recordNight} onNavigate={navigate} />
              ) : view === 'settings' && selectedSubject && config ? (
                <SettingsView
                  subject={selectedSubject}
                  config={config}
                  data={data}
                  onDeleted={() => {
                    setRememberedSubjectId(null)
                    navigate('home')
                    setRetryIndex((index) => index + 1)
                  }}
                />
              ) : (
                <WorkspaceView view={view} />
              )}
            </div>
          )}
        </div>

        <nav className="mobile-nav" aria-label="Main navigation">
          {navigation.map((item) => (
            <button className={`mobile-nav__item ${view === item.id ? 'mobile-nav__item--active' : ''}`} key={item.id} onClick={() => navigate(item.id)} aria-current={view === item.id ? 'page' : undefined}>
              <span aria-hidden="true">{item.mark}</span><span>{item.label}</span>
            </button>
          ))}
        </nav>
      </main>
    </div>
  )
}
