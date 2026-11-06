import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  AlertTriangle, ArrowLeft, CheckCircle2, Download, FileText, Info,
  Loader2, Printer, RotateCcw, ShieldAlert,
} from 'lucide-react'
import { t, Language } from '../i18n'
import { useSession } from '../hooks/useSession'
import { api } from '../services/api'
import { PdfStatusView } from '../types'

/**
 * PdfExportPage (Phase 6)
 *
 * Application PDF generation and document export.
 * - Generation is gated: the backend only builds the PDF once every populated
 *   field was customer-reviewed (blocked otherwise with a readable reason).
 * - Preview/Download/Print use ownership-checked API calls — there is no
 *   public PDF URL; files live in controlled backend temp storage only.
 * - Every generated PDF carries the educational prototype banner and
 *   disclaimers; nothing is submitted to any bank.
 */
export function PdfExportPage() {
  const { session } = useSession()
  const language: Language = (session?.language as Language) || 'en'
  const navigate = useNavigate()
  const { serviceId } = useParams<{ serviceId: string }>()

  const [status, setStatus] = useState<PdfStatusView | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pdfLang, setPdfLang] = useState<Language>(language)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)

  const frameRef = useRef<HTMLIFrameElement | null>(null)
  const objectUrlRef = useRef<string | null>(null)

  useEffect(() => {
    if (!session) navigate('/')
  }, [session, navigate])

  const trackUrl = (blob: Blob): string => {
    if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current)
    const url = URL.createObjectURL(blob)
    objectUrlRef.current = url
    return url
  }

  useEffect(() => () => {
    if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current)
  }, [])

  const errMessage = (e: any): string => {
    const d = e?.detail || ''
    if (e?.status === 403) return t(language, 'pdf.errors.unauthorized')
    if (e?.status === 404) return t(language, 'pdf.errors.notFound')
    if (e?.status === 409 || /blocked|confirm|review/i.test(d)) {
      return t(language, 'pdf.errors.blocked')
    }
    return d || t(language, 'pdf.errors.generic')
  }

  const loadStatus = useCallback(async (applicationId: string, sessionId: string) => {
    try {
      const s = await api.getPdfStatus(applicationId, sessionId)
      setStatus(s)
      return s
    } catch (e: any) {
      setError(errMessage(e))
      return null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [language])

  // Load (or create) the application, then read PDF status
  useEffect(() => {
    if (!session || !serviceId) return
    let cancelled = false
    ;(async () => {
      try {
        const view = await api.initApplication(session.sessionId, serviceId)
        if (!cancelled) await loadStatus(view.application_id, session.sessionId)
      } catch (e: any) {
        if (!cancelled) {
          setError(e?.status === 403 ? t(language, 'pdf.errors.unauthorized') : t(language, 'pdf.errors.generic'))
        }
      }
    })()
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session?.sessionId, serviceId])

  const generate = async () => {
    if (!status || !session) return
    setBusy('generate')
    setError(null)
    try {
      await api.generatePdf(status.application_id, session.sessionId, pdfLang)
      const fresh = await loadStatus(status.application_id, session.sessionId)
      if (fresh?.pdf_exists) {
        const blob = await api.getPdfBlob(status.application_id, session.sessionId)
        setPreviewUrl(trackUrl(blob))
      }
    } catch (e: any) {
      setError(errMessage(e))
    } finally {
      setBusy(null)
    }
  }

  const preview = async () => {
    if (!status || !session) return
    setBusy('preview')
    setError(null)
    try {
      const blob = await api.getPdfBlob(status.application_id, session.sessionId)
      setPreviewUrl(trackUrl(blob))
    } catch (e: any) {
      setError(errMessage(e))
    } finally {
      setBusy(null)
    }
  }

  const download = async () => {
    if (!status || !session) return
    setBusy('download')
    setError(null)
    try {
      const blob = await api.getPdfBlob(status.application_id, session.sessionId)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = status.pdf?.file_name || `${status.application_id}.pdf`
      document.body.appendChild(a)
      a.click()
      a.remove()
      setTimeout(() => URL.revokeObjectURL(url), 5000)
    } catch (e: any) {
      setError(e?.status ? errMessage(e) : t(language, 'pdf.errors.downloadFailed'))
    } finally {
      setBusy(null)
    }
  }

  const print = async () => {
    if (!status || !session) return
    // Primary: the (hidden or visible) preview iframe already holds the PDF.
    if (previewUrl && frameRef.current?.contentWindow) {
      try {
        frameRef.current.contentWindow.focus()
        frameRef.current.contentWindow.print()
        return
      } catch { /* fall through to window.open */ }
    }
    setBusy('print')
    try {
      const blob = await api.getPdfBlob(status.application_id, session.sessionId)
      const url = trackUrl(blob)
      const win = window.open(url, '_blank')
      if (!win) {
        setError(t(language, 'pdf.errors.printFailed'))
        return
      }
      win.onload = () => { try { win.print() } catch { /* viewer handles it */ } }
    } catch (e: any) {
      setError(e?.status ? errMessage(e) : t(language, 'pdf.errors.printFailed'))
    } finally {
      setBusy(null)
    }
  }

  const removePdf = async () => {
    if (!status || !session) return
    setBusy('delete')
    setError(null)
    try {
      await api.deletePdf(status.application_id, session.sessionId)
      if (objectUrlRef.current) {
        URL.revokeObjectURL(objectUrlRef.current)
        objectUrlRef.current = null
      }
      setPreviewUrl(null)
      await loadStatus(status.application_id, session.sessionId)
    } catch (e: any) {
      setError(errMessage(e))
    } finally {
      setBusy(null)
    }
  }

  if (!session) return null

  const completion = status?.completion
  const pdfReady = completion?.pdf_ready === true
  const blockedReason = completion?.pdf_blocked_reason
  const blockedText = !blockedReason
    ? null
    : blockedReason === 'review_required'
      ? t(language, 'pdf.completion.reviewRequired')
      : blockedReason === 'unconfirmed_fields'
        ? t(language, 'pdf.completion.unconfirmedFields')
        : blockedReason === 'no_confirmation'
          ? t(language, 'pdf.completion.noConfirmation')
          : t(language, 'pdf.completion.unknown')
  const pdfExists = status?.pdf_exists === true
  const hasApplication = status !== null

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="max-w-3xl mx-auto p-4 md:p-8">
        <button
          onClick={() => serviceId && navigate(`/application/form/${serviceId}`)}
          className="text-sm text-slate-600 hover:text-navy-900 transition flex items-center gap-1 mb-4"
        >
          <ArrowLeft size={16} />
          {t(language, 'pdf.actions.backToForm')}
        </button>

        <div className="rounded-2xl bg-navy-900 text-white p-5 mb-4">
          <h1 className="text-xl font-bold">{t(language, 'pdf.title')}</h1>
          <p className="text-xs text-slate-300 mt-2">{t(language, 'pdf.subtitle')}</p>
        </div>

        <div className="rounded-xl border border-amber-300 bg-amber-50 p-3 mb-4 text-amber-900 text-xs">
          <div className="font-semibold flex items-center gap-1.5">
            <ShieldAlert size={15} />
            {t(language, 'pdf.prototypeBanner')}
          </div>
          <p className="mt-1 leading-relaxed">{t(language, 'pdf.prototypeNote')}</p>
        </div>

        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-3 mb-4 text-red-800 text-sm" role="alert" data-testid="pdf-error">
            {error}
          </div>
        )}

        {!hasApplication && !error && (
          <div className="text-center py-20">
            <Loader2 size={40} className="mx-auto animate-spin text-navy-900" />
          </div>
        )}

        {status && (
          <>
            {/* Application / PDF meta card */}
            <div className="rounded-2xl border border-slate-200 bg-white p-4 mb-4" data-testid="pdf-meta">
              <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                <div>
                  <div className="text-[11px] text-slate-500">{t(language, 'pdf.meta.reference')}</div>
                  <div className="font-semibold text-navy-900">{status.application_id}</div>
                </div>
                <div>
                  <div className="text-[11px] text-slate-500">{t(language, 'pdf.meta.formNumber')}</div>
                  <div className="font-semibold text-navy-900">{status.form_number}</div>
                </div>
                <div className="col-span-2">
                  <div className="text-[11px] text-slate-500">{t(language, 'pdf.meta.service')}</div>
                  <div className="font-semibold text-navy-900">{status.service_name}</div>
                </div>
                <div>
                  <div className="text-[11px] text-slate-500">{t(language, 'pdf.meta.pdfStatus')}</div>
                  {pdfExists ? (
                    <span className="inline-flex items-center gap-1 text-emerald-700 font-semibold" data-testid="pdf-status-ready">
                      <CheckCircle2 size={14} /> {t(language, 'pdf.status.ready')}
                    </span>
                  ) : pdfReady ? (
                    <span className="text-slate-700" data-testid="pdf-status-empty">{t(language, 'pdf.status.notGenerated')}</span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-amber-700 font-semibold" data-testid="pdf-status-blocked">
                      <AlertTriangle size={14} /> {t(language, 'pdf.status.blocked')}
                    </span>
                  )}
                </div>
              </div>
              {status.pdf && (
                <div className="mt-3 pt-3 border-t border-slate-100 grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs text-slate-600">
                  <div>
                    <span className="text-slate-400">{t(language, 'pdf.fileInfo.fileName')}: </span>
                    {status.pdf.file_name}
                  </div>
                  <div>
                    <span className="text-slate-400">{t(language, 'pdf.fileInfo.pageCount')}: </span>
                    {status.pdf.page_count ?? '—'}
                  </div>
                  <div>
                    <span className="text-slate-400">{t(language, 'pdf.fileInfo.fileSize')}: </span>
                    {(status.pdf.file_size / 1024).toFixed(0)} KB
                  </div>
                  <div className="flex items-center justify-between gap-2">
                    <span>
                      <span className="text-slate-400">{t(language, 'pdf.fileInfo.generatedAt')}: </span>
                      {status.pdf.generated_at}
                    </span>
                    <button
                      onClick={removePdf}
                      disabled={busy !== null}
                      data-testid="pdf-delete"
                      className="text-[11px] text-slate-500 hover:text-red-700 transition disabled:opacity-50 whitespace-nowrap"
                    >
                      {t(language, 'pdf.actions.delete')}
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Readiness / gate info */}
            <div
              className={`rounded-xl border p-4 mb-4 text-sm ${
                pdfReady ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : 'border-amber-200 bg-amber-50 text-amber-800'
              }`}
              data-testid="pdf-gate"
            >
              {pdfReady ? (
                <>
                  <div className="font-semibold flex items-center gap-2">
                    <CheckCircle2 size={16} /> {t(language, 'pdf.completion.readyTitle')}
                  </div>
                  <p className="mt-1 text-xs">{t(language, 'pdf.completion.readyBody')}</p>
                </>
              ) : (
                <>
                  <div className="font-semibold flex items-center gap-2">
                    <AlertTriangle size={16} /> {t(language, 'pdf.completion.blockedTitle')}
                  </div>
                  <p className="mt-1 text-xs">{blockedText}</p>
                </>
              )}
              {completion && completion.counts && completion.counts.MISSING > 0 && pdfReady && (
                <p className="mt-2 text-xs flex items-start gap-1.5 text-amber-800">
                  <Info size={14} className="flex-shrink-0 mt-0.5" />
                  {t(language, 'pdf.completion.missingFields', { count: String(completion.counts.MISSING) })}
                </p>
              )}
            </div>

            {/* PDF language choice */}
            <div className="rounded-2xl border border-slate-200 bg-white p-4 mb-4">
              <label className="text-[11px] text-slate-500 block mb-2">{t(language, 'pdf.pdfLanguageLabel')}</label>
              <div className="flex gap-2">
                {(['en', 'te', 'hi'] as Language[]).map((l) => (
                  <button
                    key={l}
                    onClick={() => setPdfLang(l)}
                    disabled={busy !== null}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition disabled:opacity-50 ${
                      pdfLang === l
                        ? 'bg-navy-900 text-white border-navy-900'
                        : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-50'
                    }`}
                  >
                    {t(language, `languages.${l}`)}
                  </button>
                ))}
              </div>
            </div>

            {/* Actions */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
              <button
                onClick={generate}
                disabled={busy !== null || !pdfReady}
                data-testid="pdf-generate"
                className="py-3 rounded-xl bg-gold-500 text-navy-900 text-sm font-semibold hover:bg-gold-600 transition disabled:opacity-50 flex items-center justify-center gap-2"
                title={pdfReady ? undefined : t(language, 'pdf.errors.blocked')}
              >
                {busy === 'generate'
                  ? <><Loader2 size={16} className="animate-spin" /> {t(language, 'pdf.actions.generating')}</>
                  : <><FileText size={16} /> {pdfExists ? t(language, 'pdf.actions.regenerate') : t(language, 'pdf.actions.generate')}</>}
              </button>
              <button
                onClick={preview}
                disabled={busy !== null || !pdfExists}
                data-testid="pdf-preview"
                className="py-3 rounded-xl bg-navy-900 text-white text-sm font-medium hover:bg-navy-800 transition disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {busy === 'preview' ? <Loader2 size={16} className="animate-spin" /> : <RotateCcw size={16} />}
                {t(language, 'pdf.actions.preview')}
              </button>
              <button
                onClick={download}
                disabled={busy !== null || !pdfExists}
                data-testid="pdf-download"
                className="py-3 rounded-xl bg-white border border-slate-300 text-slate-700 text-sm font-medium hover:bg-slate-50 transition disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {busy === 'download' ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
                {t(language, 'pdf.actions.download')}
              </button>
              <button
                onClick={print}
                disabled={busy !== null || !pdfExists}
                data-testid="pdf-print"
                className="py-3 rounded-xl bg-white border border-slate-300 text-slate-700 text-sm font-medium hover:bg-slate-50 transition disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {busy === 'print' ? <Loader2 size={16} className="animate-spin" /> : <Printer size={16} />}
                {t(language, 'pdf.actions.print')}
              </button>
            </div>

            {/* Preview */}
            {previewUrl && (
              <div className="rounded-2xl border border-slate-200 bg-white overflow-hidden">
                <iframe
                  ref={frameRef}
                  src={previewUrl}
                  title="Application PDF preview"
                  data-testid="pdf-iframe"
                  className="w-full h-[70vh]"
                />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
