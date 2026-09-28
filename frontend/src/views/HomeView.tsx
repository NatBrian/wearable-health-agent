import type { DashboardSummary, KnowledgeProvenanceSummary } from '../api'
import { legacyText } from '../content/legacyCopy'
import { HomeDisclosure } from '../components/HomeDisclosure'
import type { BackendErrors } from '../useBackend'

export type DashboardViewId = 'home' | 'today' | 'history' | 'record' | 'settings'

const destinations: { id: DashboardViewId; title: string; copy: string }[] = [
  { id: 'today', title: 'Today', copy: legacyText('home.nav.today') },
  { id: 'history', title: 'History', copy: legacyText('home.nav.history') },
  { id: 'record', title: 'The record', copy: legacyText('home.nav.audit') },
  { id: 'settings', title: 'Settings', copy: legacyText('home.nav.settings') },
]

export function HomeView({
  summary, provenance, baselineMinimum, errors, onNavigate, showCannot = true,
}: {
  summary: DashboardSummary | null
  provenance: KnowledgeProvenanceSummary | null
  baselineMinimum: number
  errors?: BackendErrors
  onNavigate: (view: DashboardViewId) => void
  showCannot?: boolean
}) {
  return (
    <div className="page-stack">
      <section className="home-intro">
        <div className="eyebrow">Your night watch</div>
        <h1>What this is</h1>
        <p className="home-intro__lede">{legacyText('home.what_it_is')}</p>
      </section>

      <div className={`home-capabilities ${showCannot ? '' : 'home-capabilities--single'}`}>
        <article className="content-card content-card--can">
          <span className="card-kicker">What it can do</span>
          <p>{legacyText('home.can')}</p>
        </article>
        {showCannot && <article className="content-card content-card--cannot">
          <span className="card-kicker">What it cannot do</span>
          <p>{legacyText('home.cannot')}</p>
        </article>}
      </div>

      <HomeDisclosure baselineMinimum={baselineMinimum} />

      <section className="content-card how-card">
        <div className="section-heading"><div><span className="eyebrow">Behind the result</span><h2>How a night gets judged</h2></div><span className="section-mark" aria-hidden="true">↗</span></div>
        <p>{legacyText('home.judging')}</p>
        <p className="supporting-copy">Every step of this is shown, night by night, on “The record”.</p>
      </section>

      <section aria-labelledby="nav-heading">
        <div className="section-heading"><div><span className="eyebrow">Explore the dashboard</span><h2 id="nav-heading">Where to go</h2></div></div>
        <div className="destination-grid">
          {destinations.map((destination) => (
            <button className="destination-card" key={destination.id} onClick={() => onNavigate(destination.id)}>
              <span className="destination-card__mark" aria-hidden="true" />
              <span className="destination-card__title">{destination.title}</span>
              <span className="destination-card__copy">{destination.copy}</span>
              <span className="destination-card__arrow" aria-hidden="true">→</span>
            </button>
          ))}
        </div>
      </section>

      <section className="content-card evidence-card">
        <div className="section-heading"><div><span className="eyebrow">Evidence and limits</span><h2>Being straight with you about the evidence</h2></div><span className="evidence-symbol" aria-hidden="true">◌</span></div>
        <p>{legacyText('home.provenance')}</p>
        {provenance ? (
          <p className="evidence-count">Of the {provenance.total_entries} causes and questions this system weighs, {provenance.unevidenced_entries} rest on at least one figure with no published source behind it. Each is marked where it is used.</p>
        ) : (
          <p className="supporting-copy" role={errors?.provenance ? 'alert' : 'status'}>{errors?.provenance ? `The evidence count could not be loaded. This is a fetch failure, not an empty evidence set. ${errors.provenance}` : 'The evidence count is not available right now.'}</p>
        )}
      </section>

      {summary && (summary.latest_sleep_hours !== null || summary.latest_steps !== null) && (
        <section className="home-summary" aria-label="Latest recorded information">
          {summary.latest_sleep_hours !== null && <p>Latest sleep record: {summary.latest_sleep_hours} hours, from {summary.latest_sleep_night ?? 'a date not recorded'}.</p>}
          {summary.latest_steps !== null && <p>Latest steps record: {summary.latest_steps}, from {summary.latest_steps_night ?? 'a date not recorded'}.</p>}
        </section>
      )}
      {errors?.summary && <section className="content-card inline-notice inline-notice--warning" role="alert">The latest sleep and steps could not be loaded. This is a fetch failure, not a missing record. {errors.summary}</section>}
    </div>
  )
}
