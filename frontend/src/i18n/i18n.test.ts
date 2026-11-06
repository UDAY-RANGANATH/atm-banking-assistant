import { describe, it, expect } from 'vitest'
import { translations, t, Language } from './index'

/**
 * Phase 5 frontend unit tests: multilingual form i18n.
 * The three languages must all carry the form.* keys, and parameter
 * substitution must work. Extracted personal data is never run through t().
 */

const LANGS: Language[] = ['en', 'te', 'hi']

const FORM_STATUS_KEYS = [
  'AUTO_FILLED',
  'LOW_CONFIDENCE',
  'CONFLICT',
  'MISSING',
  'CUSTOMER_EDITED',
  'CUSTOMER_CONFIRMED',
]

describe('form i18n sections', () => {
  const statusOf = (lang: Language, status: string): unknown =>
    translations[lang].form.status[status as keyof typeof translations.en.form.status]

  it('all three languages have a form.* section', () => {
    for (const lang of LANGS) {
      expect(translations[lang].form, `form section missing for ${lang}`).toBeTruthy()
    }
  })

  it('status vocabulary keys exist and are translated strings in all languages', () => {
    for (const lang of LANGS) {
      for (const status of FORM_STATUS_KEYS) {
        const value = statusOf(lang, status)
        expect(value, `${lang}.form.status.${status}`).toBeTruthy()
        expect(typeof value, `${lang}.form.status.${status}`).toBe('string')
      }
    }
  })

  it('core UI keys translated (title, autofill, actions, warnings, errors)', () => {
    for (const lang of LANGS) {
      expect(translations[lang].form.title).toBeTruthy()
      expect(translations[lang].form.autofill).toBeTruthy()
      expect(translations[lang].form.actions.editField).toBeTruthy()
      expect(translations[lang].form.actions.acceptValue).toBeTruthy()
      expect(translations[lang].form.actions.clearValue).toBeTruthy()
      expect(translations[lang].form.actions.reviewSource).toBeTruthy()
      expect(translations[lang].form.actions.saveProgress).toBeTruthy()
      expect(translations[lang].form.actions.continue).toBeTruthy()
      expect(translations[lang].form.warnings.title).toBeTruthy()
      expect(translations[lang].form.errors.invalidValue).toBeTruthy()
    }
  })

  it('labels differ across languages (not accidentally identical english)', () => {
    const en = translations.en.form.actions.saveProgress
    const te = translations.te.form.actions.saveProgress
    const hi = translations.hi.form.actions.saveProgress
    expect(te).not.toBe(en)
    expect(hi).not.toBe(en)
  })
})

describe('t() lookup and params', () => {
  it('resolves nested keys and falls back to the key when missing', () => {
    expect(t('en', 'form.title')).toBe('Application Form')
    expect(t('en', 'form.does.not.exist')).toBe('form.does.not.exist')
  })

  it('substitutes {{count}} params in warning strings', () => {
    const en = t('en', 'form.warnings.conflict', { count: '3' })
    expect(en).toContain('3')
    expect(en).not.toContain('{{count}}')
    const hi = t('hi', 'form.warnings.missing', { count: '2' })
    expect(hi).toContain('2')
    expect(hi).not.toContain('{{count}}')
  })

  it('returns the key itself for unknown languages instead of crashing', () => {
    expect(t('xx' as unknown as Language, 'form.title')).toBe('form.title')
  })
})
