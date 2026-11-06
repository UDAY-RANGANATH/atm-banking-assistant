// Localized display helpers for catalogue data (Phase 9).
//
// The API now ships localized display strings for service cards and category
// labels. English canonical fields always remain the fallback, so callers
// never render an empty string if a translation is missing.

import type { BankingService, ServiceCategory, LocalizedServiceView } from '../types'

const SUPPORTED = ['en', 'te', 'hi'] as const

export function normalizeLang(lang: string | undefined | null): string {
  if (lang && (SUPPORTED as readonly string[]).includes(lang)) return lang
  return 'en'
}

/** Null-safe localized view of a service for the current kiosk language. */
export function serviceView(service: BankingService, lang: string): LocalizedServiceView {
  const l = normalizeLang(lang)
  const loc = l !== 'en' ? service.localized?.[l] : undefined
  return {
    name: loc?.name ?? service.name,
    description: loc?.description ?? service.description,
    eligibility: loc?.eligibility ?? service.eligibility,
    estimatedTime: loc?.estimatedTime ?? service.estimatedTime,
  }
}

/** Localized label for a category chip. */
export function categoryLabel(category: ServiceCategory, lang: string): string {
  const l = normalizeLang(lang)
  if (l !== 'en' && category.localizedLabel?.[l]) return category.localizedLabel[l] as string
  return category.label
}
