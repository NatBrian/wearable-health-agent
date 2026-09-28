import type { SystemConfig } from '../api'

export function dateLabel(value: string | null | undefined, timeZone?: string): string {
  if (!value) return 'not recorded'
  const dateOnly = value.length === 10
  const date = new Date(dateOnly ? `${value}T12:00:00Z` : value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(undefined, {
    day: 'numeric', month: 'short', year: 'numeric', ...(dateOnly ? { timeZone: 'UTC' } : timeZone ? { timeZone } : {}),
  }).format(date)
}

export function timeLabel(value: string | null | undefined, timeZone: string): string {
  if (!value) return 'time not recorded'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'time unavailable'
  return new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit', timeZone }).format(date)
}

export function localDateBoundaryUtc(value: string, timeZone: string, inclusiveEnd = false): string {
  const [year, month, day] = value.split('-').map(Number)
  const target = Date.UTC(year, month - 1, day + (inclusiveEnd ? 1 : 0))
  const formatter = new Intl.DateTimeFormat('en-CA', {
    timeZone, year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23',
  })
  const offsetAt = (instant: number) => {
    const parts = Object.fromEntries(formatter.formatToParts(new Date(instant)).map((part) => [part.type, part.value]))
    return Date.UTC(Number(parts.year), Number(parts.month) - 1, Number(parts.day), Number(parts.hour), Number(parts.minute), Number(parts.second)) - instant
  }
  let instant = target - offsetAt(target)
  instant = target - offsetAt(instant)
  if (inclusiveEnd) instant -= 1
  return new Date(instant).toISOString()
}

export function measuredValue(value: number | null | undefined, unit = ''): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return 'not recorded'
  const shown = Number.isInteger(value) ? String(value) : new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 }).format(value)
  return unit ? `${shown} ${unit}` : shown
}

export function signedValue(value: number | null | undefined, unit = ''): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return 'not available'
  const rounded = Number.isInteger(value) ? value : Number(value.toFixed(1))
  const shown = `${rounded > 0 ? '+' : ''}${rounded}`
  return unit ? `${shown} ${unit}` : shown
}

export function sourceLabel(sourceId: string, config: SystemConfig): string {
  const prefixes = config.SOURCE_LABEL_PREFIXES
  if (prefixes && typeof prefixes === 'object') {
    for (const [prefix, label] of Object.entries(prefixes as Record<string, string>)) {
      if (sourceId.startsWith(prefix)) return label
    }
  }
  return typeof config.SOURCE_LABEL_FALLBACK === 'string'
    ? config.SOURCE_LABEL_FALLBACK
    : "this repository's own knowledge"
}

export function isExternalSource(sourceId: string, config: SystemConfig): boolean {
  return typeof config.EXTERNAL_SOURCE_PREFIX === 'string'
    ? sourceId.startsWith(config.EXTERNAL_SOURCE_PREFIX)
    : sourceId.startsWith('medlineplus')
}
