import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Bot, Eraser, Compass } from 'lucide-react'
import { t, Language } from '../i18n'
import { api } from '../services/api'
import { AIChatAction, AIChatResponse } from '../types'

interface ChatPanelProps {
  language: Language
  welcomeMessage: string
  sessionId: string
  onSendMessage: (message: string) => Promise<AIChatResponse>
  /** Triggers when the customer taps a service navigation action. */
  onNavigateService: (serviceId: string) => void
}

interface PanelMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  actions?: AIChatAction[]
}

export function ChatPanel({
  language,
  welcomeMessage,
  sessionId,
  onSendMessage,
  onNavigateService,
}: ChatPanelProps) {
  const [messages, setMessages] = useState<PanelMessage[]>([
    { role: 'assistant', content: welcomeMessage },
  ])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [suggestions, setSuggestions] = useState<string[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sending])

  // Language-aware suggested questions: session (server) language first.
  useEffect(() => {
    let cancelled = false
    api
      .aiSuggestions(sessionId)
      .then((res) => {
        if (!cancelled && res.language === language && res.suggestions.length) {
          setSuggestions(res.suggestions)
        } else if (!cancelled && res.language !== language && res.suggestions.length) {
          setSuggestions(res.suggestions)
        }
      })
      .catch(() => {
        /* suggestions are optional decoration - do not disturb the user */
      })
    return () => {
      cancelled = true
    }
  }, [sessionId, language])

  const submitMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || sending) return
      setMessages((prev) => [...prev, { role: 'user', content: text }])
      setInput('')
      setSending(true)
      try {
        const response = await onSendMessage(text)
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: response.response,
            actions: response.actions?.filter((a) => a.service_id) ?? [],
          },
        ])
        if (response.suggestions?.length) {
          setSuggestions(response.suggestions)
        }
      } catch {
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', content: t(language, 'chat.error') },
        ])
      } finally {
        setSending(false)
        inputRef.current?.focus()
      }
    },
    [sending, onSendMessage, language],
  )

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    submitMessage(input)
  }

  const handleClearChat = async () => {
    try {
      await api.clearConversation(sessionId)
    } catch {
      /* server-side cleanup is best effort; UI reset always happens */
    }
    setMessages([{ role: 'assistant', content: t(language, 'chat.chatCleared') }])
    setSuggestions([])
    api
      .aiSuggestions(sessionId)
      .then((res) => setSuggestions(res.suggestions))
      .catch(() => {})
  }

  return (
    <div className="bg-white rounded-2xl shadow-xl border border-slate-200 flex flex-col h-full min-h-[400px] overflow-hidden">
      {/* Header */}
      <div className="bg-navy-900 text-white px-5 py-4 flex items-center gap-3">
        <div className="w-8 h-8 bg-gold-500 rounded-lg flex items-center justify-center text-navy-900 shrink-0">
          <Bot size={18} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-sm">{t(language, 'chat.title')}</div>
          <div className="text-xs text-slate-400 flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
            {t(language, 'chat.online')}
          </div>
        </div>
        <button
          type="button"
          onClick={handleClearChat}
          title={t(language, 'chat.clearChat')}
          aria-label={t(language, 'chat.clearChat')}
          className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-300 hover:text-white hover:bg-white/10 transition shrink-0"
        >
          <Eraser size={16} />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, i) =>
          msg.role === 'system' ? null : (
            <div
              key={i}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-in fade-in slide-in-from-y-4 duration-300`}
            >
              <div
                className={`max-w-[85%] px-4 py-3 rounded-2xl ${
                  msg.role === 'user'
                    ? 'bg-navy-900 text-white rounded-tr-none'
                    : 'bg-slate-100 text-slate-800 rounded-tl-none border border-slate-200'
                }`}
              >
                <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                {msg.actions && msg.actions.length > 0 && (
                  <div className="mt-2 flex flex-col gap-2">
                    {msg.actions.map((action, j) =>
                      action.service_id ? (
                        <button
                          key={j}
                          type="button"
                          onClick={() => onNavigateService(action.service_id as string)}
                          className="inline-flex items-center gap-2 text-xs font-medium bg-gold-100 text-gold-700 border border-gold-300 rounded-lg px-3 py-2 hover:bg-gold-200 transition text-left"
                        >
                          <Compass size={14} className="shrink-0" />
                          <span className="truncate">{action.label}</span>
                        </button>
                      ) : null,
                    )}
                  </div>
                )}
              </div>
            </div>
          ),
        )}
        {sending && (
          <div className="flex justify-start" aria-live="polite">
            <div className="bg-slate-100 px-4 py-3 rounded-2xl rounded-tl-none border border-slate-200 animate-pulse">
              <span className="text-sm text-slate-500">{t(language, 'chat.typing')}</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Suggested questions */}
      {suggestions.length > 0 && (
        <div className="px-4 pb-2">
          <div className="text-[10px] uppercase tracking-wider text-slate-400 mb-1">
            {t(language, 'chat.suggestions')}
          </div>
          <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
            {suggestions.map((s, i) => (
              <button
                key={i}
                type="button"
                onClick={() => submitMessage(s)}
                disabled={sending}
                className="whitespace-nowrap text-xs px-3 py-2 rounded-full bg-slate-100 border border-slate-200 text-slate-700 hover:bg-slate-200 hover:border-slate-300 disabled:opacity-50 transition shrink-0"
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="bg-white p-4 border-t border-slate-200">
        <form onSubmit={handleSubmit} className="flex gap-3">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={t(language, 'chat.placeholder')}
            className="flex-1 px-4 py-3 rounded-xl border border-slate-300 text-slate-800 focus:ring-2 focus:ring-gold-500 focus:border-transparent outline-none min-w-0"
            disabled={sending}
          />
          <button
            type="submit"
            disabled={sending || !input.trim()}
            aria-label={t(language, 'chat.sending')}
            className="bg-navy-900 text-white px-5 py-3 rounded-xl font-medium disabled:opacity-50 hover:bg-navy-800 transition flex items-center gap-2 shrink-0"
          >
            <Send size={18} />
          </button>
        </form>
        <div className="mt-2 text-[10px] text-slate-400">{t(language, 'chat.demoMode')}</div>
      </div>
    </div>
  )
}
