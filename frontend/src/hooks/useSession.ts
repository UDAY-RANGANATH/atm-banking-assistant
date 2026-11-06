import { useState, useCallback, useEffect } from 'react'
import { api } from '../services/api'
import { AppSession, Language } from '../types'

const STORAGE_KEY = 'atm_session'

function loadStoredSession(): AppSession | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (parsed && typeof parsed.sessionId === 'string') return parsed as AppSession
  } catch {
    /* corrupted storage - ignore */
  }
  return null
}

function persistSession(session: AppSession | null) {
  try {
    if (session) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(session))
    } else {
      localStorage.removeItem(STORAGE_KEY)
    }
  } catch {
    /* storage unavailable - prototype silently continues in-memory */
  }
}

export function useSession() {
  // Session lives in localStorage so it survives route navigation between
  // kiosk pages (language select -> home -> checklist -> scanner).
  const [session, setSession] = useState<AppSession | null>(() => loadStoredSession())
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    persistSession(session)
  }, [session])

  const createSession = useCallback(async (language: Language = 'en') => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.createSession(language)
      const newSession: AppSession = {
        sessionId: data.session_id,
        language: data.language as Language,
        currentStep: data.current_step,
      }
      // Persist synchronously: the first navigation (session create -> Home)
      // fires in the same React batch, and the next page's useSession()
      // initializes from localStorage before any effect would persist here.
      persistSession(newSession)
      setSession(newSession)
      return newSession
    } catch (e: any) {
      setError(e.message)
      throw e
    } finally {
      setLoading(false)
    }
  }, [])

  const setLanguage = useCallback(async (language: Language) => {
    if (!session) return
    setLoading(true)
    setError(null)
    try {
      const data = await api.setLanguage(session.sessionId, language)
      if (session) {
        const next: AppSession = {
          ...session,
          language: data.language as Language,
          currentStep: data.current_step,
        }
        persistSession(next)
        setSession(next)
      }
    } catch (e: any) {
      setError(e.message)
      throw e
    } finally {
      setLoading(false)
    }
  }, [session])

  const sendMessage = useCallback(async (message: string) => {
    if (!session) throw new Error('No active session')
    try {
      const response = await api.chat(session.sessionId, message)
      return response
    } catch (e: any) {
      setError(e.message)
      throw e
    }
  }, [session])

  // Phase 7: rich AI conversation (language-aware, actions + suggestions).
  const sendAiMessage = useCallback(async (message: string) => {
    if (!session) throw new Error('No active session')
    try {
      return await api.aiChat(session.sessionId, message, session.language)
    } catch (e: any) {
      setError(e.message)
      throw e
    }
  }, [session])

  const clearError = useCallback(() => setError(null), [])

  return {
    session,
    loading,
    error,
    createSession,
    setLanguage,
    sendMessage,
    sendAiMessage,
    clearError,
    hasSession: !!session,
  }
}
