import { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import {
  api, ApiUnavailable, CAUSE_LABELS,
  type Subject, type SystemStatus, type NightRow, type NightDetail, type EpisodeSummary,
  type EpisodeDetail, type PendingInteraction, type ConversationSession, type ConversationTurn,
  type SafetyRuleProvenance, type Settings, type Citation, type CauseId, type OxygenReading,
  type DetectionLevel,
} from './api'

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

type View = 'dashboard' | 'pipeline' | 'settings'

interface ChatMessage {
  role: 'user' | 'agent'; text: string; ts: string
  urgency?: 'same_day' | 'urgent' | null
  citations?: Citation[]; uncited?: string[]
}

interface VitalSeries {
  label: string; unit: string; color: string
  available: boolean; unavailableReason?: string
  baseline?: number; sigma?: number; current?: number; data?: number[]
  usableNights?: number; rung?: string
  chartPoints?: { date: string; v: number | null }[]
  chartBand?: { lo: number | null; hi: number | null }[]
}

// ─────────────────────────────────────────────────────────────────────────────
// Backend data hook — everything below reads from this, nothing is invented
// ─────────────────────────────────────────────────────────────────────────────

function useBackend() {
  const [subject, setSubject] = useState<Subject | null>(null)
  const [status, setStatus] = useState<SystemStatus | null>(null)
  const [nights, setNights] = useState<NightRow[]>([])
  const [latestDetail, setLatestDetail] = useState<NightDetail | null>(null)
  const [episodes, setEpisodes] = useState<EpisodeSummary[]>([])
  const [activeEpisode, setActiveEpisode] = useState<EpisodeDetail | null>(null)
  const [pending, setPending] = useState<PendingInteraction | null>(null)
  const [sessions, setSessions] = useState<ConversationSession[]>([])
  const [safetyRules, setSafetyRules] = useState<SafetyRuleProvenance[]>([])
  const [settings, setSettings] = useState<Settings | null>(null)
  const [oxygenReadings, setOxygenReadings] = useState<OxygenReading[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    try {
      const subjects = await api.listSubjects()
      const subj = subjects[0] ?? null
      setSubject(subj)
      if (!subj) { setLoading(false); return }
      const sid = subj.subject_id

      const [st, nightRows, eps, pend, sess, rules, cfg, oxygen] = await Promise.all([
        api.getStatus(sid),
        api.listNights(sid, 28),
        api.listEpisodes(sid),
        api.getPending(sid),
        api.getConversationSessions(sid, 200),
        api.getSafetyProvenance(),
        api.getSettings(),
        api.listOxygenReadings(sid, 7),
      ])
      setStatus(st); setNights(nightRows); setEpisodes(eps); setPending(pend)
      setSessions(sess); setSafetyRules(rules); setSettings(cfg); setOxygenReadings(oxygen)

      // Sleep and steps now travel on NightRow itself (one call already covers 28
      // nights), so this is only for what NightRow doesn't carry: robust_z and the full
      // Baseline object, for the single most recent measured night.
      const measured = nightRows.filter(n => n.usable)
      if (measured.length > 0) {
        setLatestDetail(await api.getNightDetail(sid, measured[measured.length - 1].night_date))
      }

      // The episode that most deserves the screen: open first, else most recently closed.
      const open = eps.find(e => e.state !== 'CLOSED')
      const target = open ?? eps[0]
      if (target) setActiveEpisode(await api.getEpisode(target.episode_id))

      setError(null)
    } catch (exc) {
      setError(exc instanceof ApiUnavailable ? exc.message : String(exc))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  return {
    subject, status, nights, latestDetail, episodes, activeEpisode, pending, sessions,
    safetyRules, settings, oxygenReadings, error, loading, refresh: load,
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Multi-night persistence — computed client-side from the nights list already fetched.
// No backend change: this is exactly the signal the agent itself reasons on (a single bad
// night means nothing here; a run of them does), just not previously surfaced as a number.
// ─────────────────────────────────────────────────────────────────────────────

interface Streak {
  length: number
  level: DetectionLevel
  direction: 'worsening' | 'stabilizing' | 'resolving' | null
}

function computeStreak(nights: NightRow[]): Streak | null {
  const measured = nights.filter(n => n.usable).sort((a, b) => a.night_date.localeCompare(b.night_date))
  if (measured.length === 0) return null

  const lastLevel = measured[measured.length - 1].level
  let length = 0
  for (let i = measured.length - 1; i >= 0; i--) {
    if (measured[i].level !== lastLevel) break
    length++
  }

  let direction: Streak['direction'] = null
  if (length >= 2) {
    const tail = measured.slice(-length)
    const first = tail[0].residual_bpm
    const last = tail[tail.length - 1].residual_bpm
    if (first !== null && last !== null) {
      const delta = last - first
      direction = delta > 0.5 ? 'worsening' : delta < -0.5 ? 'resolving' : 'stabilizing'
    }
  }

  return { length, level: lastLevel, direction }
}

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function UrgencyBadge({ urgency }: { urgency: 'same_day' | 'urgent' }) {
  const c = urgency === 'urgent' ? '#ef4444' : '#f59e0b'
  const label = urgency === 'urgent' ? 'URGENT' : 'SAME-DAY'
  return (
    <span style={{
      fontSize: 9, fontFamily: 'var(--font-mono)', fontWeight: 600, letterSpacing: '0.07em',
      color: c, background: c + '20', border: `1px solid ${c}40`,
      borderRadius: 4, padding: '2px 6px',
    }}>{label}</span>
  )
}

function renderMd(text: string) {
  return text.split('\n').map((line, i, arr) => {
    const parts = line.split(/(\*\*[^*]+\*\*)/)
    return (
      <span key={i}>
        {parts.map((p, j) =>
          p.startsWith('**') && p.endsWith('**')
            ? <strong key={j} style={{ color: 'rgba(255,255,255,0.9)', fontWeight: 600 }}>{p.slice(2, -2)}</strong>
            : p
        )}
        {i < arr.length - 1 && <br />}
      </span>
    )
  })
}

function fmtTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
  } catch { return iso }
}

function fmtDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
  } catch { return iso }
}

function parseCitations(json: string): Citation[] {
  try { return JSON.parse(json) as Citation[] } catch { return [] }
}
function parseUncited(json: string): string[] {
  try { return JSON.parse(json) as string[] } catch { return [] }
}

// ─────────────────────────────────────────────────────────────────────────────
// Sparkline
// ─────────────────────────────────────────────────────────────────────────────

function Spark({ data, color, h = 40 }: { data: number[]; color: string; h?: number }) {
  const W = 200, H = h, p = 3
  const slice = data.slice(-14)
  if (slice.length < 2) return <div style={{ height: H }} />
  const mn = Math.min(...slice), mx = Math.max(...slice)
  const rng = mx - mn || 1
  const xs = (i: number) => p + (i / (slice.length - 1)) * (W - p * 2)
  const ys = (v: number) => H - p - ((v - mn) / rng) * (H - p * 2)
  const d = slice.map((v, i) => `${i === 0 ? 'M' : 'L'}${xs(i).toFixed(1)},${ys(v).toFixed(1)}`).join(' ')
  const area = `${d} L${xs(slice.length - 1).toFixed(1)},${H} L${p},${H} Z`
  const id = `g${color.replace('#', '')}`
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: H, display: 'block' }}>
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.25" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#${id})`} />
      <path d={d} fill="none" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={xs(slice.length - 1)} cy={ys(slice[slice.length - 1])} r="3.5" fill={color} />
    </svg>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Full line chart — real nights, real band, no fabricated sigma multiplier
// ─────────────────────────────────────────────────────────────────────────────

