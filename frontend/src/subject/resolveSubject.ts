import type { Subject } from '../api'

export type SubjectResolution =
  | { kind: 'selected'; subject: Subject; reason: 'remembered' | 'configured' | 'sole' }
  | { kind: 'choose'; subjects: Subject[] }
  | { kind: 'none' }

export function resolveSubject(
  subjects: Subject[],
  configuredSubjectId: string | null | undefined,
  rememberedSubjectId: string | null,
): SubjectResolution {
  if (rememberedSubjectId) {
    const remembered = subjects.find((subject) => subject.subject_id === rememberedSubjectId)
    if (remembered) return { kind: 'selected', subject: remembered, reason: 'remembered' }
  }

  if (configuredSubjectId) {
    const configured = subjects.find((subject) => subject.subject_id === configuredSubjectId)
    if (configured) return { kind: 'selected', subject: configured, reason: 'configured' }
  }

  if (subjects.length === 1) return { kind: 'selected', subject: subjects[0], reason: 'sole' }
  if (subjects.length === 0) return { kind: 'none' }
  return { kind: 'choose', subjects }
}
