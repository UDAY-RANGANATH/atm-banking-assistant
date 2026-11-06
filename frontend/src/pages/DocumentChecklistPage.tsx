import { useState, useEffect, useCallback } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Scan, HelpCircle } from 'lucide-react'
import { t, Language } from '../i18n'
import { ChatPanel } from '../components/ChatPanel'
import { DocumentProgress } from '../components/DocumentProgress'
import { DocumentItem } from '../components/DocumentItem'
import { useSession } from '../hooks/useSession'
import { api } from '../services/api'
import { DocumentChecklist, DocumentChecklistItem } from '../types'

export function DocumentChecklistPage() {
  const { session, sendAiMessage } = useSession()
  const language = (session?.language as Language) || 'en'
  const navigate = useNavigate()
  const { serviceId } = useParams<{ serviceId: string }>()

  const [checklist, setChecklist] = useState<DocumentChecklist | null>(null)
  const [progress, setProgress] = useState<any>(null)
  const [helpModalDoc, setHelpModalDoc] = useState<DocumentChecklistItem | null>(null)

  const applicationId = session?.sessionId || 'demo-app-001'

  // Load checklist for the service
  const loadChecklist = useCallback(async () => {
    if (!serviceId) return
    try {
      const [chk, prog] = await Promise.all([
        api.getServiceChecklist(serviceId, applicationId),
        api.getChecklistProgress(applicationId, serviceId),
      ])
      setChecklist(chk)
      setProgress(prog)
    } catch (e) {
      console.error('Failed to load checklist:', e)
    }
  }, [serviceId, applicationId])

  useEffect(() => {
    loadChecklist()
  }, [loadChecklist])

  useEffect(() => {
    if (!session) {
      navigate('/')
    }
  }, [session, navigate])

  const handleScan = (doc: DocumentChecklistItem) => {
    sendAiMessage(`I want to scan ${doc.name} for my application`).catch(() => {})
    // Phase 4: open the real camera scanner (capture -> OCR -> review -> confirm)
    navigate(`/scan/${serviceId}/${doc.document_id}`)
  }

  const handleRetake = (doc: DocumentChecklistItem) => {
    sendAiMessage(`I want to rescan ${doc.name}`).catch(() => {})
    // Rescan goes through the same real scanner flow; the server-side scan
    // record handles the needs_rescan -> uploaded transition.
    navigate(`/scan/${serviceId}/${doc.document_id}`)
  }

  const handleHelp = (doc: DocumentChecklistItem) => {
    setHelpModalDoc(doc)
    sendAiMessage(`Help me understand why ${doc.name} is required`).catch(() => {})
  }

  const handleCloseHelp = () => {
    setHelpModalDoc(null)
  }

  const handleStartForm = () => {
    if (!session || !serviceId) return
    sendAiMessage(`I want to proceed to form filling for my application`).catch(() => {})
    navigate(`/application/form/${serviceId}`)
  }

  if (!checklist) {
    return (
      <div className="flex h-screen bg-slate-100 items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-navy-900"></div>
      </div>
    )
  }

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Left: Document Checklist */}
      <div className="flex-1 bg-slate-100 overflow-y-auto border-r border-slate-200 flex flex-col">
        <div className="p-6">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div>
              <button
                onClick={() => navigate('/home')}
                className="flex items-center gap-2 text-slate-600 hover:text-navy-900 transition"
              >
                <ArrowLeft size={18} />
                <span>{t(language, 'nav.back')}</span>
              </button>
              <h2 className="text-2xl font-bold text-navy-900 mt-2">
                {checklist.service_name}
              </h2>
              <p className="text-slate-600 text-sm">
                Form: {checklist.form_number} • {t(language, 'services.documents')}
              </p>
              <span className="text-[10px] bg-gold-100 text-gold-700 px-2 py-0.5 rounded uppercase tracking-wider">
                Prototype form number – not official
              </span>
            </div>
            <div className="text-right">
              <div className="text-xs text-slate-500">
                {t(language, 'services.documents')}
              </div>
              <div className="text-lg font-bold text-navy-900">
                {checklist.total_required + checklist.total_conditional + checklist.total_optional}
              </div>
            </div>
          </div>

          {/* Intro message from AI */}
          <div className="card-elevated p-5 mb-6 border border-slate-200">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 bg-gold-500 rounded-lg flex items-center justify-center text-navy-900 shrink-0">
                <HelpCircle size={18} />
              </div>
              <div>
                <p className="text-sm text-slate-700 leading-relaxed">
                  {t(language, 'services.documents')}:
                  {' '}
                  <span className="font-semibold text-navy-900">
                    To help you complete your {checklist.service_name} application,
                    I need the following documents. Please scan each one carefully.
                  </span>
                </p>
                <p className="text-xs text-slate-500 mt-2">
                  {t(language, 'common.required') === 'This field is required.'
                    ? 'Documents marked as mandatory must be provided.'
                    : ' Documents marked as mandatory must be provided.'}
                </p>
              </div>
            </div>
          </div>

          {/* Progress indicator */}
          {progress && <DocumentProgress language={language} progress={progress} />}

          {/* Document list */}
          <div className="flex-1 overflow-y-auto">
            {checklist.documents.length === 0 ? (
              <div className="text-center py-10 text-slate-500">
                <p>No documents required for this service.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {checklist.documents.map((doc) => (
                  <DocumentItem
                    key={doc.document_id}
                    document={doc}
                    language={language}
                    onScan={handleScan}
                    onHelp={handleHelp}
                    onRetake={handleRetake}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Action buttons at bottom */}
          <div className="p-6 bg-white border-t border-slate-200">
            <div className="space-y-3">
              <button
                onClick={handleStartForm}
                disabled={!progress?.all_mandatory_complete && progress?.total_documents > 0}
                className={`w-full py-4 rounded-xl text-sm font-medium transition ${
                  progress?.all_mandatory_complete || !progress?.total_documents
                    ? 'bg-navy-900 text-white hover:bg-navy-800'
                    : 'bg-slate-300 text-slate-500 cursor-not-allowed'
                }`}
              >
                <span className="flex items-center justify-center gap-2">
                  <Scan size={18} />
                  Proceed to Application Form
                </span>
              </button>
              {!progress?.all_mandatory_complete && progress?.total_documents > 0 && (
                <div className="text-xs text-slate-500 text-center">
                  Please complete all mandatory documents before proceeding.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Right: Chat panel */}
      <div className="w-[420px] bg-white border-l border-slate-200 flex flex-col">
        <ChatPanel
          language={language}
          welcomeMessage={t(language, 'greeting.' + language)}
          sessionId={session?.sessionId ?? ''}
          onSendMessage={(msg) => sendAiMessage(msg)}
          onNavigateService={() => {
            /* document checklist already owns navigation */
          }}
        />
      </div>

      {/* Document Help Modal */}
      {helpModalDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div
            className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm"
            onClick={handleCloseHelp}
          />
          <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 max-h-[80vh] flex flex-col overflow-hidden">
            <div className="bg-navy-900 text-white px-6 py-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-gold-500 rounded-lg flex items-center justify-center text-navy-900">
                  <HelpCircle size={20} />
                </div>
                <div>
                  <h3 className="font-bold text-lg">{t(language, 'services.helpDialogTitle')}</h3>
                  <p className="text-xs text-slate-300">{helpModalDoc.name}</p>
                </div>
              </div>
              <button
                onClick={handleCloseHelp}
                className="text-slate-400 hover:text-white transition"
              >
                <span className="sr-only">Close</span>
                <span className="text-white">✕</span>
              </button>
            </div>

            <div className="overflow-y-auto p-6 max-h-[50vh]">
              <div className="space-y-4">
                {/* Classification */}
                <div className="flex items-center gap-2">
                  <span
                    className={`text-xs font-bold px-2 py-0.5 rounded ${
                      helpModalDoc.mandatory
                        ? 'bg-red-100 text-red-700'
                        : helpModalDoc.conditional
                        ? 'bg-amber-100 text-amber-700'
                        : 'bg-blue-100 text-blue-700'
                    }`}
                  >
                    {helpModalDoc.mandatory && !helpModalDoc.conditional
                      ? t(language, 'services.mandatory')
                      : helpModalDoc.conditional
                      ? t(language, 'services.conditional')
                      : t(language, 'services.optional')}
                  </span>
                </div>

                {/* Description */}
                <div>
                  <h4 className="text-sm font-bold text-navy-900 mb-1 uppercase tracking-wider text-[10px]">
                    What is this document?
                  </h4>
                  <p className="text-sm text-slate-700 leading-relaxed">
                    {helpModalDoc.description}
                  </p>
                </div>

                {/* Purpose */}
                <div>
                  <h4 className="text-sm font-bold text-navy-900 mb-1 uppercase tracking-wider text-[10px]">
                    Why is it required?
                  </h4>
                  <p className="text-sm text-slate-700 leading-relaxed">
                    {helpModalDoc.purpose}
                  </p>
                </div>

                {/* Alternatives */}
                {helpModalDoc.alternatives && helpModalDoc.alternatives.length > 0 && (
                  <div>
                    <h4 className="text-sm font-bold text-navy-900 mb-1 uppercase tracking-wider text-[10px]">
                      {t(language, 'services.alternatives')}
                    </h4>
                    <p className="text-sm text-slate-700 leading-relaxed">
                      {helpModalDoc.alternatives.join(', ')}
                    </p>
                  </div>
                )}

                {/* Extracted fields */}
                {helpModalDoc.extracted_fields && helpModalDoc.extracted_fields.length > 0 && (
                  <div>
                    <h4 className="text-sm font-bold text-navy-900 mb-1 uppercase tracking-wider text-[10px]">
                      {t(language, 'services.extractedFrom')}
                    </h4>
                    <p className="text-sm text-slate-700 leading-relaxed">
                      {helpModalDoc.extracted_fields.map(f => f.replace(/_/g, ' ')).join(', ')}
                    </p>
                  </div>
                )}

                {/* Note */}
                <div className="pt-3 border-t border-slate-200">
                  <p className="text-xs text-slate-500 italic">
                    Scanning or uploading a document does not mean it is officially authenticated.
                    All documents are subject to bank verification.
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-slate-50 border-t border-slate-200 p-4">
              <button
                onClick={handleCloseHelp}
                className="w-full py-3 rounded-lg border border-slate-300 text-slate-700 font-medium hover:bg-slate-100 transition"
              >
                {t(language, 'common.close')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
