import { describe, expect, it } from 'vitest'
import {
  DISCLOSURE_ITEMS,
  EXPLANATION_ITEMS,
  LEGACY_EXPLANATION_KEYS,
  LEGACY_TEST_ASSERTION_MAP,
  PARITY_INVENTORY,
  VISIBLE_LITERAL_SURFACES,
} from '../test/legacyParityInventory'
import { LEGACY_VISIBLE_LITERALS } from '../test/legacyVisibleLiteralInventory'

describe('legacy Streamlit parity inventory', () => {
  it('maps every stable explanation key to a React destination and a copy check', () => {
    expect(LEGACY_EXPLANATION_KEYS).toHaveLength(87)
    expect(new Set(LEGACY_EXPLANATION_KEYS).size).toBe(LEGACY_EXPLANATION_KEYS.length)
    expect(EXPLANATION_ITEMS.map((item) => item.id)).toEqual([...LEGACY_EXPLANATION_KEYS])
    expect(EXPLANATION_ITEMS.every((item) => item.destination && item.verification.startsWith('copy:'))).toBe(true)
  })

  it('maps every disclosure row to its stated live destination', () => {
    expect(DISCLOSURE_ITEMS).toHaveLength(41)
    expect(new Set(DISCLOSURE_ITEMS.map((item) => item.id)).size).toBe(DISCLOSURE_ITEMS.length)
    expect(DISCLOSURE_ITEMS.every((item) => item.destination && item.verification.startsWith('disclosure:'))).toBe(true)
  })

  it('covers every legacy UI source area and every deleted user-visible UI test', () => {
    expect(VISIBLE_LITERAL_SURFACES).toHaveLength(18)
    expect(LEGACY_VISIBLE_LITERALS).toHaveLength(466)
    expect(LEGACY_VISIBLE_LITERALS.every((item) => item.anchor.includes('line ') && item.literal.trim() && item.destination)).toBe(true)
    expect(LEGACY_TEST_ASSERTION_MAP).toHaveLength(11)
    expect(PARITY_INVENTORY.every((item) => item.source && item.anchor && item.destination && item.verification)).toBe(true)
  })
})
