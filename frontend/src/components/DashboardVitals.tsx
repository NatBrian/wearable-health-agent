import { useState, type CSSProperties } from 'react'
import { CAUSE_LABELS, type CauseId, type DetectionLevel, type Subject, type SystemConfig, type SystemStatus } from '../api'
import type { BackendData } from '../useBackend'
import { dateLabel, measuredValue, signedValue } from '../lib/format'
import { OxygenContext } from './OxygenContext'

type SeriesId = 'rhr' | 'sleep' | 'steps' | 'oxygen'
type DetectionStreak = NonNullable<SystemStatus['detection_streak']>
type TrendPoint = { date: string; value: number | null; low?: number | null; high?: number | null }
type VitalSeries = {
  id: SeriesId
  label: string
  unit: string
  color: string
  value: number | null
  valueDate: string | null
  points: TrendPoint[]
  note: string
  baseline?: number | null
  baselineNights?: number | null
  baselineRung?: string | null
  deviation?: number | null
  robustZ?: number | null
}

const levelClass: Record<DetectionLevel, string> = {
  GREEN: 'level-green', YELLOW: 'level-yellow', RED: 'level-red', NA: 'level-na',
}
const streakDirectionLabel: Record<NonNullable<DetectionStreak['direction']>, string> = {
  rising: 'worsening', steady: 'holding steady', falling: 'resolving',
}

function SleepStreak({ streak }: { streak: DetectionStreak }) {
  const level = streak.level.toLowerCase()
  return (
    <span className={`vital-card__streak vital-card__streak--${level}`}>
      <strong>{streak.length} {level} {streak.length === 1 ? 'night' : 'nights'}</strong>
      {streak.direction && <span>{streakDirectionLabel[streak.direction]}</span>}
    </span>
  )
}

function latestValue<T extends { value: number | null }>(points: T[]): T | null {
  return [...points].reverse().find((point) => point.value !== null) ?? null
}

function Sparkline({ series }: { series: VitalSeries }) {
  const width = 180
  const height = 38
  const values = series.points.map((point) => point.value).filter((value): value is number => value !== null)
  if (values.length < 2) return <svg className="vital-card__spark" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${series.label} sparkline`}><title>{series.label} sparkline</title><desc>There is not enough recorded data to show a trend.</desc></svg>

  const min = Math.min(...values)
  const max = Math.max(...values)
  const spread = max - min || 1
  const timestamps = series.points.map((point) => Date.parse(`${point.date.slice(0, 10)}T12:00:00Z`))
  const start = timestamps[0]
  const end = timestamps.at(-1) ?? start
  const x = (index: number) => end === start ? width / 2 : (timestamps[index] - start) / (end - start) * (width - 6) + 3
  const y = (value: number) => height - 4 - ((value - min) / spread) * (height - 8)
  const paths: string[] = []
  let path = ''
  let previousTime: number | null = null
  series.points.forEach((point, index) => {
    const timestamp = timestamps[index]
    if (point.value === null || (previousTime !== null && timestamp - previousTime > 36 * 60 * 60 * 1000)) {
      if (path) paths.push(path)
      path = ''
    }
    if (point.value !== null) {
      path += `${path ? ' L' : 'M'}${x(index).toFixed(1)},${y(point.value).toFixed(1)}`
      previousTime = timestamp
    }
  })
  if (path) paths.push(path)

  return (
    <svg className="vital-card__spark" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${series.label} sparkline`}>
      {paths.map((segment, index) => <path key={index} d={segment} fill="none" stroke={series.color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />)}
    </svg>
  )
}

