import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { User, ArrowRight } from 'lucide-react'
import { t, Language, LANGUAGE_NAMES, LANGUAGE_FLAGS } from '../i18n'
import { useSession } from '../hooks/useSession'

const LANGUAGES: Language[] = ['en', 'te', 'hi']

export function LanguageSelector() {
  const { createSession, error, clearError, loading } = useSession()
  const navigate = useNavigate()

  const [selectedLang, setSelectedLang] = useState<Language>('en')

  const handleSelectLanguage = async (lang: Language) => {
    setSelectedLang(lang)
    clearError()
    try {
      await createSession(lang)
      navigate('/home')
    } catch {
      // Session may already exist locally; still navigate
      navigate('/home')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-navy-900 px-4">
      <div className="max-w-md w-full">
        {/* Kiosk branding header */}
        <div className="text-center mb-10">
          <div className="w-16 h-16 bg-gold-500 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg shadow-gold-200">
            <User size={32} className="text-navy-900" />
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">{t('en', 'welcome.title')}</h1>
          <p className="text-slate-300 text-lg">{t('en', 'welcome.subtitle')}</p>
          <p className="text-xs text-slate-500 mt-2 uppercase tracking-wider font-semibold">
            Educational Prototype
          </p>
        </div>

        {/* Language selection cards */}
        <div className="space-y-4">
          <p className="text-slate-400 text-sm font-medium mb-6 text-center">
            {t('en', 'welcome.selectLanguage')}
          </p>

          {LANGUAGES.map((lang) => (
            <button
              key={lang}
              onClick={() => handleSelectLanguage(lang)}
              className={`w-full py-6 px-6 rounded-2xl border transition-all duration-200 text-left
                ${
                  selectedLang === lang
                    ? 'bg-navy-800 border-gold-500 text-white shadow-lg shadow-gold-200/50 ring-2 ring-gold-500'
                    : 'bg-white/5 border-slate-700 text-slate-200 hover:bg-white/10 hover:border-slate-500'
                }`}
              disabled={loading}
            >
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-white/20 flex items-center justify-center text-2xl border border-white/10">
                  {LANGUAGE_FLAGS[lang]}
                </div>
                <div>
                  <div className="font-semibold text-lg">{LANGUAGE_NAMES[lang]}</div>
                  <div className="text-xs text-slate-400 mt-1">
                    {lang === 'en' ? 'English' : lang === 'te' ? 'తెలుగు' : 'हिन्दी'}
                  </div>
                </div>
                <div className="ml-auto">
                  <ArrowRight size={20} className="text-slate-400" />
                </div>
              </div>
            </button>
          ))}
        </div>

        {error && (
          <div className="mt-4 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
            {error}
          </div>
        )}

        <div className="mt-8 text-center">
          <p className="text-xs text-slate-500">
            ATM Kiosk Prototype • AI-Powered Banking Assistant
          </p>
        </div>
      </div>
    </div>
  )
}
