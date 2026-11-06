import en from './en'
import te from './te'
import hi from './hi'

export type Language = 'en' | 'te' | 'hi'

export const translations: Record<Language, typeof en> = {
  en,
  te,
  hi,
}

export const LANGUAGE_NAMES: Record<Language, string> = {
  en: 'English',
  te: 'తెలుగు (Telugu)',
  hi: 'हिन्दी (Hindi)',
}

export const LANGUAGE_FLAGS: Record<Language, string> = {
  en: '🇺🇸',
  te: '🇮🇳',
  hi: '🇮🇳',
}

export function t(lang: Language, key: string, params?: Record<string, string>): string {
  const keys = key.split('.')
  let value: any = translations[lang]

  for (const k of keys) {
    if (value === undefined || value === null) return key
    value = value[k]
  }

  if (typeof value !== 'string') return key

  // Simple parameter replacement {{param}}
  if (params) {
    let result = value
    for (const [k, v] of Object.entries(params)) {
      result = result.replace(new RegExp(`{{${k}}}`, 'g'), v)
    }
    return result
  }

  return value
}

export default t
