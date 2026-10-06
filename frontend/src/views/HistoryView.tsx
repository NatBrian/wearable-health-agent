import { useEffect, useMemo, useState } from 'react'
import { api, type DetectionLevel, type EpisodeSummary, type NightDetail, type NightRow, type Subject, type SystemConfig } from '../api'
import { legacyText } from '../content/legacyCopy'
import { dateLabel, measuredValue, signedValue } from '../lib/format'
import { HistoryChart } from '../components/HistoryChart'
import type { DashboardViewId } from './HomeView'

const levels: DetectionLevel[] = ['GREEN', 'YELLOW', 'RED', 'NA']

export function HistoryView({
  subject, config, initialNight, onOpenRecord,
}: {
  subject: Subject
  config: SystemConfig
  initialNight: string | null
  onOpenRecord: (view: DashboardViewId, nightDate?: string) => void
}) {
  const windows = config.dashboard.history_windows_days
  const [days, setDays] = useState(windows.includes(60) ? 60 : windows[0] ?? 30)
  const [selectedLevels, setSelectedLevels] = useState<DetectionLevel[]>([])
  const [investigatedOnly, setInvestigatedOnly] = useState(false)
  const [showAllFields, setShowAllFields] = useState(false)
  const [chartRows, setChartRows] = useState<NightRow[]>([])
  const [tableRows, setTableRows] = useState<NightRow[]>([])
  const [episodes, setEpisodes] = useState<EpisodeSummary[]>([])
  const [selectedDate, setSelectedDate] = useState<string | null>(initialNight)
  const [detail, setDetail] = useState<NightDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [detailError, setDetailError] = useState<string | null>(null)

  const levelKey = selectedLevels.join(',')
  useEffect(() => {
    let active = true
    setLoading(true)
    setError(null)
    const filters = { levels: selectedLevels, investigatedOnly }
    const tableRequest = selectedLevels.length || investigatedOnly
      ? api.listNights(subject.subject_id, days, filters)
      : api.listNights(subject.subject_id, days)
    void Promise.all([api.listNights(subject.subject_id, days), tableRequest, api.listEpisodes(subject.subject_id)])
      .then(([chart, table, episodeRows]) => {
        if (!active) return
        setChartRows(chart)
        setTableRows(table)
        setEpisodes(episodeRows)
        setSelectedDate((current) => {
          if (current && chart.some((night) => night.night_date === current)) return current
          return [...chart].filter((night) => night.usable).sort((a, b) => b.night_date.localeCompare(a.night_date))[0]?.night_date ?? null
        })
      })
      .catch((exc: unknown) => { if (active) setError(String(exc)) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [subject.subject_id, days, levelKey, investigatedOnly])

  useEffect(() => {
    if (!selectedDate) { setDetail(null); return }
    let active = true
    setDetailError(null)
    void api.getNightDetail(subject.subject_id, selectedDate)
      .then((result) => { if (active) setDetail(result) })
      .catch((exc: unknown) => { if (active) { setDetail(null); setDetailError(String(exc)) } })
    return () => { active = false }
  }, [subject.subject_id, selectedDate])

  const episodeById = useMemo(() => new Map(episodes.map((episode) => [episode.episode_id, episode])), [episodes])
  const selectedNight = chartRows.find((night) => night.night_date === selectedDate) ?? null
  const sortedRows = useMemo(() => [...tableRows].sort((a, b) => b.night_date.localeCompare(a.night_date)), [tableRows])
  const toggleLevel = (level: DetectionLevel) => setSelectedLevels((current) => current.includes(level) ? current.filter((item) => item !== level) : [...current, level])

  return (
    <div className="page-stack">
      <section className="history-heading"><div><span className="eyebrow">Your record over time</span><h1>Your nights</h1><p>Look for patterns across nights, then open the record for any night in full.</p></div>
        <label className="field-label history-window">How far back<select value={days} onChange={(event) => setDays(Number(event.target.value))}>{windows.map((window) => <option key={window} value={window}>Last {window} nights</option>)}</select></label>
      </section>
      <HistoryChart nights={chartRows} selectedDate={selectedDate} onSelect={setSelectedDate} baselineMinimum={config.BASELINE_MIN_NIGHTS_PERSONAL} loading={loading} error={error} />

      <section className="content-card" aria-labelledby="night-table-heading">
        <div className="section-heading"><div><span className="eyebrow">Browse the record</span><h2 id="night-table-heading">Night by night</h2></div></div>
        <p className="supporting-copy">Leave the level selection empty to show every night. Filters apply to the table; the chart above keeps its full window for context.</p>
        <fieldset className="history-filters"><legend>Show which nights</legend>{levels.map((level) => <label key={level}><input type="checkbox" checked={selectedLevels.includes(level)} onChange={() => toggleLevel(level)} /><span className={`level-badge level-badge--${level.toLowerCase()}`}>{level}</span></label>)}</fieldset>
        <label className="toggle-row"><input type="checkbox" checked={investigatedOnly} onChange={(event) => setInvestigatedOnly(event.target.checked)} /><span>Only nights that were looked into</span></label>
        <label className="toggle-row"><input type="checkbox" checked={showAllFields} onChange={(event) => setShowAllFields(event.target.checked)} /><span>Show every recorded field</span><small>The summary columns are what the system judges. This adds the remaining recorded details.</small></label>
        {loading && <p role="status">Loading nights.</p>}
        {error && <p className="inline-notice inline-notice--warning" role="alert">History could not be loaded. {error}</p>}
        {!loading && !error && sortedRows.length === 0 && <p className="empty-table">No nights match that filter. Nothing here is a statement about your health.</p>}
        {!loading && !error && sortedRows.length > 0 && (
          <div className="table-scroll" role="region" aria-label="Night by night table" tabIndex={0}>
            <table className="history-table"><thead><tr>
              <th>Night</th><th>Conclusion</th><th>Your reading</th><th>Against your normal</th><th>Reading coverage</th><th>Investigated</th>
              {showAllFields && <><th>Explained by exercise</th><th>Left after that</th><th>Your normal</th><th>Usual range</th><th>Measured over</th><th>Investigation</th><th>Sleep hours</th><th>Previous day steps</th><th>Usable</th></>}
            </tr></thead><tbody>{sortedRows.map((night) => {
              const episode = night.episode_id ? episodeById.get(night.episode_id) : undefined
              return <tr key={night.night_date} className={selectedDate === night.night_date ? 'history-table__selected' : ''}>
                <td><button className="table-link" onClick={() => setSelectedDate(night.night_date)}>{dateLabel(night.night_date, subject.timezone)}</button></td>
                <td><span className={`level-badge level-badge--${night.level.toLowerCase()}`}>{night.level}</span></td>
                <td>{measuredValue(night.rhr_bpm, 'bpm')}</td><td>{signedValue(night.deviation_bpm, 'bpm')}</td><td>{measuredValue(night.coverage_minutes, 'minutes')}</td><td>{outcomeWords(episode)}</td>
                {showAllFields && <><td>{measuredValue(night.explained_bpm, 'bpm')}</td><td>{measuredValue(night.residual_bpm, 'bpm')}</td><td>{measuredValue(night.centre_bpm, 'bpm')}</td><td>{night.band_lo === null || night.band_hi === null ? 'not available' : `${measuredValue(night.band_lo)}–${measuredValue(night.band_hi)} bpm`}</td><td>{night.rhr_window_source}</td><td>{night.episode_id ?? 'none'}</td><td>{measuredValue(night.sleep_hours, 'hours')}</td><td>{measuredValue(night.steps_prev_day)}</td><td>{night.usable ? 'yes' : 'no'}</td></>}
              </tr>
            })}</tbody></table>
          </div>
        )}
        <div className="level-explanation"><span className="eyebrow">What the conclusion means</span><p><strong>GREEN</strong> in your usual range. <strong>YELLOW</strong> somewhat above it, which on its own opens nothing. <strong>RED</strong> clearly above it, and enough of these in a row opens an investigation. <strong>NA</strong> too little of the night measured to judge.</p></div>
      </section>

      <section className="content-card selected-night" aria-labelledby="selected-night-heading">
        <div className="section-heading"><div><span className="eyebrow">Trace one night</span><h2 id="selected-night-heading">Look at one night in full</h2></div></div>
        {loading && chartRows.length === 0 ? <p role="status">Loading measured nights.</p> : error ? <p className="inline-notice inline-notice--warning" role="alert">A night cannot be selected because history failed to load. {error}</p> : chartRows.some((night) => night.usable) ? (
          <>
            <label className="field-label">Which night<select value={selectedDate ?? ''} onChange={(event) => setSelectedDate(event.target.value || null)}>{[...chartRows].filter((night) => night.usable).sort((a, b) => b.night_date.localeCompare(a.night_date)).map((night) => <option key={night.night_date} value={night.night_date}>{dateLabel(night.night_date, subject.timezone)} · {night.level}</option>)}</select></label>
            {selectedNight && <div className="selected-night__summary"><span className={`level-badge level-badge--${selectedNight.level.toLowerCase()}`}>{selectedNight.level}</span><p>{legacyText(`level.${selectedNight.level}`)}</p>{detail && <p>{legacyText(`metric.window_source.${detail.row.rhr_window_source === 'sleep' ? 'sleep' : 'clock'}`)} Your normal is {measuredValue(detail.baseline.centre_bpm, 'bpm')}; the usual range is {measuredValue(selectedNight.band_lo, 'bpm')} to {measuredValue(selectedNight.band_hi, 'bpm')}. {legacyText('metric.band')}</p>}</div>}
            {detailError && <p className="inline-notice inline-notice--warning" role="alert">The night detail could not be loaded. {detailError}</p>}
            <button className="button button--primary" onClick={() => selectedDate && onOpenRecord('record', selectedDate)}>Show me every step of that night</button>
          </>
        ) : <p>No night in this window was measured well enough to open.</p>}
      </section>
    </div>
  )
}

function outcomeWords(episode: EpisodeSummary | undefined): string {
  if (!episode) return 'not investigated'
  if (episode.disposition) return episode.disposition.replace(/_/g, ' ').toLowerCase()
  return ({
    OPEN: 'being looked into',
    AWAITING_USER: 'waiting for your answer',
    AWAITING_MEASUREMENT: 'waiting for a measurement',
    AWAITING_HUMAN_REVIEW: 'waiting for review',
    CLOSED: 'closed with no conclusion recorded',
  } as Record<string, string>)[episode.state] ?? episode.state.toLowerCase()
}
