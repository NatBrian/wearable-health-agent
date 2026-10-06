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
import { HOW_IT_WORKS_TOPIC_STEPS } from '../components/HowItWorks'

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

  it('covers every recorded pipeline step in How it works exactly once', () => {
    const stepIds = Object.values(HOW_IT_WORKS_TOPIC_STEPS).flat()
    expect(stepIds).toHaveLength(21)
    expect(new Set(stepIds).size).toBe(stepIds.length)
    expect(new Set(stepIds)).toEqual(new Set([
      'collect', 'store', 'sleep_window', 'features', 'baseline', 'subtract_explained',
      'detect', 'safety_floor', 'episode_open', 'preload', 'investigate', 'believe',
      'decide', 'ask', 'answer', 'conclude', 'critique', 'review', 'deliver',
      'safety_phrase_rules', 'safety_triage',
    ]))
  })

  it('covers every legacy UI source area and every deleted user-visible UI test', () => {
    expect(VISIBLE_LITERAL_SURFACES).toHaveLength(18)
    expect(LEGACY_VISIBLE_LITERALS).toHaveLength(466)
    expect(LEGACY_VISIBLE_LITERALS.every((item) => item.anchor.includes('line ') && item.literal.trim() && item.destination)).toBe(true)
    expect(LEGACY_TEST_ASSERTION_MAP).toHaveLength(11)
    expect(PARITY_INVENTORY.every((item) => item.source && item.anchor && item.destination && item.verification)).toBe(true)
  })
})