function LineChart({
  points: rawPoints, band, color = '#f59e0b', height = 160, unit = '',
}: {
  points: { date: string; v: number | null }[]
  band?: { lo: number | null; hi: number | null }[]
  color?: string; height?: number; unit?: string
}) {
  const [hover, setHover] = useState<number | null>(null)
  const W = 600, H = height, pad = { t: 8, b: 24, l: 36, r: 12 }
  const points = rawPoints.map((p, i) => ({ date: p.date, v: p.v, lo: band?.[i]?.lo ?? null, hi: band?.[i]?.hi ?? null }))
  const values = points.map(p => p.v).filter((v): v is number => v !== null)
  const bands = points.flatMap(p => [p.lo, p.hi]).filter((v): v is number => v !== null)
  if (values.length < 2) {
    return <div style={{ height: H, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-tertiary)', fontSize: 12 }}>Not enough measured nights yet to draw a chart.</div>
  }
  const mn = Math.min(...values, ...bands)
  const mx = Math.max(...values, ...bands)
  const rng = mx - mn || 1
  const n = points.length
  const xs = (i: number) => pad.l + (i / (n - 1)) * (W - pad.l - pad.r)
  const ys = (v: number) => pad.t + ((mx - v) / rng) * (H - pad.t - pad.b)

  // Build a line path over indices that have a reading, breaking across gaps.
  const segments: string[] = []
  let current = ''
  points.forEach((p, i) => {
    if (p.v === null) { if (current) { segments.push(current); current = '' } return }
    current += `${current ? 'L' : 'M'}${xs(i).toFixed(1)},${ys(p.v).toFixed(1)} `
  })
  if (current) segments.push(current)

  const lastIdx = [...points].map((p, i) => (p.lo !== null ? i : -1)).filter(i => i >= 0).pop()
  const bandLo = lastIdx !== undefined ? points[lastIdx].lo : null
  const bandHi = lastIdx !== undefined ? points[lastIdx].hi : null
  const yTicks = [0, 1, 2, 3, 4].map(k => mn + (rng / 4) * k)
  const xLabels = [0, Math.floor((n - 1) / 2), n - 1].map(i => ({ i, label: i === n - 1 ? 'today' : points[i].date.slice(5) }))

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height, display: 'block', cursor: 'crosshair' }}
      onMouseLeave={() => setHover(null)}
      onMouseMove={e => {
        const r = (e.currentTarget as SVGSVGElement).getBoundingClientRect()
        const rx = ((e.clientX - r.left) / r.width) * W
        const idx = Math.round(((rx - pad.l) / (W - pad.l - pad.r)) * (n - 1))
        setHover(Math.max(0, Math.min(n - 1, idx)))
      }}
    >
      {yTicks.map((v, k) => (
        <g key={k}>
          <line x1={pad.l} y1={ys(v)} x2={W - pad.r} y2={ys(v)} stroke="rgba(0,0,0,0.05)" strokeWidth="1" />
          <text x={pad.l - 4} y={ys(v) + 4} textAnchor="end" fontSize="9" fontFamily="var(--font-mono)" fill="#9ca3af">{v.toFixed(0)}</text>
        </g>
      ))}
      {bandLo !== null && bandHi !== null && (
        <rect x={pad.l} y={ys(bandHi)} width={W - pad.l - pad.r} height={ys(bandLo) - ys(bandHi)} fill={color} opacity="0.06" />
      )}
      {segments.map((d, i) => (
        <path key={i} d={d} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      ))}
      {points.map((p, i) => p.v !== null && (
        <circle key={i} cx={xs(i)} cy={ys(p.v)} r={hover === i ? 3.5 : 1.6} fill={color} />
      ))}
      {xLabels.map(({ i, label }) => (
        <text key={i} x={xs(i)} y={H - 6} textAnchor="middle" fontSize="9" fontFamily="var(--font-mono)" fill="#9ca3af">{label}</text>
      ))}
      {hover !== null && points[hover].v !== null && (
        <g>
          <line x1={xs(hover)} y1={pad.t} x2={xs(hover)} y2={H - pad.b} stroke="rgba(0,0,0,0.08)" strokeWidth="1" />
          <rect x={Math.min(xs(hover) + 8, W - 68)} y={ys(points[hover].v as number) - 24} width={60} height={18} rx="6" fill="#0e0e1c" />
          <text x={Math.min(xs(hover) + 8, W - 68) + 30} y={ys(points[hover].v as number) - 11} textAnchor="middle"
            fontSize="10" fontFamily="var(--font-mono)" fill={color} fontWeight="600">
            {points[hover].v} {unit}
          </text>
        </g>
      )}
    </svg>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Vital card
// ─────────────────────────────────────────────────────────────────────────────

