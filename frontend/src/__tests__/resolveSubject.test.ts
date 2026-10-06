import { describe, expect, it } from 'vitest'
import { resolveSubject } from '../subject/resolveSubject'
import type { Subject } from '../api'

const people: Subject[] = [
  { subject_id: 'a', label: 'Person A', source_kind: 'synthetic', timezone: 'UTC', usable_nights: 0, rung: 'COLD' },
  { subject_id: 'b', label: 'Person B', source_kind: 'synthetic', timezone: 'UTC', usable_nights: 0, rung: 'COLD' },
]

describe('resolveSubject', () => {
  it('keeps a valid selection made in this app session', () => {
    expect(resolveSubject(people, 'a', 'b')).toMatchObject({ kind: 'selected', subject: people[1], reason: 'remembered' })
  })

  it('uses the configured subject before the sole-subject fallback', () => {
    expect(resolveSubject(people, 'b', null)).toMatchObject({ kind: 'selected', subject: people[1], reason: 'configured' })
  })

  it('uses the sole subject when configuration does not resolve', () => {
    expect(resolveSubject([people[0]], 'missing', null)).toMatchObject({ kind: 'selected', subject: people[0], reason: 'sole' })
  })

  it('requires an explicit choice when several subjects remain', () => {
    expect(resolveSubject(people, 'missing', null)).toEqual({ kind: 'choose', subjects: people })
  })

  it('distinguishes an empty list from ambiguity', () => {
    expect(resolveSubject([], null, null)).toEqual({ kind: 'none' })
  })
})
