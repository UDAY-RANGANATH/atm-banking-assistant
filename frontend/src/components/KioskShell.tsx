import { useState } from 'react'
import { Home, RefreshCw, Globe, HelpCircle, ArrowLeft } from 'lucide-react'
import { Language, LANGUAGE_NAMES } from '../i18n'

interface KioskShellProps {
  language: Language
  onChangeLanguage: (lang: Language) => void
  onRestart: () => void
  onHome: () => void
  children: React.ReactNode
}

export function KioskShell({
  language,
  onChangeLanguage,
  onRestart,
  onHome,
  children,
}: KioskShellProps) {
  const [langMenuOpen, setLangMenuOpen] = useState(false)

  return (
    <div className="min-h-screen bg-slate-100 relative">
      {/* Top kiosk header bar */}
      <header className="bg-navy-900 text-white px-6 py-4 shadow-md border-b border-navy-700">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gold-500 rounded-lg flex items-center justify-center text-navy-900 font-bold text-xl">
              <Home size={24} />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight">AI Banking Assistant</h1>
              <p className="text-xs text-slate-300">Educational Prototype • ATM Kiosk</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Language selector */}
            <div className="relative" onClick={(e) => { e.stopPropagation(); setLangMenuOpen(!langMenuOpen) }}>
              <button className="flex items-center gap-2 px-4 py-2 bg-navy-800 border border-navy-600 rounded-xl text-white text-sm font-medium hover:bg-navy-700 transition">
                <Globe size={18} />
                <span>{LANGUAGE_NAMES[language]}</span>
                <svg className="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              {langMenuOpen && (
                <div className="absolute bottom-full left-0 mb-2 w-48 bg-white border border-slate-200 rounded-xl shadow-xl py-2 z-50">
                  {(['en', 'te', 'hi'] as Language[]).map((lang) => (
                    <button
                      key={lang}
                      onClick={() => {
                        onChangeLanguage(lang)
                        setLangMenuOpen(false)
                      }}
                      className={`w-full text-left px-4 py-2 text-sm transition ${
                        language === lang ? 'bg-gold-100 text-gold-800 font-semibold' : 'text-slate-700 hover:bg-slate-100'
                      }`}
                    >
                      {LANGUAGE_NAMES[lang]}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <button
              onClick={onRestart}
              className="flex items-center gap-2 px-4 py-2 bg-navy-800 border border-navy-600 rounded-xl text-white text-sm font-medium hover:bg-navy-700 transition"
            >
              <RefreshCw size={18} />
              <span className="hidden sm:block">Restart</span>
            </button>
          </div>
        </div>
      </header>

      {/* Demo notice banner */}
      <div className="max-w-7xl mx-auto px-4 py-2">
        <div className="bg-gold-50 border border-gold-200 text-gold-800 text-xs px-4 py-2 rounded-lg flex items-center gap-2">
          <span>⚠️</span>
          <span>DEMONSTRATION PROTOTYPE – Not an official bank form. Not submitted to any financial institution.</span>
        </div>
      </div>

      <main className="max-w-7xl mx-auto px-4 py-6 min-h-[60vh]">
        {children}
      </main>

      {/* Footer / global actions */}
      <footer className="bg-navy-900 border-t border-navy-700 px-6 py-3">
        <div className="max-w-7xl mx-auto flex justify-between items-center text-sm text-slate-400">
          <span>AI Banking Assistant v1.0.0 – Educational Prototype</span>
          <div className="flex items-center gap-6">
            <button
              onClick={onHome}
              className="flex items-center gap-2 hover:text-white transition"
            >
              <ArrowLeft size={16} />
              <span className="hidden sm:inline">Home</span>
            </button>
            <button className="flex items-center gap-2 hover:text-white transition">
              <HelpCircle size={16} />
              <span className="hidden sm:inline">Help</span>
            </button>
          </div>
        </div>
      </footer>
    </div>
  )
}
