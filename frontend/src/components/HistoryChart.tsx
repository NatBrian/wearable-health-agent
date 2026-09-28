import type { NightRow } from '../api'
import { legacyText } from '../content/legacyCopy'
import { measuredValue } from '../lib/format'

export function HistoryChart({ nights, selectedDate, onSelect, baselineMinimum, loading, error }: {
  nights: NightRow[]
  selectedDate: string | null
  onSelect: (nightDate: string) => void
  baselineMinimum: number
  loading?: boolean
  error?: string | null
}) {
  const width = 860
  const height = 260
  const pad = { top: 18, right: 22, bottom: 42, left: 48 }
  const chartWidth = width - pad.left - pad.right
  const chartHeight = height - pad.top - pad.bottom
  const readings = nights.flatMap((night) => [night.rhr_bpm, night.band_lo, night.band_hi]).filter((value): value is number => value !== null)
  const minimum = readings.length ? Math.min(...readings) : 0
  const maximum = readings.length ? Math.max(...readings) : 1
  const spread = maximum - minimum || 1
  const low = minimum - spread * 0.12
  const high = maximum + spread * 0.12
  const timestamps = nights.map((night) => Date.parse(`${night.night_date}T00:00:00Z`))
  const firstTimestamp = timestamps[0] ?? 0
  const lastTimestamp = timestamps.at(-1) ?? firstTimestamp
  const x = (index: number) => pad.left + (lastTimestamp === firstTimestamp ? chartWidth / 2 : (timestamps[index] - firstTimestamp) / (lastTimestamp - firstTimestamp) * chartWidth)
  const y = (value: number) => pad.top + (high - value) / (high - low) * chartHeight
  const lineSegments: string[] = []
  let segment = ''
  nights.forEach((night, index) => {
    if (!night.usable || night.rhr_bpm === null) {
      if (segment) lineSegments.push(segment)
      segment = ''
    } else {
      segment += `${segment ? ' L' : 'M'}${x(index).toFixed(1)},${y(night.rhr_bpm).toFixed(1)}`
    }
  })
  if (segment) lineSegments.push(segment)
  const bands = nights.flatMap((night, index) => night.band_lo === null || night.band_hi === null
    ? []
    : [{ date: night.night_date, x: x(index), top: y(night.band_hi), bottom: y(night.band_lo) }])

  return (
    <section className="content-card chart-card" aria-labelledby="history-chart-heading">
      <div className="section-heading"><div><span className="eyebrow">Nightly measurements</span><h2 id="history-chart-heading">Your nights over time</h2></div></div>
      {error ? <p className="inline-notice inline-notice--warning" role="alert">The chart could not be loaded. This is a fetch failure, not an empty history. {error}</p> : loading && nights.length === 0 ? <p role="status">Loading the history chart.</p> : nights.length === 0 ? <p>No nights are available in this period.</p> : !nights.some((night) => night.usable && night.rhr_bpm !== null) ? <p>No night in this period was measured well enough to plot. That is missing data, not a result.</p> : (
        <div className="chart-scroll" role="region" aria-label="Nightly heart rate chart. Scroll horizontally to inspect dates.">
          <svg className="history-chart" viewBox={`0 0 ${width} ${height}`} role="group" aria-labelledby="chart-title" aria-describedby="chart-description">
            <title id="chart-title">Sleeping heart rate by night</title>
            <desc id="chart-description">Dots show the recorded level for each night. The line joins recorded heart rate values and leaves gaps where there is no value. Shaded vertical ranges show the range returned for each night.</desc>
            {[0, 1, 2, 3].map((line) => {
              const value = low + (high - low) * line / 3
              const yPosition = y(value)
              return <g key={line}><line x1={pad.left} x2={width - pad.right} y1={yPosition} y2={yPosition} stroke="#e7ece9" /><text x={pad.left - 8} y={yPosition + 3} textAnchor="end">{measuredValue(value)}</text></g>
            })}
            {bands.map((band) => <rect key={`band-${band.date}`} x={band.x - Math.max(2, chartWidth / nights.length / 4)} y={band.top} width={Math.max(4, chartWidth / nights.length / 2)} height={Math.max(1, band.bottom - band.top)} rx="2" fill="#cddfd1" opacity=".7" />)}
            {lineSegments.map((path, index) => <path key={`line-${index}`} d={path} fill="none" stroke="#3a7664" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />)}
            {nights.map((night, index) => {
              if (!night.usable || night.rhr_bpm === null) return <text key={night.night_date} className="chart-gap" x={x(index)} y={height - 13} textAnchor="middle" role="img" aria-label={`${night.night_date}: no usable reading`}>·</text>
              const color = night.level === 'RED' ? '#a44f43' : night.level === 'YELLOW' ? '#b47b29' : night.level === 'GREEN' ? '#4c8060' : '#87928e'
              return <circle key={night.night_date} className="chart-point" cx={x(index)} cy={y(night.rhr_bpm)} r={selectedDate === night.night_date ? 6 : 4} fill={color} stroke={selectedDate === night.night_date ? '#163f39' : '#fff'} strokeWidth={selectedDate === night.night_date ? 2 : 1} tabIndex={0} role="button" aria-label={`${night.night_date}, ${night.level}, ${measuredValue(night.rhr_bpm, 'beats per minute')}`} onClick={() => onSelect(night.night_date)} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onSelect(night.night_date) } }} />
            })}
            {nights.map((night, index) => index === 0 || index === nights.length - 1 || index === Math.floor(nights.length / 2)
              ? <text key={`date-${night.night_date}`} className="chart-date" x={x(index)} y={height - 5} textAnchor="middle">{night.night_date.slice(5)}</text>
              : null)}
          </svg>
        </div>
      )}
      <div className="chart-legend" aria-label="Chart legend"><span><i className="legend-band" />Your usual range</span><span><i className="legend-dot legend-dot--green" />GREEN</span><span><i className="legend-dot legend-dot--yellow" />YELLOW</span><span><i className="legend-dot legend-dot--red" />RED</span><span><i className="legend-dot legend-dot--na" />NA</span></div>
      <p className="supporting-copy">{legacyText('chart.how_to_read')}</p>
      <details className="chart-notes"><summary>What this chart can and cannot tell you</summary><div className="disclosure-card__body">
        <p>This system looks for a raised sleeping heart rate against your own median. It needs {baselineMinimum} usable nights before it can alert. Before then, the starting range comes from a population estimate and shifts towards your own readings as the system learns your normal. The source and population scope are available in the baseline step on The record.</p>
        <p>Only the recorded sleep window is used when available. Waking heart rate and naps are left out; when the watch records no sleep window, the system uses its configured clock fallback and identifies that on the night record.</p>
        <p>Only a raised heart rate is investigated. A low reading does not open an investigation, and this system cannot detect sleep apnoea. A normal-looking point describes that measurement only, not your health.</p>
        <p>Nights with no reading are left as gaps rather than joined up. A gap is missing data, not a normal result.</p>
      </div></details>
    </section>
  )
}