function TrendChart({ series, nightsCount }: { series: VitalSeries; nightsCount: number }) {
  const width = 800
  const height = 220
  const pad = { top: 16, right: 24, bottom: 34, left: 56 }
  const chartWidth = width - pad.left - pad.right
  const chartHeight = height - pad.top - pad.bottom
  const available = series.points.flatMap((point) => [point.value, point.low, point.high]).filter((value): value is number => value !== null && value !== undefined)
  const min = available.length ? Math.min(...available) : 0
  const max = available.length ? Math.max(...available) : 1
  const spread = max - min || 1
  const timestamps = series.points.map((point) => Date.parse(`${point.date.slice(0, 10)}T12:00:00Z`))
  const first = timestamps[0] ?? 0
  const last = timestamps.at(-1) ?? first
  const x = (index: number) => pad.left + (last === first ? chartWidth / 2 : (timestamps[index] - first) / (last - first) * chartWidth)
  const y = (value: number) => pad.top + ((max - value) / spread) * chartHeight
  const paths: string[] = []
  let path = ''
  let previousTime: number | null = null
  series.points.forEach((point, index) => {
    const timestamp = timestamps[index]
    if (point.value === null || (previousTime !== null && timestamp - previousTime > 36 * 60 * 60 * 1000)) {
      if (path) paths.push(path)
      path = ''
    }
    if (point.value !== null) {
      path += `${path ? ' L' : 'M'}${x(index).toFixed(1)},${y(point.value).toFixed(1)}`
      previousTime = timestamp
    }
  })
  if (path) paths.push(path)
  const rangeBars = series.points.flatMap((point, index) => point.low == null || point.high == null
    ? []
    : [{ date: point.date, x: x(index), top: y(point.high), bottom: y(point.low) }])
  const labelIndices = [...new Set([0, Math.floor((series.points.length - 1) / 2), series.points.length - 1])]

  return (
    <section className="content-card trend-panel" aria-labelledby="trend-title">
      <div className="section-heading">
        <div><span className="eyebrow">{series.label} · {nightsCount} nights</span><h2 id="trend-title">{series.label} trend</h2></div>
        <div className="trend-panel__current"><strong>{measuredValue(series.value, series.unit)}</strong><span>{series.valueDate ? dateLabel(series.valueDate) : 'latest available'}</span></div>
      </div>
      {series.id === 'rhr' && <p className="supporting-copy">The shaded band shows the nightly range returned by the API. Missing nights remain gaps.</p>}
      {(series.points.length < 2 || !series.points.some((point) => point.value !== null)) && <p className="trend-panel__empty" role="status">{series.note}</p>}
      <div className="dashboard-chart-scroll" role="region" aria-label={`${series.label} chart`}>
          <svg className="dashboard-trend-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${series.label} trend`}>
            <title>{series.label} over time</title>
            <desc>Values are shown on their recorded dates. Gaps are not joined. {series.id === 'rhr' ? 'Vertical ranges show the nightly range returned for each reading.' : ''}</desc>
            {[0, 1, 2, 3].map((line) => {
              const value = min + spread * line / 3
              const yPosition = y(value)
              return <g key={line}><line x1={pad.left} x2={width - pad.right} y1={yPosition} y2={yPosition} className="dashboard-chart-gridline" /><text x={pad.left - 9} y={yPosition + 4} textAnchor="end">{measuredValue(value)}</text></g>
            })}
            {rangeBars.map((range) => <line key={range.date} x1={range.x} x2={range.x} y1={range.top} y2={range.bottom} className="dashboard-chart-range" />)}
            {paths.map((segment, index) => <path key={index} d={segment} className="dashboard-chart-line" style={{ stroke: series.color }} />)}
            {series.points.map((point, index) => point.value === null
              ? <text key={point.date} className="dashboard-chart-gap" x={x(index)} y={height - 12} textAnchor="middle" aria-label={`${point.date}: no reading`}>·</text>
              : <circle key={point.date} cx={x(index)} cy={y(point.value)} r="3.5" className="dashboard-chart-point" style={{ fill: series.color }}><title>{dateLabel(point.date)}: {measuredValue(point.value, series.unit)}</title></circle>)}
            {labelIndices.map((index) => {
              const point = series.points[index]
              return point ? <text key={point.date} className="dashboard-chart-date" x={x(index)} y={height - 4} textAnchor="middle">{dateLabel(point.date)}</text> : null
            })}
          </svg>
      </div>
    </section>
  )
}

