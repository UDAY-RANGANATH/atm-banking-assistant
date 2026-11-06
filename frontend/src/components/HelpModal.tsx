import { X, ChevronRight, FileText, Clock, UserCheck, Info } from 'lucide-react'
import { t, Language } from '../i18n'

interface HelpModalProps {
  isOpen: boolean
  onClose: () => void
  service: any
  language: Language
}

export function HelpModal({ isOpen, onClose, service, language }: HelpModalProps) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm"
        onClick={onClose}
      />
      {/* Modal */}
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-2xl mx-4 max-h-[90vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="bg-navy-900 text-white px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-gold-500 rounded-lg flex items-center justify-center text-navy-900">
              <Info size={20} />
            </div>
            <div>
              <h3 className="font-bold text-lg">{t(language, 'services.helpDialogTitle')}</h3>
              <p className="text-xs text-slate-300">{service.name}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white transition"
          >
            <X size={20} />
          </button>
        </div>

        {/* Scrollable content */}
        <div className="overflow-y-auto p-6 max-h-[60vh]">
          <div className="space-y-6">
            {/* Form number badge */}
            <div className="flex items-center gap-3">
              <span className="text-xs bg-gold-100 text-gold-800 px-2 py-1 rounded font-medium">
                {service.formNumber}
              </span>
              <span className="text-xs text-slate-500 uppercase tracking-wider">
                {service.isPrototype ? 'Prototype form number' : 'Official form number'}
              </span>
            </div>

            {/* Short description */}
            <div>
              <p className="text-sm text-slate-600 leading-relaxed">{service.description}</p>
            </div>

            {/* Eligibility */}
            <div className="flex items-start gap-3">
              <UserCheck size={20} className="text-gold-500 mt-0.5 flex-shrink-0" />
              <div>
                <div className="text-xs font-semibold text-navy-900 uppercase tracking-wider mb-1">
                  {t(language, 'services.eligibilityLabel')}
                </div>
                <p className="text-sm text-slate-700">{service.eligibility}</p>
              </div>
            </div>

            {/* Estimated time */}
            <div className="flex items-start gap-3">
              <Clock size={20} className="text-gold-500 mt-0.5 flex-shrink-0" />
              <div>
                <div className="text-xs font-semibold text-navy-900 uppercase tracking-wider mb-1">
                  {t(language, 'services.estimatedTimeLabel')}
                </div>
                <p className="text-sm text-slate-700">{service.estimatedTime}</p>
              </div>
            </div>

            {/* Full explanation sections */}
            <div className="pt-4 border-t border-slate-200 space-y-4">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <FileText size={18} className="text-navy-900" />
                  <span className="text-sm font-bold text-navy-900 uppercase tracking-wider">
                    Service Explanation
                  </span>
                </div>
                <div
                  dangerouslySetInnerHTML={{ __html: service.fullExplanation }}
                  className="text-sm text-slate-700 leading-relaxed space-y-3"
                />
              </div>

              {/* Required documents preview */}
              <div className="pt-2">
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-xs font-bold text-navy-900 uppercase tracking-wider">
                    {t(language, 'services.documents')}
                  </span>
                </div>
                <div className="space-y-2">
                  {service.documents.map((doc: any, idx: number) => (
                    <div
                      key={idx}
                      className="flex items-start gap-3 p-3 rounded-xl border border-slate-200 bg-slate-50"
                    >
                      <div className="flex items-center gap-2 mt-0.5">
                        {doc.mandatory ? (
                          <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded">
                            {t(language, 'services.mandatory')}
                          </span>
                        ) : doc.conditional ? (
                          <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded">
                            {t(language, 'services.conditional')}
                          </span>
                        ) : (
                          <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                            {t(language, 'services.optional')}
                          </span>
                        )}
                      </div>
                      <div className="flex-1">
                        <div className="text-sm font-semibold text-navy-900">
                          {doc.name}
                        </div>
                        <p className="text-xs text-slate-600 mt-0.5">{doc.purpose}</p>
                        {doc.alternatives && doc.alternatives.length > 0 && (
                          <p className="text-xs text-slate-500 mt-1 italic">
                            {t(language, 'services.alternatives')}: {doc.alternatives.join(', ')}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer actions */}
        <div className="bg-slate-50 border-t border-slate-200 p-4 flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 py-3 rounded-xl border border-slate-300 text-slate-700 font-medium hover:bg-slate-100 transition"
          >
            {t(language, 'common.cancel')}
          </button>
          <button
            onClick={() => {
              onClose()
              // The parent will handle start application
              if ((window as any).onHelpStartApplication) {
                ;(window as any).onHelpStartApplication(service)
              }
            }}
            className="flex-1 py-3 rounded-xl bg-navy-900 text-white font-medium hover:bg-navy-800 transition flex items-center justify-center gap-2"
          >
            <ChevronRight size={18} />
            <span>{t(language, 'services.startApplication')}</span>
          </button>
        </div>
      </div>
    </div>
  )
}
