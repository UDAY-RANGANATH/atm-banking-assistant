import { CheckCircle, AlertCircle, Minus, Clock, User } from 'lucide-react'
import { t, Language } from '../i18n'

interface DocumentProgressProps {
  language: Language
  progress: any // ChecklistProgress
}

export function DocumentProgress({ language, progress }: DocumentProgressProps) {
  if (!progress) return null

  const statusLabels: Record<string, Record<Language, string>> = {
    pending: { en: 'Pending', te: 'పెండింగ్', hi: 'लंबित' },
    uploaded: { en: 'Uploaded', te: 'అప్‌లోడ్', hi: 'अपलोड किया गया' },
    readable: { en: 'Readable', te: 'చదవడానికి', hi: 'पठनीय' },
    needs_rescan: { en: 'Needs Rescan', te: 'మళ్లీ స్కెన్', hi: 'पुनः स्कैन की आवश्यकता' },
    optional: { en: 'Optional', te: 'ఐచ్ఛికం', hi: 'वैकल्पिक' },
    not_applicable: { en: 'Not Applicable', te: 'లాగదు', hi: 'लागू नहीं' },
  }

  const statusLabel = (status: string) => {
    return statusLabels[status]?.[language] || statusLabels[status]?.en || status
  }

  return (
    <div className="card-elevated p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-bold text-navy-900">
            {t(language, 'services.documents')} - Progress
          </h3>
          <p className="text-sm text-slate-600">
            {progress.completed}/{progress.total_documents} completed
          </p>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-navy-900">
            {progress.percentage}%
          </div>
          <div className="text-xs text-slate-500">Complete</div>
        </div>
      </div>

      {/* Progress bar */}
      <div className="w-full h-2 bg-slate-200 rounded-full overflow-hidden mb-4">
        <div
          className="h-full bg-gradient-to-r from-navy-900 to-gold-500 transition-all duration-500"
          style={{ width: `${Math.min(progress.percentage, 100)}%` }}
        />
      </div>

      {/* Status summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
        <div className="flex items-center gap-2 p-2 rounded bg-slate-50">
          <CheckCircle size={14} className="text-green-600" />
          <span className="text-slate-700 font-medium">
            {progress.completed}
          </span>
          <span className="text-slate-500">{t(language, 'common.success')}</span>
        </div>
        <div className="flex items-center gap-2 p-2 rounded bg-amber-50">
          <Clock size={14} className="text-amber-600" />
          <span className="text-slate-700 font-medium">{progress.pending}</span>
          <span className="text-slate-500">{statusLabel('pending')}</span>
        </div>
        <div className="flex items-center gap-2 p-2 rounded bg-blue-50">
          <Minus size={14} className="text-blue-600" />
          <span className="text-slate-700 font-medium">{progress.optional}</span>
          <span className="text-slate-500">{statusLabel('optional')}</span>
        </div>
        <div className="flex items-center gap-2 p-2 rounded bg-slate-50">
          <User size={14} className="text-slate-600" />
          <span className="text-slate-700 font-medium">{progress.needs_rescan}</span>
          <span className="text-slate-500">{statusLabel('needs_rescan')}</span>
        </div>
      </div>

      {/* Mandatory completion notice */}
      {progress.all_mandatory_complete === false && progress.total_documents > 0 && (
        <div className="mt-4 p-3 rounded-lg bg-amber-50 border border-amber-200 flex items-start gap-3">
          <AlertCircle size={18} className="text-amber-600 mt-0.5" />
          <div>
            <p className="text-sm text-amber-800 font-medium">
              Not all mandatory documents are complete
            </p>
            <p className="text-xs text-amber-700 mt-1">
              Please complete all mandatory documents before proceeding to form filling.
            </p>
          </div>
        </div>
      )}

      {progress.all_mandatory_complete === true && progress.total_documents > 0 && (
        <div className="mt-4 p-3 rounded-lg bg-green-50 border border-green-200 flex items-start gap-3">
          <CheckCircle size={18} className="text-green-600 mt-0.5" />
          <div>
            <p className="text-sm text-green-800 font-medium">
              All mandatory documents complete
            </p>
            <p className="text-xs text-green-700 mt-1">
              You can proceed to application form filling.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