function LatestNight({ data }: { data: BackendData }) {
  const detail = data.latestDetail
  if (data.errors.latestDetail) return <section className="content-card" aria-labelledby="latest-night-title"><h2 id="latest-night-title">Last measured night</h2><p className="inline-notice inline-notice--warning" role="alert">The latest night detail could not be loaded. This is a fetch failure, not an empty measurement. {data.errors.latestDetail}</p></section>
  if (!detail) return <section className="content-card" aria-labelledby="latest-night-title"><h2 id="latest-night-title">Last measured night</h2><p>{data.errors.nights ? 'Night readings could not be loaded.' : 'No measured night yet.'}</p></section>
  const { row, baseline, detection } = detail
  return (
    <section className="content-card latest-night" aria-labelledby="latest-night-title">
      <div className="section-heading"><div><span className="eyebrow">{dateLabel(row.night_date)}</span><h2 id="latest-night-title">Last measured night</h2></div><span className={`level-pill ${levelClass[row.level]}`}>{row.level}</span></div>
      <div className="latest-night__headline">
        <div><strong>{measuredValue(row.rhr_bpm, 'bpm')}</strong><span>Resting heart rate</span></div>
        <div><strong>{measuredValue(row.coverage_minutes, 'minutes')}</strong><span>Watch coverage</span></div>
      </div>
      <dl className="latest-night__details">
        <div><dt>Your usual centre</dt><dd>{measuredValue(baseline.centre_bpm, 'bpm')}</dd></div>
        <div><dt>Usual range</dt><dd>{row.band_lo === null || row.band_hi === null ? 'not available' : `${measuredValue(row.band_lo)}–${measuredValue(row.band_hi)} bpm`}</dd></div>
        <div><dt>Deviation</dt><dd>{measuredValue(row.deviation_bpm, 'bpm')}</dd></div>
        <div><dt>Baseline</dt><dd>{baseline.usable_nights} usable nights · {baseline.rung}</dd></div>
        <div><dt>Baseline scale</dt><dd>{measuredValue(baseline.scale_bpm, 'bpm')}</dd></div>
        {detection.robust_z !== null && <div><dt>Robust z</dt><dd>{measuredValue(detection.robust_z)}</dd></div>}
      </dl>
      {row.rhr_window_source && <p className="supporting-copy">Heart-rate window: {row.rhr_window_source.replace(/_/g, ' ')}.</p>}
    </section>
  )
}

function CauseDifferential({ data }: { data: BackendData }) {
  const history = data.activeEpisode?.belief_history ?? []
  const first = history[0]?.[2].marginals
  const latest = history.at(-1)?.[2].marginals
  const causes = latest
    ? (Object.entries(latest) as [CauseId, number][]).sort((left, right) => right[1] - left[1])
    : []

  return (
    <section className="content-card cause-differential" aria-labelledby="differential-title" aria-label="Cause differential">
      <div className="section-heading"><div><span className="eyebrow">{data.activeEpisode ? 'Current episode' : 'Investigation context'}</span><h2 id="differential-title">Cause differential</h2></div>{data.activeEpisode && <span className="supporting-copy">Change since the investigation opened</span>}</div>
      {data.errors.activeEpisode ? <p className="inline-notice inline-notice--warning" role="alert">The cause differential could not be loaded. This is a fetch failure, not an empty differential. {data.errors.activeEpisode}</p> : causes.length === 0 ? <p>{data.episodes.length === 0 ? 'No investigation is active, so there is no cause differential to show.' : 'No cause probabilities are recorded for this investigation.'}</p> : (
        <ol className="cause-list">{causes.map(([cause, probability]) => {
          const initial = first?.[cause]
          return <li key={cause}>
            <div className="cause-list__label"><span>{CAUSE_LABELS[cause]}</span><strong>{measuredValue(probability * 100, '%')}</strong></div>
            <div className="cause-list__track" aria-hidden="true"><span style={{ width: `${Math.max(0, Math.min(100, probability * 100))}%` }} /></div>
            {initial !== undefined && initial !== probability && <p>Opened at {measuredValue(initial * 100, '%')}; now {measuredValue(probability * 100, '%')}.</p>}
          </li>
        })}</ol>
      )}
    </section>
  )
}

