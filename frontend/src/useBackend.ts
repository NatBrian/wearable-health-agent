import { useCallback, useEffect, useState } from 'react'
import {
  api,
  type ConversationSession,
  type DashboardSummary,
  type EpisodeDetail,
  type EpisodeSummary,
  type KnowledgeProvenanceSummary,
  type KnowledgeProvenance,
  type NightDetail,
  type NightRow,
  type OxygenReading,
  type PendingInteraction,
  type SafetyRuleProvenance,
  type Settings,
  type SystemStatus,
} from './api'

export type BackendResource =
  | 'status' | 'summary' | 'nights' | 'episodes' | 'pending' | 'sessions'
  | 'safetyRules' | 'settings' | 'oxygenReadings' | 'provenance' | 'knowledgeProvenance'
  | 'latestDetail' | 'activeEpisode'
export type BackendErrors = Partial<Record<BackendResource, string>>

export interface BackendData {
  status: SystemStatus | null
  summary: DashboardSummary | null
  provenance: KnowledgeProvenanceSummary | null
  knowledgeProvenance: KnowledgeProvenance | null
  nights: NightRow[]
  latestDetail: NightDetail | null
  episodes: EpisodeSummary[]
  activeEpisode: EpisodeDetail | null
  pending: PendingInteraction | null
  sessions: ConversationSession[]
  safetyRules: SafetyRuleProvenance[]
  settings: Settings | null
  oxygenReadings: OxygenReading[]
  errors: BackendErrors
  loading: boolean
  error: string | null
  refresh: () => void
}

type BackendSnapshot = Omit<BackendData, 'loading' | 'error' | 'refresh'>

export const PENDING_POLL_INTERVAL_MS = 30_000

const EMPTY_DATA: BackendSnapshot = {
  status: null,
  summary: null,
  provenance: null,
  knowledgeProvenance: null,
  nights: [],
  latestDetail: null,
  episodes: [],
  activeEpisode: null,
  pending: null,
  sessions: [],
  safetyRules: [],
  settings: null,
  oxygenReadings: [],
  errors: {},
}

export function useBackend(subjectId: string | null, historyDays = 28): BackendData {
  const [data, setData] = useState<BackendSnapshot>(EMPTY_DATA)
  const [dataSubjectId, setDataSubjectId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [revision, setRevision] = useState(0)

  const refresh = useCallback(() => setRevision((current) => current + 1), [])

  useEffect(() => {
    if (!subjectId) {
      setData(EMPTY_DATA)
      setDataSubjectId(null)
      setLoading(false)
      setError(null)
      return
    }

    let active = true
    setLoading(true)
    const load = async () => {
      const requests = await Promise.allSettled([
        api.getStatus(subjectId),
        api.getDashboardSummary(subjectId),
        api.listNights(subjectId, historyDays),
        api.listEpisodes(subjectId),
        api.getPending(subjectId),
        api.getConversationSessions(subjectId, 400),
        api.getSafetyProvenance(),
        api.getSettings(),
        api.listOxygenReadings(subjectId, 7),
        api.getKnowledgeProvenanceSummary(),
        api.getKnowledgeProvenance(),
      ])
      if (!active) return

      const resourceOrder: BackendResource[] = [
        'status', 'summary', 'nights', 'episodes', 'pending', 'sessions',
        'safetyRules', 'settings', 'oxygenReadings', 'provenance', 'knowledgeProvenance',
      ]
      const errors: BackendErrors = {}
      requests.forEach((result, index) => {
        if (result.status === 'rejected') errors[resourceOrder[index]] = String(result.reason)
      })
      const value = <T,>(index: number, fallback: T): T => {
        const result = requests[index]
        return result?.status === 'fulfilled' ? result.value as T : fallback
      }
      const nights = value<NightRow[]>(2, [])
      const episodes = value<EpisodeSummary[]>(3, [])
      const measured = nights.filter((night) => night.usable)
      const recentEpisode = episodes.find((episode) => episode.state !== 'CLOSED') ?? episodes[0]

      const [latestDetailResult, episodeResult] = await Promise.allSettled([
        measured.length > 0
          ? api.getNightDetail(subjectId, measured[measured.length - 1].night_date)
          : Promise.resolve(null),
        recentEpisode ? api.getEpisode(recentEpisode.episode_id) : Promise.resolve(null),
      ])
      if (!active) return

      const nextData = {
        status: value<SystemStatus | null>(0, null),
        summary: value<DashboardSummary | null>(1, null),
        provenance: value<KnowledgeProvenanceSummary | null>(9, null),
        knowledgeProvenance: value<KnowledgeProvenance | null>(10, null),
        nights,
        latestDetail: latestDetailResult.status === 'fulfilled' ? latestDetailResult.value : null,
        episodes,
        activeEpisode: episodeResult.status === 'fulfilled' ? episodeResult.value : null,
        pending: value<PendingInteraction | null>(4, null),
        sessions: value<ConversationSession[]>(5, []),
        safetyRules: value<SafetyRuleProvenance[]>(6, []),
        settings: value<Settings | null>(7, null),
        oxygenReadings: value<OxygenReading[]>(8, []),
        errors,
      }
      if (latestDetailResult.status === 'rejected') errors.latestDetail = String(latestDetailResult.reason)
      if (episodeResult.status === 'rejected') errors.activeEpisode = String(episodeResult.reason)
      setData(nextData)
      setDataSubjectId(subjectId)
      setError(Object.values(errors)[0] ?? null)
      setLoading(false)
    }

    void load().catch((exc: unknown) => {
      if (!active) return
      setError(String(exc))
      setLoading(false)
    })

    return () => { active = false }
  }, [subjectId, historyDays, revision])

  useEffect(() => {
    if (!subjectId) return

    let active = true
    let inFlight = false
    const refreshPending = async () => {
      if (!active || inFlight || document.visibilityState === 'hidden') return
      inFlight = true
      try {
        const pending = await api.getPending(subjectId)
        if (!active) return
        setData((current) => {
          const errors = { ...current.errors }
          delete errors.pending
          return { ...current, pending, errors }
        })
      } catch (exc) {
        if (!active) return
        setData((current) => ({ ...current, errors: { ...current.errors, pending: String(exc) } }))
      } finally {
        inFlight = false
      }
    }

    const interval = window.setInterval(() => { void refreshPending() }, PENDING_POLL_INTERVAL_MS)
    document.addEventListener('visibilitychange', refreshPending)
    return () => {
      active = false
      window.clearInterval(interval)
      document.removeEventListener('visibilitychange', refreshPending)
    }
  }, [subjectId])

  const currentData = subjectId === dataSubjectId ? data : EMPTY_DATA
  return {
    ...currentData,
    loading: Boolean(subjectId) && (loading || subjectId !== dataSubjectId),
    error: subjectId === dataSubjectId ? error : null,
    refresh,
  }
}
