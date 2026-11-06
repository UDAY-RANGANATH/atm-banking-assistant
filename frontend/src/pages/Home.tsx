import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, Grid2x2, HelpCircle } from 'lucide-react'
import { t, Language } from '../i18n'
import { ChatPanel } from '../components/ChatPanel'
import { HelpModal } from '../components/HelpModal'
import { useSession } from '../hooks/useSession'
import { api } from '../services/api'
import { BankingService, ServiceCategory } from '../types'

export default function Home() {
  const { session, sendAiMessage } = useSession()
  const navigate = useNavigate()

  const [services, setServices] = useState<BankingService[]>([])
  const [categories, setCategories] = useState<ServiceCategory[]>([])
  const [activeCategory, setActiveCategory] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [helpModal, setHelpModal] = useState<{ isOpen: boolean; service: any }>({
    isOpen: false,
    service: null,
  })

  const language = (session?.language as Language) || 'en'

  // Fetch categories and services on mount / language change
  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const [cats, svcs] = await Promise.all([
        api.getServiceCategories(),
        api.getServices(),
      ])
      setCategories(cats)
      setServices(svcs)
    } catch (e) {
      // Fallback: backend may not be running; show empty state
      console.error('Failed to load service catalogue:', e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  useEffect(() => {
    if (!session) {
      navigate('/')
    }
  }, [session, navigate])

  const filteredServices = services.filter((s) => {
    const matchCategory = activeCategory === 'all' || s.category === activeCategory
    const matchSearch =
      s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.description.toLowerCase().includes(searchQuery.toLowerCase())
    return matchCategory && matchSearch
  })

  const handleHelp = (service: BankingService) => {
    setHelpModal({ isOpen: true, service })
    sendAiMessage(`Help me understand ${service.name}`).catch(() => {})
  }

  const handleStartApplication = async (service: BankingService) => {
    if (!session) return
    try {
      await api.startApplication(session.sessionId, service.id)
      sendAiMessage(`I want to start the ${service.name} application (Form ${service.formNumber})`).catch(() => {})
      navigate(`/documents/${service.id}`)
    } catch {
      // Fallback: just answer in the assistant if the API fails
      sendAiMessage(`I want to apply for ${service.name}`).catch(() => {})
    }
  }

  // Assistant navigation actions: start the real application (customer's
  // explicit tap) and open its document checklist - the assistant itself
  // never starts, confirms or modifies anything.
  const handleNavigateToService = async (serviceId: string) => {
    if (!session) return
    const service = services.find((s) => s.id === serviceId)
    try {
      await api.startApplication(session.sessionId, serviceId)
    } catch {
      /* may already exist or belong to another step - navigation still proceeds */
    }
    sendAiMessage(service ? `I want to start the ${service.name} application` : `open ${serviceId}`).catch(() => {})
    navigate(`/documents/${serviceId}`)
  }

  const handleCloseHelp = () => {
    setHelpModal({ isOpen: false, service: null })
  }

  return (
    <div className="flex flex-col-reverse lg:flex-row h-screen overflow-hidden">
      {/* Left: Services catalog */}
      <div className="flex-1 bg-slate-100 overflow-y-auto border-r border-slate-200 flex flex-col">
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-2xl font-bold text-navy-900">{t(language, 'services.title')}</h2>
              <p className="text-slate-600 text-sm">{t(language, 'services.subtitle')}</p>
            </div>
            <div className="flex items-center gap-2 bg-white rounded-xl border border-slate-200 p-2">
              <Search size={18} className="text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={t(language, 'services.searchPlaceholder')}
                className="w-full bg-transparent border-none outline-none text-sm text-slate-700 placeholder-slate-400"
              />
            </div>
          </div>

          {/* Category filters */}
          <div className="flex gap-2 mb-6 overflow-x-auto pb-2 scrollbar-hide">
            <button
              onClick={() => setActiveCategory('all')}
              className={`whitespace-nowrap px-4 py-2 rounded-lg text-sm font-medium transition ${
                activeCategory === 'all'
                  ? 'bg-navy-900 text-white'
                  : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
              }`}
            >
              All Services
            </button>
            {categories.map((cat) => (
              <button
                key={cat.key}
                onClick={() => setActiveCategory(cat.key)}
                className={`whitespace-nowrap px-4 py-2 rounded-lg text-sm font-medium transition ${
                  activeCategory === cat.key
                    ? 'bg-navy-900 text-white'
                    : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
                }`}
              >
                {cat.label}
              </button>
            ))}
          </div>

          {/* Loading state */}
          {loading && (
            <div className="col-span-3 text-center py-20 text-slate-500">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-navy-900 mx-auto mb-3"></div>
              <p>{t(language, 'common.loading')}</p>
            </div>
          )}

          {/* Services grid */}
          {!loading && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredServices.length > 0 ? (
                filteredServices.map((service) => (
                  <div
                    key={service.id}
                    className="card-elevated p-5 hover:shadow-xl transition border border-slate-200"
                  >
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-xs font-semibold text-navy-900 uppercase tracking-wider">
                        {service.name.split(' ').slice(0, 2).join(' ')}
                      </span>
                      <span className="text-xs bg-gold-100 text-gold-700 px-2 py-1 rounded">
                        {service.formNumber}
                      </span>
                    </div>
                    <h3 className="text-lg font-bold text-navy-900 mb-1">
                      {service.name}
                    </h3>
                    <p className="text-sm text-slate-600 mb-3 line-clamp-2">
                      {service.description}
                    </p>
                    <div className="flex items-center justify-between mb-3 text-xs">
                      <span className="text-slate-500">{service.estimatedTime}</span>
                      <span className="text-[10px] text-slate-400 uppercase tracking-wider">
                        {service.isPrototype ? 'Prototype' : 'Official'}
                      </span>
                    </div>

                    <div className="space-y-2">
                      <button
                        onClick={() => handleStartApplication(service)}
                        className="w-full kiosk-btn-primary"
                      >
                        {t(language, 'services.startApplication')}
                      </button>
                      <button
                        onClick={() => handleHelp(service)}
                        className="w-full kiosk-btn text-sm border-slate-300 text-slate-700 hover:bg-slate-50 flex items-center justify-center gap-2"
                      >
                        <HelpCircle size={16} />
                        {t(language, 'services.help')}
                      </button>
                    </div>
                  </div>
                ))
              ) : (
                <div className="col-span-3 text-center py-10 text-slate-500">
                  <Grid2x2 size={32} className="mx-auto mb-3 opacity-50" />
                  <p>No services found.</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Right: Chat panel (full-width column on tablet/mobile) */}
      <div className="w-full lg:w-[420px] shrink-0 bg-white border-l border-slate-200 flex flex-col h-[55vh] lg:h-auto p-2 lg:p-0 pt-0">
        <ChatPanel
          language={language}
          welcomeMessage={t(language, 'greeting.' + language)}
          sessionId={session?.sessionId ?? ''}
          onSendMessage={(msg) => sendAiMessage(msg)}
          onNavigateService={(serviceId) => {
            void handleNavigateToService(serviceId)
          }}
        />
      </div>

      {/* Help Modal */}
      <HelpModal
        isOpen={helpModal.isOpen}
        onClose={handleCloseHelp}
        service={helpModal.service}
        language={language}
      />
    </div>
  )
}
