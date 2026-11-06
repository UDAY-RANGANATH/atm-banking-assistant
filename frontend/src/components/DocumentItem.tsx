import { Scan, HelpCircle, Upload, RefreshCw, CheckCircle, AlertCircle, Clock } from 'lucide-react'
import { t, Language } from '../i18n'
import { DocumentChecklistItem } from '../types'

interface DocumentItemProps {
  document: DocumentChecklistItem
  language: Language
  onScan: (doc: DocumentChecklistItem) => void
  onHelp: (doc: DocumentChecklistItem) => void
  onRetake: (doc: DocumentChecklistItem) => void
}

const STATUS_CONFIG: Record<string, { labelKey: string; icon: any; color: string; bg: string }> = {
  pending: { labelKey: 'pending', icon: Clock, color: 'text-slate-500', bg: 'bg-slate-50' },
  uploaded: { labelKey: 'uploaded', icon: Upload, color: 'text-blue-600', bg: 'bg-blue-50' },
  readable: { labelKey: 'readable', icon: CheckCircle, color: 'text-green-600', bg: 'bg-green-50' },
  needs_rescan: { labelKey: 'needs_rescan', icon: AlertCircle, color: 'text-amber-600', bg: 'bg-amber-50' },
  optional: { labelKey: 'optional', icon: null, color: 'text-slate-400', bg: 'bg-slate-50' },
  not_applicable: { labelKey: 'not_applicable', icon: null, color: 'text-slate-300', bg: 'bg-slate-50' },
}

const MANDATORY_LABELS: Record<Language, string> = {
  en: 'Mandatory',
  te: 'తప్పనిసరి',
  hi: 'अनिवार्य',
}

const OPTIONAL_LABELS: Record<Language, string> = {
  en: 'Optional',
  te: 'ఐచ్ఛికం',
  hi: 'वैकल्पिक',
}

const CONDITIONAL_LABELS: Record<Language, string> = {
  en: 'Conditional',
  te: 'ಶর্ত groove', // placeholder - actual te/hi translations in i18n
  hi: 'शर्त के अनुसार',
}

export function DocumentItem({
  document,
  language,
  onScan,
  onHelp,
  onRetake,
}: DocumentItemProps) {
  const statusConfig = STATUS_CONFIG[document.status] || STATUS_CONFIG.pending
  const isMandatory = document.mandatory && !document.conditional
  const isConditional = document.conditional

  const getClassificationLabel = () => {
    if (isMandatory) return MANDATORY_LABELS[language]
    if (isConditional) return CONDITIONAL_LABELS[language]
    return OPTIONAL_LABELS[language]
  }

  const getClassificationColor = () => {
    if (isMandatory) return 'bg-red-100 text-red-700'
    if (isConditional) return 'bg-amber-100 text-amber-700'
    return 'bg-blue-100 text-blue-700'
  }

  const getStatusLabel = () => {
    const labels: Record<string, Record<Language, string>> = {
      pending: { en: 'Pending', te: 'పెండింగ్', hi: 'लंबित' },
      uploaded: { en: 'Uploaded', te: 'అప్‌లోడ్', hi: 'अपलोड किया गया' },
      readable: { en: 'Readable', te: 'చదవడానికి', hi: 'पठनीय' },
      needs_rescan: { en: 'Needs Rescan', te: 'మళ్లీ స్కెన్', hi: 'पुनः स्कैन' },
      optional: { en: 'Optional', te: 'ఐచ్ఛికం', hi: 'वैकल्पिक' },
      not_applicable: { en: 'Not Applicable', te: 'లాగదు', hi: 'लागू नहीं' },
    }
    return labels[document.status]?.[language] || labels[document.status]?.en || document.status
  }

  return (
    <div className="card-elevated p-5 mb-4 border border-slate-200 hover:shadow-lg transition group">
      {/* Header row */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-start gap-3 flex-1">
          <div className="flex items-center gap-2 mt-0.5">
            <span className={`text-xs font-bold px-2 py-0.5 rounded ${getClassificationColor()}`}>
              {getClassificationLabel()}
            </span>
            {document.conditional && (
              <span className="text-[10px] text-slate-500 italic">
                {document.conditional_reason || ''}
              </span>
            )}
          </div>
          <div>
            <h4 className="text-sm font-bold text-navy-900">{document.name}</h4>
            <p className="text-xs text-slate-600 mt-1 leading-relaxed">
              {document.purpose}
            </p>
          </div>
        </div>

        {/* Status badge */}
        <div className="text-right">
          <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg ${statusConfig.bg} border border-slate-200`}>
            {statusConfig.icon && <statusConfig.icon size={14} className={statusConfig.color} />}
            <span className={`text-xs font-medium ${statusConfig.color}`}>
              {getStatusLabel()}
            </span>
          </div>
        </div>
      </div>

      {/* Extracted fields preview */}
      {document.extracted_fields && document.extracted_fields.length > 0 && (
        <div className="mb-3">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
              Extracted info
            </span>
          </div>
          <div className="flex flex-wrap gap-1">
            {document.extracted_fields.map((field, i) => (
              <span
                key={i}
                className="text-[10px] text-slate-500 bg-slate-100 px-2 py-0.5 rounded"
              >
                {field.replace(/_/g, ' ')}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Alternatives */}
      {document.alternatives && document.alternatives.length > 0 && (
        <div className="mb-3">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
              Accepted alternatives
            </span>
          </div>
          <p className="text-xs text-slate-600 italic">
            {document.alternatives.join(', ')}
          </p>
        </div>
      )}

      {/* Action buttons */}
      <div className="flex gap-2 pt-3 border-t border-slate-100">
        {(document.status === 'pending' || document.status === 'needs_rescan') && (
          <>
            <button
              onClick={() => onScan(document)}
              className="flex-1 py-2.5 rounded-lg bg-navy-900 text-white text-sm font-medium hover:bg-navy-800 transition flex items-center justify-center gap-2 disabled:opacity-50"
            >
              <Scan size={16} />
              {document.status === 'needs_rescan' ? t(language, 'common.edit') : 'Scan'}
            </button>
            {document.status === 'needs_rescan' && (
              <button
                onClick={() => onRetake(document)}
                className="px-3 py-2.5 rounded-lg border border-slate-300 text-slate-700 text-sm font-medium hover:bg-slate-50 transition disabled:opacity-50"
              >
                <RefreshCw size={16} />
              </button>
            )}
          </>
        )}
        {document.status === 'uploaded' || document.status === 'readable' && (
          <>
            <button
              onClick={() => onScan(document)}
              className="flex-1 py-2.5 rounded-lg border border-slate-300 text-slate-700 text-sm font-medium hover:bg-slate-50 transition disabled:opacity-50"
            >
              <Scan size={16} />
              {t(language, 'common.edit')}
            </button>
          </>
        )}
        {document.status === 'optional' && (
          <button
            onClick={() => onScan(document)}
            className="flex-1 py-2.5 rounded-lg border border-slate-300 text-slate-500 text-sm font-medium hover:bg-slate-50 transition disabled:opacity-50"
          >
            <Scan size={16} />
            {t(language, 'common.edit')}
          </button>
        )}
      </div>

      {/* Help button */}
      <div className="mt-3">
        <button
          onClick={() => onHelp(document)}
          className="w-full py-2 rounded-lg border border-slate-200 text-slate-600 text-sm font-medium hover:bg-slate-50 transition flex items-center justify-center gap-2"
        >
          <HelpCircle size={16} />
          {t(language, 'services.help')}
        </button>
      </div>
    </div>
  )
}
