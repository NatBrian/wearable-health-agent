import { legacyText } from '../content/legacyCopy'
import type { BackendData } from '../useBackend'
import type { Subject, SystemConfig } from '../api'
import { DashboardVitals } from '../components/DashboardVitals'
import { StatusBar } from '../components/StatusBar'
import { HistoryView } from './HistoryView'
import { HomeView, type DashboardViewId } from './HomeView'
import { TodayView } from './TodayView'

export type DashboardSection = 'overview' | 'today' | 'history'

const sections: { id: DashboardSection; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'today', label: 'Today' },
  { id: 'history', label: 'History' },
]

export function DashboardView({
  subject, config, data, section, initialNight, onSectionChange, onNavigate, onOpenChat,
}: {
  subject: Subject
  config: SystemConfig
  data: BackendData
  section: DashboardSection
  initialNight: string | null
  onSectionChange: (section: DashboardSection) => void
  onNavigate: (view: DashboardViewId, nightDate?: string) => void
  onOpenChat: () => void
}) {
  return (
    <div className="dashboard-view">
      <nav className="section-tabs" aria-label="Dashboard sections" role="tablist">
        {sections.map((item) => <button
          key={item.id}
          type="button"
          role="tab"
          aria-selected={section === item.id}
          className={section === item.id ? 'section-tab section-tab--active' : 'section-tab'}
          onClick={() => onSectionChange(item.id)}
        >{item.label}</button>)}
      </nav>

      {section === 'overview' && <div className="page-stack">
        <DashboardVitals data={data} subject={subject} config={config} />
        <details className="dashboard-explanations">
          <summary>What this is, and how the system works</summary>
          <div className="dashboard-explanations__body">
            <HomeView provenance={data.provenance} summary={data.summary} baselineMinimum={config.BASELINE_MIN_NIGHTS_PERSONAL} errors={data.errors} onNavigate={onNavigate} showCannot={false} />
          </div>
        </details>
      </div>}

      {section === 'today' && <div className="page-stack"><StatusBar status={data.status} subject={subject} loading={data.loading} error={data.errors.status ?? null} onOpenRecord={() => onNavigate('record', data.status?.last_nightly_utc?.slice(0, 10))} /><TodayView subject={subject} config={config} data={data} onNavigate={onNavigate} onOpenChat={onOpenChat} /></div>}
      {section === 'history' && <HistoryView subject={subject} config={config} initialNight={initialNight} onOpenRecord={onNavigate} />}
    </div>
  )
}