function DashboardBanner({ data, timezone }: { data: BackendData; timezone: string }) {
  const episode = data.episodes.find((item) => item.state !== 'CLOSED')
  if (episode) {
    return <section className="dashboard-state dashboard-state--active" aria-label="Episode status">
      <span className="dashboard-state__icon" aria-hidden="true">!</span>
      <div><strong>Investigation open · {dateLabel(episode.night_span[0], timezone)} to {dateLabel(episode.night_span[1], timezone)}</strong><p>State: {episode.state.replace(/_/g, ' ').toLowerCase()}{episode.top_cause ? ` · leading hypothesis ${CAUSE_LABELS[episode.top_cause]} at ${measuredValue((episode.top_probability ?? 0) * 100, '%')}` : ''}</p></div>
      <span className="dashboard-state__tag">Active</span>
    </section>
  }
  return <section className="dashboard-state dashboard-state--quiet" aria-label="Episode status">
    <span className="dashboard-state__icon" aria-hidden="true">✓</span>
    <div><strong>Nothing is waiting for you right now.</strong><p>{data.status ? `${data.status.quiet_nights_streak} measured quiet nights · baseline ${data.status.rung.toLowerCase()}` : 'System status is unavailable.'}</p></div>
  </section>
}

export function DashboardVitals({ data, subject, config }: { data: BackendData; subject: Subject; config: SystemConfig }) {
  const measuredNights = data.nights.filter((night) => night.usable)
  const latestNight = measuredNights.at(-1) ?? null
  const sleepPoints = measuredNights.map((night) => ({ date: night.night_date, value: night.sleep_hours }))
  const stepsPoints = measuredNights.map((night) => ({ date: night.night_date, value: night.steps_prev_day }))
  const lastSleep = latestValue(sleepPoints)
  const lastSteps = latestValue(stepsPoints)
  const lastOxygen = data.oxygenReadings.at(-1) ?? null

  const series: VitalSeries[] = [
    {
      id: 'rhr', label: 'Resting HR', unit: 'bpm', color: '#f59e0b',
      value: data.latestDetail?.row.rhr_bpm ?? latestNight?.rhr_bpm ?? null,
      valueDate: data.latestDetail?.row.night_date ?? latestNight?.night_date ?? null,
      points: data.nights.map((night) => ({ date: night.night_date, value: night.usable ? night.rhr_bpm : null, low: night.band_lo, high: night.band_hi })),
      note: data.errors.nights ? 'Night readings could not be loaded.' : 'Not enough measured nights yet to draw a chart.',
      baseline: data.latestDetail?.baseline.centre_bpm ?? latestNight?.centre_bpm ?? null,
      baselineNights: data.latestDetail?.baseline.usable_nights ?? data.status?.usable_nights ?? null,
      baselineRung: data.latestDetail?.baseline.rung ?? data.status?.rung ?? null,
      deviation: data.latestDetail?.row.deviation_bpm ?? latestNight?.deviation_bpm ?? null,
      robustZ: data.latestDetail?.detection.robust_z ?? null,
    },
    {
      id: 'sleep', label: 'Sleep', unit: 'h', color: '#c5f041', value: lastSleep?.value ?? null, valueDate: lastSleep?.date ?? null,
      points: sleepPoints, note: data.errors.nights ? 'Sleep readings could not be loaded.' : 'No sleep readings are available in this period.',
    },
    {
      id: 'steps', label: `Steps (${config.dashboard.steps_average_days}d avg)`, unit: 'steps', color: '#818cf8', value: data.summary?.steps_average ?? null,
      valueDate: data.summary?.steps_window_end ?? null, points: stepsPoints,
      note: data.errors.summary ? 'The configured steps average could not be loaded.' : 'No steps readings are available in this period.',
    },
    {
      id: 'oxygen', label: 'SpO₂', unit: '%', color: '#22d3ee', value: lastOxygen?.percentage ?? null,
      valueDate: lastOxygen?.ts_utc ?? null, points: data.oxygenReadings.map((reading) => ({ date: reading.ts_utc, value: reading.percentage })),
      note: data.errors.oxygenReadings ? 'Oxygen spot checks could not be loaded.' : 'No spot reading in the recent period.',
    },
  ]
  const [selectedId, setSelectedId] = useState<SeriesId>('rhr')
  const selected = series.find((item) => item.id === selectedId) ?? series[0]

  return (
    <div className="dashboard-overview">
      <DashboardBanner data={data} timezone={subject.timezone} />
      {(data.errors.nights || data.errors.summary || data.errors.oxygenReadings) && <p className="inline-notice inline-notice--warning" role="alert">Some dashboard readings could not be loaded. A failed request is not an empty or normal result. {[data.errors.nights, data.errors.summary, data.errors.oxygenReadings].filter(Boolean).join(' ')}</p>}
      <section className="vital-grid" aria-label="Recorded measures">
        {series.map((item) => {
          const displayValue = item.id === 'steps' && item.value !== null
            ? `${measuredValue(item.value)} ${item.unit}`
            : item.id === 'sleep' && item.value !== null
              ? `${new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(item.value)} ${item.unit}`
            : measuredValue(item.value, item.unit)
          const note = item.id === 'steps' && data.summary
            ? `Configured ${config.dashboard.steps_average_days}-day average · ${dateLabel(data.summary.steps_window_start)} to ${dateLabel(data.summary.steps_window_end)}`
            : item.valueDate ? `Most recent reading · ${dateLabel(item.valueDate, subject.timezone)}` : item.note
          return <button key={item.id} type="button" className={`vital-card ${selectedId === item.id ? 'vital-card--selected' : ''}`} style={{ '--vital-accent': item.color } as CSSProperties} aria-pressed={selectedId === item.id} onClick={() => setSelectedId(item.id)}>
            <span className="vital-card__label">{item.label}</span><strong className="vital-card__value" style={{ color: item.color }}>{displayValue}</strong>
            <Sparkline series={item} /><span className="vital-card__note">{note}</span>
            {item.id === 'rhr' && item.baseline !== null && item.baseline !== undefined && <span className="vital-card__baseline">Base {measuredValue(item.baseline, 'bpm')}{item.baselineNights !== null && item.baselineNights !== undefined && item.baselineRung ? <span>{measuredValue(item.baselineNights)} usable nights · {item.baselineRung}</span> : null}</span>}
            {item.id === 'rhr' && (item.deviation !== null && item.deviation !== undefined || item.robustZ !== null && item.robustZ !== undefined) && <span className="vital-card__deviation">{item.deviation !== null && item.deviation !== undefined ? `Deviation ${signedValue(item.deviation, 'bpm')}` : ''}{item.robustZ !== null && item.robustZ !== undefined ? `${item.deviation !== null && item.deviation !== undefined ? ' · ' : ''}robust z ${item.robustZ.toFixed(2)}` : ''}</span>}
            {item.id === 'sleep' && data.status?.detection_streak && <SleepStreak streak={data.status.detection_streak} />}
          </button>
        })}
      </section>
      {selected && <TrendChart series={selected} nightsCount={data.nights.length} />}
      <div className="dashboard-detail-grid"><LatestNight data={data} /><CauseDifferential data={data} /></div>
      <OxygenContext readings={data.oxygenReadings} subject={subject} error={data.errors.oxygenReadings} safetyRules={data.safetyRules} title="Recent oxygen spot checks" />
    </div>
  )
}
