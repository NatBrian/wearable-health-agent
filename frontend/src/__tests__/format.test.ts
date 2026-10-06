import { describe, expect, it } from 'vitest'
import { localDateBoundaryUtc } from '../lib/format'

describe('localDateBoundaryUtc', () => {
  it('uses the subject timezone and includes the whole selected date', () => {
    expect(localDateBoundaryUtc('2026-09-28', 'Asia/Singapore')).toBe('2026-09-27T16:00:00.000Z')
    expect(localDateBoundaryUtc('2026-09-28', 'Asia/Singapore', true)).toBe('2026-09-28T15:59:59.999Z')
  })
})
