import { describe, expect, it } from 'vitest'
import { LEGACY_COPY } from '../content/legacyCopy'
import { LEGACY_EXPLANATION_KEYS } from '../test/legacyParityInventory'

describe('legacy explanatory copy', () => {
  it('preserves every stable explanation key from Streamlit', () => {
    expect(Object.keys(LEGACY_COPY)).toEqual([...LEGACY_EXPLANATION_KEYS])
  })

  it('keeps the source copy free of typed digits and forbidden reassurance', () => {
    const text = Object.values(LEGACY_COPY).join('\n').toLowerCase()
    expect(text).not.toMatch(/[0-9]/)
    for (const phrase of ['you are fine', "you're fine", 'nothing to worry about', 'definitely not', "it's nothing", 'no need to worry', "that's reassuring", 'that is reassuring', 'thats reassuring']) {
      expect(text).not.toContain(phrase)
    }
  })

  it('keeps self-measured system performance in the experiment records', () => {
    expect(LEGACY_COPY['home.cannot']).toContain('Engineering evaluations are kept in the experiment records')
    expect(LEGACY_COPY['home.cannot']).not.toContain('accuracy it was measured at is published in the record')
  })
})