function VitalCard({
  series, selected, onClick, footnote,
}: { series: VitalSeries; selected: boolean; onClick: () => void; footnote?: React.ReactNode }) {
  if (!series.available) {
    return (
      <div style={{
        background: 'var(--card-bg)', border: '1.5px solid transparent', borderRadius: 'var(--card-radius)',
        padding: '16px 18px', boxShadow: 'var(--card-shadow)', opacity: 0.6,
      }}>
        <div style={{ color: 'var(--text-secondary)', fontSize: 11, fontWeight: 500, marginBottom: 8 }}>{series.label}</div>
        <div style={{ color: 'var(--text-tertiary)', fontSize: 11, lineHeight: 1.5 }}>{series.unavailableReason ?? 'Not computed by this device.'}</div>
      </div>
    )
  }
  const delta = (series.current ?? 0) - (series.baseline ?? 0)
  const sigmas = series.sigma ? (Math.abs(delta) / series.sigma).toFixed(1) : null
  const deviant = series.sigma ? Math.abs(delta) / series.sigma >= 1.5 : false
  const sign = delta > 0 ? '+' : ''

  return (
    <button onClick={onClick} style={{
      background: selected ? series.color + '12' : 'var(--card-bg)',
      border: `1.5px solid ${selected ? series.color : 'transparent'}`,
      borderRadius: 'var(--card-radius)', padding: '16px 18px',
      boxShadow: selected ? `0 0 0 1px ${series.color}25, var(--card-shadow)` : 'var(--card-shadow)',
      textAlign: 'left', cursor: 'pointer', transition: 'all 0.18s', width: '100%',
    }}>
      <div style={{ color: 'var(--text-secondary)', fontSize: 11, fontWeight: 500, marginBottom: 8 }}>{series.label}</div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 4, marginBottom: 10 }}>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 28, fontWeight: 700, color: deviant ? series.color : 'var(--text-primary)', lineHeight: 1 }}>
          {series.current ?? '—'}
        </span>
        <span style={{ color: 'var(--text-tertiary)', fontSize: 12 }}>{series.unit}</span>
      </div>
      {series.data && series.data.length >= 2 ? <Spark data={series.data} color={series.color} h={36} /> : <div style={{ height: 36 }} />}
      <div style={{ marginTop: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          {series.baseline !== undefined && <span style={{ color: 'var(--text-tertiary)', fontSize: 10, fontFamily: 'var(--font-mono)' }}>base {series.baseline}</span>}
          {series.usableNights !== undefined && (
            <span style={{ color: 'var(--text-tertiary)', fontSize: 9, fontFamily: 'var(--font-mono)', marginLeft: 5, opacity: 0.7 }}>
              · {series.usableNights}n · {series.rung}
            </span>
          )}
        </div>
        {deviant && sigmas && (
          <span style={{ fontSize: 10, fontFamily: 'var(--font-mono)', fontWeight: 700, color: series.color, background: series.color + '18', borderRadius: 6, padding: '2px 7px' }}>
            {sign}{delta % 1 === 0 ? delta : delta.toFixed(1)} · {sigmas}σ
          </span>
        )}
      </div>
      {footnote}
    </button>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Streak — multi-night persistence, computed client-side, not fetched. A caption on the
// Sleep card rather than its own tile: it's context for that number, not a vital itself.
// ─────────────────────────────────────────────────────────────────────────────

const STREAK_COLOR: Record<DetectionLevel, string> = { GREEN: '#0f5132', YELLOW: '#b8860b', RED: '#842029', NA: '#5b6169' }
const DIRECTION_LABEL: Record<NonNullable<Streak['direction']>, string> = {
  worsening: 'worsening', stabilizing: 'holding steady', resolving: 'resolving',
}

function StreakFootnote({ streak }: { streak: Streak | null }) {
  if (!streak || streak.length === 0) return null
  const color = STREAK_COLOR[streak.level]
  const noun = streak.length === 1 ? 'night' : 'nights'
  return (
    <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid rgba(0,0,0,0.06)', display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
      <span style={{ fontSize: 10, fontFamily: 'var(--font-mono)', fontWeight: 700, color, background: color + '18', borderRadius: 6, padding: '2px 7px' }}>
        {streak.length} {streak.level.toLowerCase()} {noun}
      </span>
      {streak.direction && (
        <span style={{ color: 'var(--text-tertiary)', fontSize: 10 }}>{DIRECTION_LABEL[streak.direction]}</span>
      )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Oxygen spot checks — real readings, deliberately not a baseline vital. Matches how the
// backend itself treats this channel: stored, shown, never given a personal range.
// See docs/DESIGN-DATA-CHANNELS.md.
// ─────────────────────────────────────────────────────────────────────────────

function OxygenSpotChecks({ readings }: { readings: OxygenReading[] }) {
  return (
    <div style={{ background: 'var(--card-bg)', borderRadius: 'var(--card-radius)', padding: '18px 20px', boxShadow: 'var(--card-shadow)', marginBottom: 20 }}>
      <div style={{ color: 'var(--text-secondary)', fontSize: 11, fontWeight: 500, marginBottom: 4 }}>Recent SpO₂ spot checks</div>
      <p style={{ color: 'var(--text-tertiary)', fontSize: 10.5, lineHeight: 1.5, margin: '0 0 12px' }}>
        Spot measurements, not a stream — a handful across a week, and no personal baseline
        is computed from them. Shown as individual readings on purpose, not a trend line.
      </p>
      {readings.length === 0 ? (
        <div style={{ color: 'var(--text-tertiary)', fontSize: 12 }}>No readings in the last 7 days.</div>
      ) : (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {[...readings].reverse().map((r, i) => (
            <div key={i} style={{ background: '#f9fafb', borderRadius: 10, padding: '8px 12px', minWidth: 110 }}>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 18, fontWeight: 700, color: r.percentage <= 92 ? '#842029' : r.percentage <= 94 ? '#664d03' : '#0f5132' }}>
                {r.percentage.toFixed(0)}%
              </div>
              <div style={{ color: 'var(--text-tertiary)', fontSize: 9.5, fontFamily: 'var(--font-mono)', marginTop: 2 }}>
                {fmtDate(r.ts_utc)} {fmtTime(r.ts_utc)}
              </div>
            </div>
          ))}
        </div>
      )}
      <p style={{ color: 'var(--text-tertiary)', fontSize: 9.5, marginTop: 10, fontStyle: 'italic' }}>
        Coloring only, not a diagnosis: NHS England COVID Oximetry @home, 92% or below is
        emergency care, 93 to 94% is a same-day GP contact. That pathway was written for
        people already diagnosed with COVID-19, not as a screening rule for someone well.
      </p>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Chat panel (right, light) — real conversation, real pending question, real send
// ─────────────────────────────────────────────────────────────────────────────

function ChatPanel({
  subjectId, sessions, pending, onAfterAction, onClose,
}: {
  subjectId: string; sessions: ConversationSession[]; pending: PendingInteraction | null
  onAfterAction: () => void; onClose?: () => void
}) {
  const [input, setInput] = useState('')
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null)
  const [sending, setSending] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  const messages: ChatMessage[] = useMemo(() => {
    const turns: ConversationTurn[] = sessions.flatMap(s => s.turns).sort((a, b) => a.seq - b.seq)
    return turns.map(t => ({
      role: t.role, text: t.text, ts: fmtTime(t.created_at_utc), urgency: t.urgency,
      citations: parseCitations(t.citations_json), uncited: parseUncited(t.uncited_json),
    }))
  }, [sessions])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length, pending])

  const send = async () => {
    const text = input.trim()
    if (!text || sending) return
    setInput('')
    setSending(true)
    try {
      await api.postMessage(subjectId, text, pending?.episode_id)
      onAfterAction()
    } finally {
      setSending(false)
    }
  }

  const answerPending = async (optionId: string) => {
    if (!pending?.question) return
    setSending(true)
    try {
      await api.submitAnswer(pending.episode_id, { probe_id: pending.question.probe.probe_id, option_id: optionId })
      onAfterAction()
    } finally {
      setSending(false)
    }
  }

  return (
    <div style={{ background: '#fff', display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div style={{ padding: '14px 16px', borderBottom: '1px solid rgba(0,0,0,0.08)', display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
        <div style={{ width: 32, height: 32, borderRadius: 9, flexShrink: 0, background: 'linear-gradient(135deg,rgba(245,158,11,0.15),rgba(34,211,238,0.12))', border: '1px solid rgba(245,158,11,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
            <path d="M7.5 1.5L11 5.5H8.5V9.5H6.5V5.5H4L7.5 1.5Z" fill="#f59e0b" />
            <path d="M2 11.5h11" stroke="#22d3ee" strokeWidth="1.2" strokeLinecap="round" />
            <circle cx="7.5" cy="13" r="0.8" fill="#22d3ee" />
          </svg>
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ color: 'var(--text-primary)', fontSize: 13, fontWeight: 600, lineHeight: 1.2 }}>Agent Chat</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <div className="pulse" style={{ width: 5, height: 5, borderRadius: '50%', background: pending ? '#f59e0b' : '#9ca3af' }} />
            <span style={{ color: 'var(--text-tertiary)', fontSize: 10, fontFamily: 'var(--font-mono)' }}>
              {pending ? 'AWAITING YOUR REPLY' : 'IDLE'} · {messages.filter(m => m.role === 'agent').length} agent turns
            </span>
          </div>
        </div>
        {onClose && (
          <button onClick={onClose}
            style={{ width: 30, height: 30, border: 'none', background: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: 8, color: 'var(--text-tertiary)' }}
            title="Close chat">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M1.5 1.5L12.5 12.5M12.5 1.5L1.5 12.5" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
            </svg>
          </button>
        )}
      </div>

      {activeCitation && (
        <div style={{ margin: '10px 13px 0', padding: '11px 13px', background: 'rgba(34,211,238,0.06)', border: '1px solid rgba(34,211,238,0.2)', borderRadius: 12, flexShrink: 0 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
            <span style={{ color: '#0891b2', fontSize: 10, fontFamily: 'var(--font-mono)' }}>Source</span>
            <button onClick={() => setActiveCitation(null)} style={{ background: 'none', border: 'none', color: 'var(--text-tertiary)', fontSize: 16, cursor: 'pointer', lineHeight: 1 }}>×</button>
          </div>
          <div style={{ color: 'var(--text-primary)', fontSize: 12, fontWeight: 500, lineHeight: 1.4, marginBottom: 4 }}>{activeCitation.title}</div>
          <p style={{ color: 'var(--text-secondary)', fontSize: 11, lineHeight: 1.6, margin: 0, fontStyle: 'italic' }}>"{activeCitation.passage.slice(0, 400)}"</p>
        </div>
      )}

      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 13px', display: 'flex', flexDirection: 'column', gap: 14 }}>
        {messages.length === 0 && (
          <div style={{ color: 'var(--text-tertiary)', fontSize: 12, textAlign: 'center', marginTop: 20 }}>
            No conversation yet. The agent speaks only when it has something worth an interruption.
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} style={{ display: 'flex', flexDirection: msg.role === 'user' ? 'row-reverse' : 'row', gap: 8, alignItems: 'flex-end' }}>
            <div style={{ flexShrink: 0 }}>
              {msg.role === 'agent' ? (
                <div style={{ width: 24, height: 24, borderRadius: 7, background: 'linear-gradient(135deg,rgba(245,158,11,0.15),rgba(34,211,238,0.12))', border: '1px solid rgba(245,158,11,0.25)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <svg width="11" height="11" viewBox="0 0 11 11" fill="none"><path d="M5.5 1L8.5 4.5H6.5V7.5H4.5V4.5H2.5L5.5 1Z" fill="#f59e0b" /><path d="M1 8.5h9" stroke="#22d3ee" strokeWidth="0.9" strokeLinecap="round" /></svg>
                </div>
              ) : (
                <div style={{ width: 24, height: 24, borderRadius: 7, background: '#f3f4f6', border: '1px solid rgba(0,0,0,0.08)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-tertiary)', fontSize: 8, fontWeight: 700 }}>YOU</div>
              )}
            </div>
            <div style={{ maxWidth: '84%', display: 'flex', flexDirection: 'column', gap: 4 }}>
              <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexDirection: msg.role === 'user' ? 'row-reverse' : 'row' }}>
                <span style={{ color: 'var(--text-tertiary)', fontSize: 9, fontFamily: 'var(--font-mono)' }}>{msg.ts}</span>
                {msg.urgency && <UrgencyBadge urgency={msg.urgency} />}
              </div>
              <div style={{
                padding: '10px 12px',
                background: msg.role === 'user' ? '#f59e0b' : '#f9fafb',
                border: `1px solid ${msg.role === 'user' ? 'transparent' : 'rgba(0,0,0,0.07)'}`,
                borderRadius: msg.role === 'user' ? '14px 4px 14px 14px' : '4px 14px 14px 14px',
              }}>
                <p style={{ color: msg.role === 'user' ? '#fff' : 'var(--text-secondary)', fontSize: 12, lineHeight: 1.65, margin: 0 }}>
                  {renderMd(msg.text)}
                </p>
                {msg.citations && msg.citations.length > 0 && (
                  <div style={{ marginTop: 8, display: 'flex', gap: 4, flexWrap: 'wrap', alignItems: 'center' }}>
                    <span style={{ color: 'var(--text-tertiary)', fontSize: 10, fontFamily: 'var(--font-mono)' }}>Sources</span>
                    {msg.citations.map((c, j) => (
                      <button key={j} onClick={() => setActiveCitation(p => p?.source_id === c.source_id ? null : c)} style={{
                        width: 18, height: 18, borderRadius: 4, border: 'none', cursor: 'pointer',
                        background: activeCitation?.source_id === c.source_id ? '#0891b2' : 'rgba(34,211,238,0.15)',
                        color: activeCitation?.source_id === c.source_id ? '#fff' : '#0891b2',
                        fontSize: 9, fontFamily: 'var(--font-mono)', fontWeight: 700,
                      }}>{j + 1}</button>
                    ))}
                    {msg.uncited && msg.uncited.length > 0 && (
                      <span title={msg.uncited.join(' · ')}
                        style={{ display: 'flex', alignItems: 'center', gap: 3, fontSize: 9, fontFamily: 'var(--font-mono)', color: '#ef4444', background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 4, padding: '2px 5px', cursor: 'help' }}>
                        {msg.uncited.length} not from a cited source
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}

        {pending?.kind === 'question' && pending.question && (
          <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
            <div style={{ width: 24, height: 24, borderRadius: 7, background: 'linear-gradient(135deg,rgba(245,158,11,0.15),rgba(34,211,238,0.12))', border: '1px solid rgba(245,158,11,0.25)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
              <svg width="11" height="11" viewBox="0 0 11 11" fill="none"><path d="M5.5 1L8.5 4.5H6.5V7.5H4.5V4.5H2.5L5.5 1Z" fill="#f59e0b" /></svg>
            </div>
            <div style={{ maxWidth: '84%', display: 'flex', flexDirection: 'column', gap: 6 }}>
              <div style={{ padding: '10px 12px', background: '#fff7ed', border: '1px solid #fde68a', borderRadius: '4px 14px 14px 14px' }}>
                <p style={{ color: 'var(--text-primary)', fontSize: 12, lineHeight: 1.6, margin: 0, fontWeight: 500 }}>{pending.question.text}</p>
              </div>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {pending.question.options.map(opt => (
                  <button key={opt.option_id} disabled={sending} onClick={() => answerPending(opt.option_id)} style={{
                    padding: '6px 12px', borderRadius: 20, border: '1px solid #fde68a', background: '#fff',
                    color: '#92400e', fontSize: 11, fontWeight: 500, cursor: sending ? 'default' : 'pointer',
                  }}>{opt.label}</button>
                ))}
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div style={{ padding: '10px 13px', borderTop: '1px solid rgba(0,0,0,0.08)', flexShrink: 0, display: 'flex', gap: 8 }}>
        <textarea value={input} onChange={e => setInput(e.target.value)} rows={1}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
          placeholder="Tell the agent how you're feeling…"
          style={{ flex: 1, background: '#f3f4f6', border: '1px solid rgba(0,0,0,0.08)', borderRadius: 12, color: 'var(--text-primary)', fontSize: 12, padding: '9px 13px', resize: 'none', outline: 'none', lineHeight: 1.5 }}
        />
        <button onClick={send} disabled={!input.trim() || sending} style={{
          padding: '0 14px', borderRadius: 12, border: 'none', cursor: 'pointer',
          background: input.trim() && !sending ? '#f59e0b' : '#f3f4f6',
          color: input.trim() && !sending ? '#fff' : 'var(--text-tertiary)',
          fontSize: 12, fontWeight: 700, flexShrink: 0,
        }}>{sending ? '…' : 'Send'}</button>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Dashboard view
// ─────────────────────────────────────────────────────────────────────────────

function DashboardView({
  status, nights, latestDetail, activeEpisode, oxygenReadings,
}: {
  status: SystemStatus | null; nights: NightRow[]; latestDetail: NightDetail | null
  activeEpisode: EpisodeDetail | null; oxygenReadings: OxygenReading[]
}) {
  const [selected, setSelected] = useState<string>('Resting HR')

  const measured = nights.filter(n => n.usable)
  const last = measured[measured.length - 1] ?? null

  // Sleep and steps travel on NightRow itself now, across whatever window `nights` covers
  // (28 nights, one call) — not fetched per-night through NightDetail. Both are
  // frequently null on any single night, so the "current" value is the most recent
  // night that actually has one, not necessarily the very last night.
  const sleepPoints = measured
    .map(n => ({ date: n.night_date, hours: n.sleep_hours }))
    .filter((p): p is { date: string; hours: number } => p.hours !== null)
  const lastSleep = sleepPoints[sleepPoints.length - 1]

  const stepsPoints = measured
    .map(n => ({ date: n.night_date, steps: n.steps_prev_day }))
    .filter((p): p is { date: string; steps: number } => p.steps !== null)
  const lastSteps = stepsPoints[stepsPoints.length - 1]
  const recentSteps = stepsPoints.slice(-7)
  const stepsWeeklyAvg = recentSteps.length > 0
    ? Math.round(recentSteps.reduce((sum, p) => sum + p.steps, 0) / recentSteps.length)
    : undefined

  const streak = useMemo(() => computeStreak(nights), [nights])

  const vitals: VitalSeries[] = [
    {
      label: 'Resting HR', unit: 'bpm', color: '#f59e0b', available: !!last,
      baseline: last?.centre_bpm ?? undefined,
      sigma: latestDetail?.baseline.scale_bpm,
      current: last?.rhr_bpm ?? undefined,
      data: measured.map(n => n.rhr_bpm).filter((v): v is number => v !== null),
      usableNights: status?.usable_nights, rung: status?.rung,
      chartPoints: measured.map(n => ({ date: n.night_date, v: n.rhr_bpm })),
      chartBand: measured.map(n => ({ lo: n.band_lo, hi: n.band_hi })),
    },
    {
      label: 'Sleep', unit: 'h', color: '#c5f041', available: !!lastSleep,
      current: lastSleep?.hours,
      data: sleepPoints.map(p => p.hours),
      unavailableReason: `Not recorded by this device across the last ${measured.length} measured nights.`,
      chartPoints: sleepPoints.map(p => ({ date: p.date, v: p.hours })),
    },
    {
      label: 'Steps (7d avg)', unit: 'steps', color: '#818cf8', available: !!lastSteps,
      current: stepsWeeklyAvg,
      data: stepsPoints.map(p => p.steps),
      unavailableReason: `Not recorded by this device across the last ${measured.length} measured nights.`,
      chartPoints: stepsPoints.map(p => ({ date: p.date, v: p.steps })),
    },
    {
      // Spot checks, not a nightly reading — no baseline/sigma, same as Steps above, but
      // shown here too (not just the detailed panel below) since there's no technical
      // reason to keep a real reading out of the quick-glance row.
      label: 'SpO₂', unit: '%', color: '#22d3ee', available: oxygenReadings.length > 0,
      current: oxygenReadings[oxygenReadings.length - 1]?.percentage,
      data: oxygenReadings.map(r => r.percentage),
      unavailableReason: 'No spot reading in the last 7 days.',
      chartPoints: oxygenReadings.map(r => ({ date: r.ts_utc.slice(0, 10), v: r.percentage })),
    },
  ]
  const activeSeries = vitals.find(s => s.label === selected) ?? vitals[0]

  const differential = useMemo(() => {
    if (!activeEpisode || activeEpisode.belief_history.length === 0) return null
    const [, , latestBelief] = activeEpisode.belief_history[activeEpisode.belief_history.length - 1]
    const first = activeEpisode.belief_history[0][2]
    return { latest: latestBelief, first }
  }, [activeEpisode])

  const causesSorted = differential
    ? (Object.entries(differential.latest.marginals) as [CauseId, number][]).sort((a, b) => b[1] - a[1])
    : []

  const leading = causesSorted[0]
  const leadingFirst = leading && differential ? differential.first.marginals[leading[0]] : undefined

  return (
    <div style={{ height: '100%', overflow: 'hidden' }}>
      <div style={{ overflowY: 'auto', padding: '0 24px 24px 0', height: '100%' }}>
        {/* alert / reassurance */}
        {activeEpisode && activeEpisode.summary.state !== 'CLOSED' ? (
          <div style={{ background: '#fff', borderRadius: 16, padding: '14px 18px', marginBottom: 20, boxShadow: 'var(--card-shadow)', display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ width: 36, height: 36, borderRadius: 10, background: '#fff7ed', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                <path d="M9 2.5L15.5 14H2.5L9 2.5Z" stroke="#f59e0b" strokeWidth="1.4" strokeLinejoin="round" />
                <path d="M9 7.5V10" stroke="#f59e0b" strokeWidth="1.4" strokeLinecap="round" />
                <circle cx="9" cy="12" r="0.8" fill="#f59e0b" />
              </svg>
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ color: 'var(--text-primary)', fontSize: 13, fontWeight: 600, marginBottom: 2 }}>
                Investigation open · {activeEpisode.summary.night_span[0]} to {activeEpisode.summary.night_span[1]}
              </div>
              <div style={{ color: 'var(--text-secondary)', fontSize: 11.5 }}>
                State: {activeEpisode.summary.state.replace('_', ' ')}
                {leading && <> · leading hypothesis {CAUSE_LABELS[leading[0]]} at {(leading[1] * 100).toFixed(0)}%</>}
              </div>
            </div>
            <div style={{ flexShrink: 0, textAlign: 'right' }}>
              <div style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: '#f59e0b', fontWeight: 700 }}>ACTIVE</div>
            </div>
          </div>
        ) : (
          <div style={{ background: '#fff', borderRadius: 16, padding: '14px 18px', marginBottom: 20, boxShadow: 'var(--card-shadow)', display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ width: 36, height: 36, borderRadius: 10, background: '#e6f4ea', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M3 8l3.5 3.5L13 5" stroke="#0f5132" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" /></svg>
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ color: 'var(--text-primary)', fontSize: 13, fontWeight: 600, marginBottom: 2 }}>Nothing is waiting for you right now.</div>
              <div style={{ color: 'var(--text-secondary)', fontSize: 11.5 }}>
                {status ? `${status.quiet_nights_streak} quiet nights in a row · baseline ${status.rung.toLowerCase()}` : 'Loading status…'}
              </div>
            </div>
          </div>
        )}

        {/* vitals */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, marginBottom: 20 }}>
          {vitals.map(s => (
            <VitalCard
              key={s.label}
              series={s}
              selected={selected === s.label}
              onClick={() => setSelected(s.label)}
              footnote={s.label === 'Sleep' ? <StreakFootnote streak={streak} /> : undefined}
            />
          ))}
        </div>

        {/* chart */}
        <div style={{ background: 'var(--card-bg)', borderRadius: 'var(--card-radius)', padding: '20px 22px', boxShadow: 'var(--card-shadow)', marginBottom: 20 }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 16 }}>
            <div>
              <div style={{ color: 'var(--text-secondary)', fontSize: 11, fontWeight: 500, marginBottom: 4 }}>{activeSeries.label} · {nights.length} nights</div>
              <div style={{ display: 'flex', gap: 10, alignItems: 'baseline' }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 32, fontWeight: 700, color: activeSeries.color, lineHeight: 1 }}>{activeSeries.current ?? '—'}</span>
                <span style={{ color: 'var(--text-tertiary)', fontSize: 14 }}>{activeSeries.unit}</span>
                {latestDetail && activeSeries.label === 'Resting HR' && latestDetail.detection.robust_z !== null && (
                  <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', fontWeight: 700, color: activeSeries.color, background: activeSeries.color + '15', borderRadius: 8, padding: '3px 9px', marginLeft: 4 }}>
                    robust z {latestDetail.detection.robust_z.toFixed(2)}
                  </span>
                )}
              </div>
            </div>
          </div>
          {activeSeries.chartPoints && activeSeries.chartPoints.length >= 2
            ? <LineChart points={activeSeries.chartPoints} band={activeSeries.chartBand} color={activeSeries.color} height={170} unit={activeSeries.unit} />
            : <div style={{ height: 170, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-tertiary)', fontSize: 12 }}>{activeSeries.unavailableReason ?? 'Not enough measured nights yet to draw a chart.'}</div>
          }
        </div>

        {/* bottom row */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          {/* night detail */}
          <div style={{ background: 'var(--card-bg)', borderRadius: 'var(--card-radius)', padding: '18px 20px', boxShadow: 'var(--card-shadow)' }}>
            <div style={{ color: 'var(--text-secondary)', fontSize: 11, fontWeight: 500, marginBottom: 14 }}>Last measured night</div>
            {latestDetail ? (
              <>
                <div style={{ display: 'flex', gap: 20, marginBottom: 14 }}>
                  <div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 26, fontWeight: 700, color: '#f59e0b', lineHeight: 1 }}>{latestDetail.row.rhr_bpm} bpm</div>
                    <div style={{ color: 'var(--text-tertiary)', fontSize: 10, marginTop: 2 }}>resting HR</div>
                  </div>
                  <div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 26, fontWeight: 700, color: '#9b8fef', lineHeight: 1 }}>{Math.round(latestDetail.row.coverage_minutes / 60 * 10) / 10}h</div>
                    <div style={{ color: 'var(--text-tertiary)', fontSize: 10, marginTop: 2 }}>watch coverage</div>
                  </div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {[
                    ['Your normal', `${latestDetail.baseline.centre_bpm} bpm (${latestDetail.baseline.usable_nights}n, ${latestDetail.baseline.rung})`],
                    ['Usual range', `${latestDetail.row.band_lo?.toFixed(1)}–${latestDetail.row.band_hi?.toFixed(1)} bpm`],
                    ['Deviation', `${latestDetail.row.deviation_bpm} bpm`],
                    ['Level', latestDetail.row.level],
                  ].map(([k, v]) => (
                    <div key={k} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                      <span style={{ color: 'var(--text-tertiary)' }}>{k}</span>
                      <span style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>{v}</span>
                    </div>
                  ))}
                </div>
              </>
            ) : <div style={{ color: 'var(--text-tertiary)', fontSize: 12 }}>No measured night yet.</div>}
          </div>

          {/* differential — full 12-cause posterior, not just the top hypothesis */}
          <div style={{ background: 'var(--card-bg)', borderRadius: 'var(--card-radius)', padding: '18px 20px', boxShadow: 'var(--card-shadow)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <span style={{ color: 'var(--text-secondary)', fontSize: 10, fontWeight: 500 }}>Differential · all 12 causes</span>
              {leading && leadingFirst !== undefined && (
                <span style={{ color: 'var(--text-tertiary)', fontSize: 9, fontFamily: 'var(--font-mono)' }}>
                  {CAUSE_LABELS[leading[0]]} {(leadingFirst * 100).toFixed(0)}%
                  <span style={{ color: '#f59e0b', margin: '0 3px' }}>→</span>
                  {(leading[1] * 100).toFixed(0)}%
                </span>
              )}
            </div>
            {causesSorted.length > 0 ? causesSorted.map(([cause, pct], i) => (
              <div key={cause} style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 5 }}>
                <span style={{ width: 110, color: 'var(--text-secondary)', fontSize: 10, flexShrink: 0 }}>{CAUSE_LABELS[cause]}</span>
                <div style={{ flex: 1, height: 5, background: '#f3f4f6', borderRadius: 3, overflow: 'hidden' }}>
                  <div style={{ height: '100%', width: `${pct * 100}%`, background: i === 0 ? '#f59e0b' : '#9b8fef', borderRadius: 3, transition: 'width 0.4s ease' }} />
                </div>
                <span style={{ width: 34, color: i === 0 ? '#f59e0b' : 'var(--text-tertiary)', fontSize: 9, fontFamily: 'var(--font-mono)', fontWeight: 600, textAlign: 'right' }}>{(pct * 100).toFixed(0)}%</span>
              </div>
            )) : <div style={{ color: 'var(--text-tertiary)', fontSize: 12 }}>No investigation has run yet — nothing for the belief network to show.</div>}
          </div>
        </div>

        <OxygenSpotChecks readings={oxygenReadings} />
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Pipeline view — real safety provenance table, real per-night step trace
// ─────────────────────────────────────────────────────────────────────────────

function PipelineView({ safetyRules, activeEpisode }: { safetyRules: SafetyRuleProvenance[]; activeEpisode: EpisodeDetail | null }) {
  const layers = [
    { label: 'Detection', color: '#f59e0b', items: ['pandas + NumPy personal baseline', 'Chronos-Bolt zero-shot forecast', '28-day rolling median & MAD', 'Multi-signal persistence', 'Red-flag intercept (hard-coded)'], note: 'LLM never invoked on quiet nights.' },
    { label: 'Reasoning', color: '#9b8fef', items: ['pgmpy Bayesian network', '12-cause differential', 'Literature clinical priors', 'EVSI interrupt policy', 'LangGraph + SQLite checkpointer'], note: 'LLM only handles natural language generation.' },
    { label: 'Retrieval', color: '#34d399', items: ['Hybrid BM25 + dense retrieval', 'MedlinePlus corpus, attribution-only', 'Verbatim claim-to-source enforcement', 'Unsupported claims stripped, not shown', 'Self-hosted LLM behind the API'], note: 'Every factual claim must match a source verbatim.' },
  ]

  const stages = activeEpisode?.stages ?? []

  return (
    <div style={{ background: 'var(--canvas-bg)', height: '100%', overflowY: 'auto', padding: '24px' }}>
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontFamily: 'var(--font-display)', fontSize: 22, fontWeight: 500, color: 'var(--text-primary)', marginBottom: 4 }}>System Pipeline</div>
        <p style={{ color: 'var(--text-secondary)', fontSize: 12 }}>End-to-end architecture — from watch sensor to agent response.</p>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 14, marginBottom: 20 }}>
        {layers.map(layer => (
          <div key={layer.label} style={{ background: 'var(--card-bg)', borderRadius: 'var(--card-radius)', padding: '18px 20px', boxShadow: 'var(--card-shadow)', borderTop: `3px solid ${layer.color}` }}>
            <div style={{ color: layer.color, fontSize: 11, fontFamily: 'var(--font-mono)', fontWeight: 700, marginBottom: 12 }}>{layer.label.toUpperCase()} LAYER</div>
            {layer.items.map(item => (
              <div key={item} style={{ display: 'flex', gap: 8, marginBottom: 7 }}>
                <div style={{ width: 4, height: 4, borderRadius: '50%', background: layer.color, flexShrink: 0, marginTop: 5 }} />
                <span style={{ color: 'var(--text-secondary)', fontSize: 12 }}>{item}</span>
              </div>
            ))}
            <div style={{ marginTop: 10, paddingTop: 10, borderTop: `1px solid ${layer.color}20` }}>
              <p style={{ color: 'var(--text-tertiary)', fontSize: 10.5, lineHeight: 1.5, margin: 0, fontStyle: 'italic' }}>{layer.note}</p>
            </div>
          </div>
        ))}
      </div>

      {/* real stage trace for the active episode */}
      {activeEpisode && (
        <div style={{ background: 'var(--card-bg)', borderRadius: 'var(--card-radius)', padding: '20px 22px', boxShadow: 'var(--card-shadow)', marginBottom: 20 }}>
          <div style={{ color: 'var(--text-secondary)', fontSize: 11, fontWeight: 500, marginBottom: 14 }}>
            Node trace · episode {activeEpisode.summary.episode_id}
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {stages.map(stage => (
              <div key={stage.name} style={{
                padding: '8px 12px', borderRadius: 10, minWidth: 150,
                background: stage.status === 'RAN' ? 'rgba(34,197,94,0.06)' : 'rgba(0,0,0,0.03)',
                border: `1px solid ${stage.status === 'RAN' ? 'rgba(34,197,94,0.25)' : 'rgba(0,0,0,0.08)'}`,
              }}>
                <div style={{ fontSize: 11, fontFamily: 'var(--font-mono)', fontWeight: 700, color: stage.status === 'RAN' ? '#0f5132' : 'var(--text-tertiary)' }}>{stage.name}</div>
                <div style={{ fontSize: 9, color: stage.status === 'RAN' ? '#166534' : 'var(--text-tertiary)', fontFamily: 'var(--font-mono)', marginTop: 2 }}>{stage.status}</div>
                <div style={{ fontSize: 10, color: 'var(--text-tertiary)', marginTop: 4, lineHeight: 1.4 }}>{stage.reason}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Safety rule catalog — real GET /knowledge/safety-provenance */}
      <div style={{ background: 'var(--card-bg)', borderRadius: 'var(--card-radius)', padding: '18px 20px', boxShadow: 'var(--card-shadow)', marginBottom: 20, borderTop: '3px solid #ef4444' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
          <div style={{ color: '#ef4444', fontSize: 11, fontFamily: 'var(--font-mono)', fontWeight: 700 }}>SAFETY LAYER · RED-FLAG RULE CATALOG</div>
          <span style={{ fontSize: 9, fontFamily: 'var(--font-mono)', color: 'var(--text-tertiary)' }}>{safetyRules.length} rules</span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
          {safetyRules.map(r => (
            <div key={r.rule} style={{ background: '#f9fafb', borderRadius: 10, padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: 4 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <span style={{ color: 'var(--text-primary)', fontSize: 11, fontWeight: 500, lineHeight: 1.3, flex: 1, fontFamily: 'var(--font-mono)' }}>{r.rule}</span>
                <span style={{
                  fontSize: 8, fontFamily: 'var(--font-mono)', fontWeight: 700, marginLeft: 6, flexShrink: 0,
                  color: r.provenance === 'CITED' ? '#0891b2' : r.provenance === 'DERIVED' ? '#9b8fef' : '#f59e0b',
                  background: r.provenance === 'CITED' ? 'rgba(8,145,178,0.1)' : r.provenance === 'DERIVED' ? 'rgba(155,143,239,0.1)' : 'rgba(245,158,11,0.1)',
                  borderRadius: 3, padding: '1px 4px',
                }}>{r.provenance}</span>
              </div>
              <span style={{ color: 'var(--text-tertiary)', fontSize: 9, fontFamily: 'var(--font-mono)' }}>{r.number}</span>
              <span style={{ color: 'var(--text-tertiary)', fontSize: 9.5, lineHeight: 1.5 }} title={r.basis}>{r.basis.slice(0, 160)}{r.basis.length > 160 ? '…' : ''}</span>
            </div>
          ))}
        </div>
        <p style={{ color: 'var(--text-tertiary)', fontSize: 10, marginTop: 10, lineHeight: 1.5, fontStyle: 'italic' }}>
          Hard-coded arithmetic rules evaluated before any LLM call. Firing overrides the agent. The AI can never make anything less urgent.
        </p>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Settings view — real GET/POST /settings, honest about what has no backend field
// ─────────────────────────────────────────────────────────────────────────────

function SettingsView({ settings, status, onSaved }: { settings: Settings | null; status: SystemStatus | null; onSaved: (s: Settings) => void }) {
  const [sec, setSec] = useState<'device' | 'agent' | 'model' | 'privacy'>('device')
  const [interruptionBudget, setInterruptionBudget] = useState(settings?.interruption_budget_per_week ?? 2)
  const [costWeight, setCostWeight] = useState(settings?.policy_cost_weight ?? 0.2)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (settings) { setInterruptionBudget(settings.interruption_budget_per_week); setCostWeight(settings.policy_cost_weight) }
  }, [settings])

  const save = async (patch: Partial<Settings>) => {
    setSaving(true)
    try {
      const updated = await api.updateSettings(patch)
      onSaved(updated)
    } finally { setSaving(false) }
  }

  const sections = [
    { id: 'device', label: 'Device & Data' }, { id: 'agent', label: 'Agent Behavior' },
    { id: 'model', label: 'Model & RAG' }, { id: 'privacy', label: 'Privacy' },
  ] as const

  const bridgeStatus = status?.components.find(c => c.component === 'bridge')
  const llmStatus = status?.components.find(c => c.component === 'llm')

  return (
    <div style={{ background: 'var(--canvas-bg)', height: '100%', display: 'grid', gridTemplateColumns: '200px 1fr', overflow: 'hidden' }}>
      <div style={{ background: 'var(--card-bg)', borderRight: '1px solid rgba(0,0,0,0.07)', padding: '24px 14px', display: 'flex', flexDirection: 'column', gap: 2 }}>
        <div style={{ color: 'var(--text-tertiary)', fontSize: 9, fontFamily: 'var(--font-mono)', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 10, paddingLeft: 10 }}>Sections</div>
        {sections.map(s => (
          <button key={s.id} onClick={() => setSec(s.id)} style={{
            background: sec === s.id ? 'rgba(197,240,65,0.12)' : 'none',
            border: `1px solid ${sec === s.id ? 'rgba(197,240,65,0.3)' : 'transparent'}`,
            borderRadius: 10, padding: '9px 12px', textAlign: 'left', cursor: 'pointer',
            color: sec === s.id ? '#5a7a00' : 'var(--text-secondary)', fontSize: 13,
            fontWeight: sec === s.id ? 600 : 400,
          }}>{s.label}</button>
        ))}
      </div>
      <div style={{ overflowY: 'auto', padding: '28px 32px', display: 'flex', flexDirection: 'column', gap: 18 }}>
        {sec === 'device' && (
          <>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: 20, color: 'var(--text-primary)', marginBottom: -10 }}>Device & Data</div>
            <div style={{ background: 'var(--card-bg)', borderRadius: 16, padding: '16px 18px', boxShadow: 'var(--card-shadow)', borderLeft: `4px solid ${bridgeStatus?.ok ? '#22d3ee' : '#ef4444'}` }}>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 10 }}>
                <div className="pulse" style={{ width: 7, height: 7, borderRadius: '50%', background: bridgeStatus?.ok ? '#22d3ee' : '#ef4444' }} />
                <span style={{ color: bridgeStatus?.ok ? '#22d3ee' : '#ef4444', fontSize: 11, fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
                  {bridgeStatus?.detail ?? 'Unknown'}
                </span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
                {[
                  { k: 'Baseline', v: status ? `${status.usable_nights}n · ${status.rung}` : '—' },
                  { k: 'Last sync', v: status?.last_ingest_utc ? fmtTime(status.last_ingest_utc) : 'never' },
                  { k: 'Quiet streak', v: status ? `${status.quiet_nights_streak} nights` : '—' },
                ].map(r => (
                  <div key={r.k}><div style={{ color: 'var(--text-tertiary)', fontSize: 10, marginBottom: 2 }}>{r.k}</div><div style={{ color: 'var(--text-secondary)', fontSize: 12 }}>{r.v}</div></div>
                ))}
              </div>
            </div>
            <div style={{ padding: '13px 16px', background: '#f3f4f6', border: '1px solid rgba(0,0,0,0.08)', borderRadius: 14 }}>
              <p style={{ color: 'var(--text-secondary)', fontSize: 11.5, lineHeight: 1.6, margin: 0 }}>
                The baseline window and detection thresholds are fixed constants in the backend, not user-configurable — there is no <code>/settings</code> field for either, so they are shown, not edited.
              </p>
            </div>
          </>
        )}
        {sec === 'agent' && (
          <>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: 20, color: 'var(--text-primary)', marginBottom: -10 }}>Agent Behavior</div>
            <div style={{ background: 'var(--card-bg)', borderRadius: 16, padding: '16px 18px', boxShadow: 'var(--card-shadow)' }}>
              <div style={{ color: 'var(--text-primary)', fontSize: 13, fontWeight: 600, marginBottom: 3 }}>Interruption budget per week</div>
              <div style={{ color: 'var(--text-tertiary)', fontSize: 11.5, marginBottom: 12 }}>How many unprompted questions the agent may ask in seven days. Real backend field.</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <input type="range" min={0} max={7} step={1} value={interruptionBudget}
                  onChange={e => setInterruptionBudget(parseInt(e.target.value, 10))}
                  onMouseUp={() => save({ interruption_budget_per_week: interruptionBudget })}
                  style={{ flex: 1, accentColor: '#c5f041' }} />
                <span style={{ color: '#5a7a00', fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: 13, minWidth: 70 }}>{interruptionBudget} / week</span>
              </div>
            </div>
            <div style={{ background: 'var(--card-bg)', borderRadius: 16, padding: '16px 18px', boxShadow: 'var(--card-shadow)' }}>
              <div style={{ color: 'var(--text-primary)', fontSize: 13, fontWeight: 600, marginBottom: 3 }}>Policy cost weight</div>
              <div style={{ color: 'var(--text-tertiary)', fontSize: 11.5, marginBottom: 12 }}>Weight on interruption cost inside the EVSI decision — higher means the agent needs more expected information gain before it asks. Real backend field (<code>policy_cost_weight</code>).</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <input type="range" min={0.05} max={0.60} step={0.05} value={costWeight}
                  onChange={e => setCostWeight(parseFloat(e.target.value))}
                  onMouseUp={() => save({ policy_cost_weight: costWeight })}
                  style={{ flex: 1, accentColor: '#c5f041' }} />
                <span style={{ color: '#5a7a00', fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: 13, minWidth: 40 }}>{costWeight.toFixed(2)}</span>
              </div>
            </div>
            {saving && <div style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>Saving…</div>}
            <div style={{ padding: '13px 16px', background: '#fffbeb', border: '1px solid #fde68a', borderRadius: 14 }}>
              <p style={{ color: '#92400e', fontSize: 11.5, lineHeight: 1.6, margin: 0 }}>The red-flag escalation intercept is hard-coded and cannot be disabled from here or anywhere else. It sits above the agent, not inside its settings.</p>
            </div>
          </>
        )}
        {sec === 'model' && (
          <>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: 20, color: 'var(--text-primary)', marginBottom: -10 }}>Model & RAG</div>
            <div style={{ background: 'var(--card-bg)', borderRadius: 16, padding: '16px 18px', boxShadow: 'var(--card-shadow)' }}>
              <div style={{ color: 'var(--text-primary)', fontSize: 13, fontWeight: 600, marginBottom: 12 }}>LLM Endpoint</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                {[
                  { k: 'Provider', v: settings?.llm_provider ?? '—' },
                  { k: 'Model', v: settings?.llm_model ?? '—' },
                  { k: 'Base URL', v: settings?.llm_base_url ?? 'not set' },
                  { k: 'Status', v: llmStatus?.detail ?? '—' },
                ].map(r => (
                  <div key={r.k} style={{ background: '#f9fafb', borderRadius: 10, padding: '10px 12px' }}>
                    <div style={{ color: 'var(--text-tertiary)', fontSize: 10, marginBottom: 3 }}>{r.k}</div>
                    <div style={{ color: 'var(--text-primary)', fontSize: 12, fontFamily: 'var(--font-mono)', fontWeight: 500, wordBreak: 'break-all' }}>{r.v}</div>
                  </div>
                ))}
              </div>
            </div>
            <div style={{ padding: '13px 16px', background: '#f3f4f6', border: '1px solid rgba(0,0,0,0.08)', borderRadius: 14 }}>
              <p style={{ color: 'var(--text-secondary)', fontSize: 11.5, lineHeight: 1.6, margin: 0 }}>
                Retrieval grounding is a deterministic verbatim-containment check, not a cosine-similarity threshold — there is no numeric slider to show here honestly. A claim's <code>evidence_span</code> either appears in a retrieved passage or it is stripped and counted as unsupported.
              </p>
            </div>
          </>
        )}
        {sec === 'privacy' && (
          <>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: 20, color: 'var(--text-primary)', marginBottom: -10 }}>Privacy</div>
            <div style={{ padding: '14px 16px', background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 14 }}>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 6 }}>
                <div style={{ width: 7, height: 7, borderRadius: '50%', background: '#22c55e' }} />
                <span style={{ color: '#166534', fontSize: 11, fontFamily: 'var(--font-mono)', fontWeight: 700 }}>LOCAL-FIRST, SINGLE USER</span>
              </div>
              <p style={{ color: '#15803d', fontSize: 11.5, lineHeight: 1.6, margin: 0 }}>
                Health data and the API stay on this machine, bound to localhost with no authentication — a deliberate scope decision for a single-person tool, not a production posture.
                {settings?.llm_provider !== 'cassette' && settings?.llm_base_url && (
                  <> The text sent to the LLM currently leaves the machine, to <strong>{settings.llm_base_url}</strong> — that is a real limitation of a hosted model, stated rather than hidden.</>
                )}
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Root
// ─────────────────────────────────────────────────────────────────────────────

const NAV_ITEMS = [
  {
    id: 'dashboard' as View, label: 'Dashboard',
    icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="1.5" y="1.5" width="5.5" height="5.5" rx="1.5" stroke="currentColor" strokeWidth="1.2" /><rect x="9" y="1.5" width="5.5" height="5.5" rx="1.5" stroke="currentColor" strokeWidth="1.2" /><rect x="1.5" y="9" width="5.5" height="5.5" rx="1.5" stroke="currentColor" strokeWidth="1.2" /><rect x="9" y="9" width="5.5" height="5.5" rx="1.5" stroke="currentColor" strokeWidth="1.2" /></svg>,
  },
  {
    id: 'pipeline' as View, label: 'Pipeline',
    icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="1" y="3" width="4" height="3" rx="1" stroke="currentColor" strokeWidth="1.1" /><rect x="6" y="6" width="4" height="3" rx="1" stroke="currentColor" strokeWidth="1.1" /><rect x="11" y="3" width="4" height="3" rx="1" stroke="currentColor" strokeWidth="1.1" /><rect x="6" y="10" width="4" height="3" rx="1" stroke="currentColor" strokeWidth="1.1" /><path d="M5 4.5h1M10 7.5h1M10 4.5H11M8 9V10" stroke="currentColor" strokeWidth="1" strokeLinecap="round" /></svg>,
  },
  {
    id: 'settings' as View, label: 'Settings',
    icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="2.2" stroke="currentColor" strokeWidth="1.1" /><path d="M8 1.5v1.5M8 13v1.5M14.5 8H13M3 8H1.5M12.2 3.8l-1.1 1.1M4.9 11.1l-1.1 1.1M12.2 12.2l-1.1-1.1M4.9 4.9L3.8 3.8" stroke="currentColor" strokeWidth="1.1" strokeLinecap="round" /></svg>,
  },
]

export default function App() {
  const [view, setView] = useState<View>('dashboard')
  const [chatOpen, setChatOpen] = useState(false)
  const backend = useBackend()
  const {
    subject, status, nights, latestDetail, episodes, activeEpisode, pending, sessions,
    safetyRules, settings, oxygenReadings, error, loading, refresh,
  } = backend

  const hasUnread = !!pending

  if (loading) {
    return <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)', fontSize: 13 }}>Connecting to the agent backend…</div>
  }

  if (error) {
    return (
      <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 12 }}>
        <div style={{ color: '#ef4444', fontSize: 14, fontWeight: 600 }}>Could not reach the application.</div>
        <div style={{ color: 'var(--text-tertiary)', fontSize: 12, maxWidth: 420, textAlign: 'center' }}>{error}</div>
        <div style={{ color: 'var(--text-tertiary)', fontSize: 11 }}>Is the backend running? <code>uv run wha serve</code> or <code>uv run python tools/demo_film/serve_demo.py</code></div>
        <button onClick={refresh} style={{ padding: '8px 16px', borderRadius: 10, border: '1px solid rgba(0,0,0,0.1)', background: '#fff', cursor: 'pointer' }}>Retry</button>
      </div>
    )
  }

  if (!subject) {
    return <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-tertiary)' }}>No subject configured on this backend yet.</div>
  }

  const openEpisode = episodes.find(e => e.state !== 'CLOSED')
  const sessionCard = activeEpisode
  const initials = subject.label.split(/\s+/).map(w => w[0]).join('').slice(0, 2).toUpperCase()

  return (
    <div style={{ height: '100vh', display: 'grid', gridTemplateColumns: '196px 1fr', overflow: 'hidden', position: 'relative' }}>
      {/* Sidebar */}
      <aside style={{ background: 'var(--sidebar-bg)', display: 'flex', flexDirection: 'column', borderRight: '1px solid var(--sidebar-border)', overflow: 'hidden' }}>
        <div style={{ padding: '20px 18px 16px', borderBottom: '1px solid var(--sidebar-border)', flexShrink: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
            <div style={{ width: 30, height: 30, borderRadius: 8, background: 'linear-gradient(135deg,rgba(245,158,11,0.3),rgba(34,211,238,0.2))', border: '1px solid rgba(245,158,11,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M7 1.5L10.5 6H8V9.5H6V6H3.5L7 1.5Z" fill="#f59e0b" />
                <path d="M2 11h10" stroke="#22d3ee" strokeWidth="1.2" strokeLinecap="round" />
                <circle cx="7" cy="12.5" r="0.8" fill="#22d3ee" />
              </svg>
            </div>
            <div>
              <div style={{ color: '#fff', fontSize: 14, fontWeight: 700, lineHeight: 1.1 }}>Vital Agent</div>
              <div style={{ color: 'var(--sidebar-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }}>health triage</div>
            </div>
          </div>
        </div>

        <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--sidebar-border)', flexShrink: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
            <div style={{ width: 32, height: 32, borderRadius: '50%', flexShrink: 0, background: 'linear-gradient(135deg,#9b8fef,#c5f041)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#0e0e1c', fontSize: 11, fontWeight: 800 }}>{initials}</div>
            <div>
              <div style={{ color: '#fff', fontSize: 12, fontWeight: 600, lineHeight: 1.2 }}>{subject.label}</div>
              <div style={{ color: 'var(--sidebar-muted)', fontSize: 10 }}>{subject.usable_nights} nights · {subject.rung}</div>
            </div>
          </div>
        </div>

        <nav style={{ flex: 1, padding: '12px 10px', display: 'flex', flexDirection: 'column', gap: 2 }}>
          {NAV_ITEMS.map(item => (
            <button key={item.id} onClick={() => setView(item.id)} style={{
              display: 'flex', alignItems: 'center', gap: 10, padding: '9px 12px',
              borderRadius: 10, border: 'none', cursor: 'pointer',
              background: view === item.id ? 'rgba(255,255,255,0.1)' : 'none',
              color: view === item.id ? '#fff' : 'var(--sidebar-muted)',
              fontSize: 13, fontWeight: view === item.id ? 600 : 400,
              width: '100%', textAlign: 'left',
            }}>
              {item.icon}
              <span style={{ flex: 1 }}>{item.label}</span>
              {item.id === 'dashboard' && hasUnread && view !== item.id && (
                <span style={{ width: 16, height: 16, borderRadius: '50%', background: '#f59e0b', color: '#070912', fontSize: 9, fontWeight: 800, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>!</span>
              )}
            </button>
          ))}
        </nav>

        <div style={{ padding: '14px', flexShrink: 0 }}>
          {openEpisode ? (
            <div style={{ background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.2)', borderRadius: 12, padding: '12px 13px' }}>
              <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: 7 }}>
                <div className="pulse" style={{ width: 6, height: 6, borderRadius: '50%', background: '#f59e0b' }} />
                <span style={{ color: '#f59e0b', fontSize: 10, fontFamily: 'var(--font-mono)', fontWeight: 700 }}>ACTIVE SESSION</span>
              </div>
              <div style={{ color: 'rgba(255,255,255,0.7)', fontSize: 11.5, fontWeight: 500, marginBottom: 3 }}>{openEpisode.night_span[0]} → {openEpisode.night_span[1]}</div>
              {openEpisode.top_cause && (
                <>
                  <div style={{ color: 'rgba(255,255,255,0.3)', fontSize: 10, marginBottom: 8 }}>{CAUSE_LABELS[openEpisode.top_cause]} → {((openEpisode.top_probability ?? 0) * 100).toFixed(0)}%</div>
                  <div style={{ height: 4, background: 'rgba(255,255,255,0.1)', borderRadius: 2, overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${(openEpisode.top_probability ?? 0) * 100}%`, background: '#f59e0b', borderRadius: 2 }} />
                  </div>
                </>
              )}
            </div>
          ) : (
            <div style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 12, padding: '12px 13px' }}>
              <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: 4 }}>
                <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#9ca3af' }} />
                <span style={{ color: '#9ca3af', fontSize: 10, fontFamily: 'var(--font-mono)', fontWeight: 700 }}>NO OPEN SESSION</span>
              </div>
              <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: 10.5 }}>{sessionCard ? `Last closed: ${sessionCard.summary.disposition ?? 'unresolved'}` : 'No investigation has run yet.'}</div>
            </div>
          )}
        </div>
      </aside>

      {/* Main */}
      <div style={{ overflow: 'hidden', display: 'flex', flexDirection: 'row', background: 'var(--canvas-bg)', minWidth: 0 }}>
        <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column', minWidth: 0, transition: 'flex 0.3s ease' }}>
          <div style={{
            background: 'var(--card-bg)', borderBottom: '1px solid rgba(0,0,0,0.07)',
            padding: '0 24px', height: 56,
            display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0,
          }}>
            <div>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: 18, fontWeight: 500, color: 'var(--text-primary)', lineHeight: 1.1 }}>
                {{ dashboard: 'Health Overview', pipeline: 'System Pipeline', settings: 'Settings' }[view]}
              </div>
              <div style={{ color: 'var(--text-tertiary)', fontSize: 11 }}>
                {view === 'dashboard' && (status?.last_nightly_utc ? `Last scored ${fmtDate(status.last_nightly_utc)} · ${openEpisode ? 'investigation active' : 'no open investigation'}` : 'Waiting for the first night')}
                {view === 'pipeline' && 'Architecture & live telemetry'}
                {view === 'settings' && 'Configure your agent'}
              </div>
            </div>
          </div>

          <div style={{ flex: 1, overflow: 'hidden', padding: view === 'dashboard' ? '20px 0 0 24px' : 0 }}>
            {view === 'dashboard' && <DashboardView status={status} nights={nights} latestDetail={latestDetail} activeEpisode={activeEpisode} oxygenReadings={oxygenReadings} />}
            {view === 'pipeline' && <PipelineView safetyRules={safetyRules} activeEpisode={activeEpisode} />}
            {view === 'settings' && <SettingsView settings={settings} status={status} onSaved={refresh} />}
          </div>
        </div>

        <div style={{
          width: chatOpen ? 360 : 0,
          minWidth: 0, overflow: 'hidden', flexShrink: 0,
          transition: 'width 0.3s cubic-bezier(0.4,0,0.2,1)',
          borderLeft: chatOpen ? '1px solid rgba(0,0,0,0.08)' : 'none',
          background: '#fff',
        }}>
          <div style={{ width: 360, height: '100%' }}>
            <ChatPanel subjectId={subject.subject_id} sessions={sessions} pending={pending} onAfterAction={refresh} onClose={() => setChatOpen(false)} />
          </div>
        </div>
      </div>

      <button
        onClick={() => setChatOpen(o => !o)}
        style={{
          position: 'fixed', bottom: 28, right: 28, zIndex: 50,
          display: chatOpen ? 'none' : 'flex',
          alignItems: 'center', justifyContent: 'center',
          width: 54, height: 54, borderRadius: '50%',
          background: 'linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%)',
          border: 'none', cursor: 'pointer',
          boxShadow: '0 4px 20px rgba(245,158,11,0.5), 0 2px 8px rgba(0,0,0,0.12)',
        }}
        title={chatOpen ? 'Close chat' : 'Open Agent Chat'}
      >
        <svg width="26" height="26" viewBox="0 0 26 26" fill="none">
          <path d="M4 6a3 3 0 013-3h12a3 3 0 013 3v10a3 3 0 01-3 3H15l-3 3-3-3H7a3 3 0 01-3-3V6z" fill="rgba(255,255,255,0.25)" />
          <circle cx="13" cy="3.5" r="1.2" fill="#fff" />
          <line x1="13" y1="4.7" x2="13" y2="6.5" stroke="#fff" strokeWidth="1.2" strokeLinecap="round" />
          <rect x="8" y="9" width="10" height="7" rx="3" fill="#fff" opacity="0.9" />
          <circle cx="10.5" cy="12" r="1.3" fill="#f59e0b" />
          <circle cx="15.5" cy="12" r="1.3" fill="#f59e0b" />
        </svg>
      </button>

      {!chatOpen && hasUnread && (
        <div style={{
          position: 'fixed', bottom: 72, right: 24, zIndex: 51,
          width: 14, height: 14, borderRadius: '50%',
          background: '#ef4444', border: '2px solid #fff',
        }} className="pulse" />
      )}
    </div>
  )
}
