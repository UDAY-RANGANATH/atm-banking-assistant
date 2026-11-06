import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  ArrowLeft, BadgeCheck, CheckCircle2, Eraser, FileDown, FileSearch, Loader2,
  Pencil, RefreshCw, Save, ShieldAlert, AlertTriangle, Info, X,
} from 'lucide-react'
import { t, Language } from '../i18n'
import { useSession } from '../hooks/useSession'
import { api } from '../services/api'
import {
  ApplicationFormView, CompletionStatus, FieldConflictCandidate,
  FieldStatus, FormFieldView,
} from '../types'

/**
 * ApplicationFormPage (Phase 5)
 *
 * Intelligent Application Form Autofill.
 * - The form fields come from reusable per-service form configurations.
 * - "Fill from My Documents" runs the OCR->form autofill engine over the
 *   customer's CONFIRMED scans; synonymous / conflicting values are reported,
 *   never auto-picked, and missing values are never invented.
 * - Every field shows a status badge (AUTO_FILLED / LOW_CONFIDENCE /
 *   CONFLICT / MISSING / CUSTOMER_EDITED / CUSTOMER_CONFIRMED).
 * - The customer can edit, accept, clear every field, and review the source
 *   document behind a value.
 * - Nothing is silently submitted: Continue requires an explicit final review
 *   and confirmation, and in this educational prototype does not send
 *   anything to a bank.
 */

const STATUS_BADGE: Record<FieldStatus, { cls: string; icon: string }> = {
  AUTO_FILLED: { cls: 'bg-blue-100 text-blue-800 border-blue-200', icon: '✦' },
  LOW_CONFIDENCE: { cls: 'bg-amber-100 text-amber-900 border-amber-300', icon: '⚠' },
  CONFLICT: { cls: 'bg-red-100 text-red-800 border-red-300', icon: '⚡' },
  MISSING: { cls: 'bg-slate-100 text-slate-600 border-slate-200', icon: '—' },
  CUSTOMER_EDITED: { cls: 'bg-violet-100 text-violet-800 border-violet-200', icon: '✎' },
  CUSTOMER_CONFIRMED: { cls: 'bg-emerald-100 text-emerald-800 border-emerald-300', icon: '✓' },
}

function FieldStatusBadge({ status, language }: { status: FieldStatus; language: Language }) {
  const badge = STATUS_BADGE[status] ?? STATUS_BADGE.MISSING
  return (
    <span
      data-testid={`field-status-${status}`}
      className={`inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full border ${badge.cls}`}
    >
      <span aria-hidden>{badge.icon}</span>
      {t(language, `form.status.${status}`)}
    </span>
  )
}

export function ApplicationFormPage() {
  const { session } = useSession()
  const language: Language = (session?.language as Language) || 'en'
  const navigate = useNavigate()
  const { serviceId } = useParams<{ serviceId: string }>()

  const [form, setForm] = useState<ApplicationFormView | null>(null)
  const [completion, setCompletion] = useState<CompletionStatus | null>(null)
  const [stage, setStage] = useState<'loading' | 'ready' | 'finalReview' | 'done'>('loading')
  const [busy, setBusy] = useState<string | null>(null)
  const [toast, setToast] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [editing, setEditing] = useState<Record<string, string>>({})
  const [reviewSource, setReviewSource] = useState<FormFieldView | null>(null)
  const [reviewImageUrl, setReviewImageUrl] = useState<string | null>(null)
  const [finalConfirmChecked, setFinalConfirmChecked] = useState(false)

  useEffect(() => {
    if (!session) navigate('/')
  }, [session, navigate])

  const refreshCompletion = useCallback(async (applicationId: string) => {
    if (!session) return
    try {
      const c = await api.getCompletionStatus(applicationId, session.sessionId)
      setCompletion(c)
    } catch { /* non-critical */ }
  }, [session])

  // Load (or create) the application + run autofill once on entry
  useEffect(() => {
    if (!session || !serviceId) return
    let cancelled = false
    ;(async () => {
      try {
        let view = await api.initApplication(session.sessionId, serviceId)
        view = await api.autofillApplication(view.application_id, session.sessionId)
        if (!cancelled) {
          setForm(view)
          setStage('ready')
          await refreshCompletion(view.application_id)
        }
      } catch (e: any) {
        if (!cancelled) {
          setError(e?.detail || t(language, 'form.errors.generic'))
          setStage('ready')
        }
      }
    })()
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session?.sessionId, serviceId])

  const applyFieldResult = (fieldId: string, record: { value: string | null; status: FieldStatus; confidence: number | null; source: FormFieldView['source'] }) => {
    setForm((prev) => prev ? {
      ...prev,
      fields: prev.fields.map((f) => f.field_id === fieldId
        ? { ...f, value: record.value, status: record.status, confidence: record.confidence, source: record.source, conflicts: null }
        : f),
    } : prev)
  }

  const patchField = async (
    field: FormFieldView,
    action: 'edit' | 'clear' | 'confirm' | 'accept',
    value?: string,
  ) => {
    if (!form || !session) return
    setBusy(field.field_id)
    setError(null)
    try {
      const res = await api.patchApplicationField(form.application_id, session.sessionId, field.field_id, action, value)
      applyFieldResult(field.field_id, res.record)
      setEditing((p) => {
        const next = { ...p }
        delete next[field.field_id]
        return next
      })
      await refreshCompletion(form.application_id)
    } catch (e: any) {
      // Backend detail is an i18n key (e.g. pattern.mobile_number) - message
      // is shown, but the personal value itself is never echoed in logs.
      if (typeof e?.detail === 'string' && e.detail.startsWith('pattern.')) {
        setError(t(language, 'form.errors.invalidValue'))
      } else {
        setError(e?.detail || t(language, 'form.errors.generic'))
      }
    } finally {
      setBusy(null)
    }
  }

  const runAutofill = async () => {
    if (!form || !session) return
    setBusy('autofill')
    setError(null)
    try {
      const view = await api.autofillApplication(form.application_id, session.sessionId)
      setForm(view)
      setToast(t(language, 'form.autofillNote'))
      await refreshCompletion(view.application_id)
    } catch (e: any) {
      setError(e?.detail || t(language, 'form.errors.generic'))
    } finally {
      setBusy(null)
    }
  }

  /**
   * Bulk confirmation of every populated field (Phase 6 hook-up).
   * The PDF gate requires each filled field to be customer-reviewed;
   * this confirms AUTO_FILLED values the customer accepts in one action.
   * Unfilled (MISSING) fields are never confirmed.
   */
  const confirmAllFilled = async () => {
    if (!form || !session) return
    const ids = form.fields
      .filter((f) => f.value && f.status !== 'CUSTOMER_CONFIRMED' && f.status !== 'CUSTOMER_EDITED')
      .map((f) => f.field_id)
    if (!ids.length) {
      setToast(t(language, 'form.warnings.allReviewed'))
      return
    }
    setBusy('confirmAll')
    setError(null)
    try {
      await api.confirmApplicationFields(form.application_id, session.sessionId, ids)
      const view = await api.getApplicationForm(form.application_id, session.sessionId)
      setForm(view)
      setToast(t(language, 'form.actions.confirmedAll'))
      await refreshCompletion(form.application_id)
    } catch (e: any) {
      setError(e?.detail || t(language, 'form.errors.generic'))
    } finally {
      setBusy(null)
    }
  }

  const saveProgress = async () => {
    if (!form || !session) return
    setBusy('save')
    try {
      await api.saveApplication(form.application_id, session.sessionId)
      setToast(t(language, 'form.warnings.saved'))
    } catch (e: any) {
      setError(e?.detail || t(language, 'form.errors.generic'))
    } finally {
      setBusy(null)
    }
  }

  const openSource = async (field: FormFieldView) => {
    setReviewSource(field)
    const scanId = field.source?.scan_id
    if (scanId) {
      try {
        setReviewImageUrl(await api.scanImageUrl(scanId))
      } catch {
        setReviewImageUrl(null)
      }
    } else {
      setReviewImageUrl(null)
    }
  }

  const applyCandidate = async (field: FormFieldView, cand: FieldConflictCandidate) => {
    await patchField(field, 'edit', cand.value)
  }

  const warnings = useMemo(() => completion?.warnings ?? [], [completion])
  const byKind = (kind: string) => warnings.find((w) => w.kind === kind)

  const needsReview = !completion?.ready_to_continue
  const missingCount = completion?.counts?.MISSING ?? 0

  if (!session) return null

  // --------------------------- render ---------------------------
  const label = (f: FormFieldView) => f.label[language] || f.label.en || f.field_id

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="max-w-3xl mx-auto p-4 md:p-8">
        {/* Header */}
        <button
          onClick={() => serviceId && navigate(`/documents/${serviceId}`)}
          className="text-sm text-slate-600 hover:text-navy-900 transition flex items-center gap-1 mb-4"
        >
          <ArrowLeft size={16} />
          {t(language, 'form.actions.backToChecklist')}
        </button>

        <div className="rounded-2xl bg-navy-900 text-white p-5 mb-4">
          <h1 className="text-xl font-bold">{t(language, 'form.title')}</h1>
          {form && (
            <div className="mt-2 flex flex-wrap gap-2 text-xs">
              <span className="bg-gold-500 text-navy-900 font-semibold px-2 py-1 rounded">
                {t(language, 'services.formNumber')}: {form.form_number}
              </span>
              <span className="bg-white/10 px-2 py-1 rounded">{form.service_name}</span>
              <span className="bg-white/10 px-2 py-1 rounded">
                {t(language, 'form.referenceNumber')}: {form.application_id}
              </span>
            </div>
          )}
          <p className="text-xs text-slate-300 mt-2">{t(language, 'form.subtitle')}</p>
        </div>

        {/* Prototype notice */}
        <div className="rounded-xl border border-blue-200 bg-blue-50 p-3 mb-4 text-blue-900 text-xs flex gap-2">
          <Info size={16} className="flex-shrink-0 mt-0.5" />
          <span>{t(language, 'form.prototypeNotice')}</span>
        </div>

        {stage === 'loading' && (
          <div className="text-center py-20">
            <Loader2 size={40} className="mx-auto animate-spin text-navy-900" />
            <p className="mt-4 text-slate-600 text-sm">{t(language, 'form.autofillRunning')}</p>
          </div>
        )}

        {stage === 'ready' && !form && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-amber-800 text-sm">
            {error || t(language, 'form.noDocumentsYet')}
          </div>
        )}

        {form && (
          <>
            {/* Warning banners */}
            {needsReview && (
              <div className="rounded-xl border border-red-200 bg-red-50 p-4 mb-4 text-red-800 text-sm" data-testid="needs-review-banner">
                <div className="font-semibold flex items-center gap-2">
                  <ShieldAlert size={16} />
                  {t(language, 'form.warnings.title')}
                </div>
                <ul className="mt-1 space-y-0.5 text-xs">
                  {byKind('conflict') && (
                    <li>{t(language, 'form.warnings.conflict', { count: String(byKind('conflict')!.fields.length) })}</li>
                  )}
                  {byKind('low_confidence') && (
                    <li>{t(language, 'form.warnings.lowConfidence', { count: String(byKind('low_confidence')!.fields.length) })}</li>
                  )}
                </ul>
              </div>
            )}
            {byKind('missing') && (
              <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 mb-4 text-amber-800 text-sm flex gap-2">
                <AlertTriangle size={16} className="flex-shrink-0 mt-0.5" />
                <span>
                  {t(language, 'form.warnings.missing', { count: String(missingCount) })} — {t(language, 'form.noDocumentsYet')}
                </span>
              </div>
            )}
            {!needsReview && (
              <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 mb-4 text-emerald-800 text-sm flex items-center gap-2">
                <CheckCircle2 size={16} />
                {t(language, 'form.warnings.allReviewed')}
              </div>
            )}

            {error && (
              <div className="rounded-xl border border-red-200 bg-red-50 p-3 mb-4 text-red-800 text-sm" role="alert">
                {error}
              </div>
            )}
            {toast && (
              <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 mb-4 text-emerald-800 text-sm flex items-center justify-between">
                <span>{toast}</span>
                <button onClick={() => setToast(null)} aria-label="close"><X size={14} /></button>
              </div>
            )}

            {/* Toolbar */}
            <div className="grid grid-cols-3 gap-3 mb-6">
              <button
                onClick={runAutofill}
                disabled={busy !== null || !form}
                className="py-3 rounded-xl bg-navy-900 text-white text-sm font-medium hover:bg-navy-800 transition disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {busy === 'autofill' ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}
                {t(language, 'form.actions.autofillAgain')}
              </button>
              <button
                onClick={saveProgress}
                disabled={busy !== null || !form}
                className="py-3 rounded-xl bg-white border border-slate-300 text-slate-700 text-sm font-medium hover:bg-slate-50 transition disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {busy === 'save' ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
                {t(language, 'form.actions.saveProgress')}
              </button>
              <button
                onClick={() => { setFinalConfirmChecked(false); setStage('finalReview') }}
                disabled={busy !== null}
                className="py-3 rounded-xl bg-gold-500 text-navy-900 text-sm font-semibold hover:bg-gold-600 transition disabled:opacity-50"
              >
                {t(language, 'form.actions.continue')}
              </button>
            </div>

            {/* Bulk confirmation (Phase 6): needed before a PDF can be generated */}
            <button
              onClick={confirmAllFilled}
              disabled={busy !== null || !form?.fields.some(
                (f) => f.value && f.status !== 'CUSTOMER_CONFIRMED' && f.status !== 'CUSTOMER_EDITED',
              )}
              data-testid="confirm-all-fields"
              className="w-full mb-6 py-3 rounded-xl bg-emerald-600 text-white text-sm font-semibold hover:bg-emerald-700 transition disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {busy === 'confirmAll' ? <Loader2 size={16} className="animate-spin" /> : <BadgeCheck size={16} />}
              {t(language, 'form.actions.confirmAll')}
            </button>

            {/* Fields */}
            <div className="space-y-3">
              {form.fields.map((f) => {
                const isEditing = editing[f.field_id] !== undefined
                const editValue = isEditing ? editing[f.field_id] : (f.value ?? '')
                return (
                  <div
                    key={f.field_id}
                    data-testid={`form-field-${f.field_id}`}
                    className={`rounded-2xl border p-4 bg-white ${
                      f.status === 'CONFLICT' ? 'border-red-300' :
                      f.status === 'LOW_CONFIDENCE' ? 'border-amber-300' :
                      f.status === 'CUSTOMER_CONFIRMED' ? 'border-emerald-200' : 'border-slate-200'}`}
                  >
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <label className="text-sm font-semibold text-navy-900" htmlFor={`in-${f.field_id}`}>
                        {label(f)}
                      </label>
                      <FieldStatusBadge status={f.status} language={language} />
                    </div>

                    {/* input */}
                    {f.type === 'select' && f.options ? (
                      <select
                        id={`in-${f.field_id}`}
                        value={isEditing ? editValue : (f.value ?? '')}
                        onChange={(e) => {
                          setEditing((p) => ({ ...p, [f.field_id]: e.target.value }))
                          patchField(f, 'edit', e.target.value || undefined)
                        }}
                        className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-navy-900/30"
                      >
                        <option value="">--</option>
                        {f.options.map((o) => <option key={o} value={o}>{o}</option>)}
                      </select>
                    ) : (
                      <input
                        id={`in-${f.field_id}`}
                        type="text"
                        value={isEditing ? editValue : (f.value ?? '')}
                        placeholder={f.status === 'MISSING' ? t(language, 'form.source.manualNote') : ''}
                        onChange={(e) => setEditing((p) => ({ ...p, [f.field_id]: e.target.value }))}
                        onBlur={() => {
                          if (!isEditing) return
                          if (editValue !== (f.value ?? '')) {
                            if (editValue.trim()) {
                              patchField(f, 'edit', editValue)
                            } else {
                              // blanked input without explicit Clear: restore committed value
                              setEditing((p) => { const n = { ...p }; delete n[f.field_id]; return n })
                            }
                          } else {
                            setEditing((p) => { const n = { ...p }; delete n[f.field_id]; return n })
                          }
                        }}
                        onKeyDown={(e) => { if (e.key === 'Enter') (e.target as HTMLInputElement).blur() }}
                        className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-navy-900/30"
                      />
                    )}

                    {/* conflict candidates */}
                    {f.status === 'CONFLICT' && f.conflicts && (
                      <div data-testid="conflict-candidates" className="mt-3 rounded-xl bg-red-50 border border-red-200 p-3">
                        <div className="text-xs font-semibold text-red-800 mb-2">
                          {t(language, 'form.source.conflictsTitle')}
                        </div>
                        <p className="text-[11px] text-red-700 mb-2">{t(language, 'form.source.conflictsBody')}</p>
                        <div className="space-y-2">
                          {f.conflicts.map((c, i) => (
                            <div key={i} className="flex items-center justify-between gap-2 bg-white rounded-lg border border-red-100 px-3 py-2">
                              <div className="min-w-0">
                                <div className="text-sm text-slate-800 truncate" data-testid="conflict-candidate-value">{c.value}</div>
                                <div className="text-[10px] text-slate-500">
                                  {t(language, 'form.source.fromDocument')} {c.doc_field_label || c.doc_type}
                                  {c.confidence != null && <> · {t(language, 'form.source.confidence')} {Math.round(c.confidence)}%</>}
                                </div>
                              </div>
                              <button
                                onClick={() => applyCandidate(f, c)}
                                disabled={busy !== null}
                                className="text-xs bg-red-600 text-white px-3 py-1.5 rounded-lg hover:bg-red-700 transition whitespace-nowrap"
                              >
                                {t(language, 'form.source.useThisValue')}
                              </button>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* source meta */}
                    {(f.source || f.confidence != null) && (
                      <div className="mt-2 text-[11px] text-slate-500 flex flex-wrap items-center gap-x-3 gap-y-1">
                        {f.source && (
                          <span>
                            {t(language, 'form.source.fromDocument')}: {f.source.doc_field_label || f.source.doc_type}
                          </span>
                        )}
                        {f.confidence != null && (
                          <span>{t(language, 'form.source.confidence')}: {Math.round(f.confidence)}%</span>
                        )}
                        {f.source?.corroborated_by && f.source.corroborated_by.length > 0 && (
                          <span>{t(language, 'form.source.corroborated')} ({f.source.corroborated_by.length})</span>
                        )}
                      </div>
                    )}
                    {f.sensitive && (
                      <div className="mt-1 text-[10px] text-slate-400">{t(language, 'form.source.maskedNote')}</div>
                    )}

                    {/* field actions */}
                    <div className="mt-3 flex flex-wrap gap-2">
                      {f.value && f.status !== 'CUSTOMER_CONFIRMED' && (
                        <button
                          onClick={() => patchField(f, 'confirm')}
                          disabled={busy !== null}
                          data-testid="accept-value"
                          className="text-xs px-3 py-1.5 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 transition flex items-center gap-1 disabled:opacity-50"
                        >
                          <BadgeCheck size={13} />
                          {t(language, 'form.actions.acceptValue')}
                        </button>
                      )}
                      <button
                        onClick={() => {
                          const cur = f.value ?? ''
                          setEditing((p) => ({ ...p, [f.field_id]: cur }))
                          document.getElementById(`in-${f.field_id}`)?.focus()
                        }}
                        disabled={busy !== null}
                        data-testid="edit-field"
                        className="text-xs px-3 py-1.5 rounded-lg bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 transition flex items-center gap-1 disabled:opacity-50"
                      >
                        <Pencil size={13} />
                        {t(language, 'form.actions.editField')}
                      </button>
                      {(f.value || f.status !== 'MISSING') && (
                        <button
                          onClick={() => patchField(f, 'clear')}
                          disabled={busy !== null}
                          data-testid="clear-value"
                          className="text-xs px-3 py-1.5 rounded-lg bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 transition flex items-center gap-1 disabled:opacity-50"
                        >
                          <Eraser size={13} />
                          {t(language, 'form.actions.clearValue')}
                        </button>
                      )}
                      {(f.source?.scan_id || f.conflicts && f.conflicts.some((c) => c.scan_id)) && (
                        <button
                          onClick={() => openSource(f)}
                          data-testid="review-source"
                          className="text-xs px-3 py-1.5 rounded-lg bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 transition flex items-center gap-1"
                        >
                          <FileSearch size={13} />
                          {t(language, 'form.actions.reviewSource')}
                        </button>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>

            {/* Footer actions */}
            <div className="grid grid-cols-2 gap-3 mt-6">
              <button
                onClick={saveProgress}
                disabled={busy !== null}
                className="py-3 rounded-xl bg-white border border-slate-300 text-slate-700 text-sm font-medium hover:bg-slate-50 transition disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {busy === 'save' ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
                {t(language, 'form.actions.saveProgress')}
              </button>
              <button
                onClick={() => { setFinalConfirmChecked(false); setStage('finalReview') }}
                disabled={busy !== null}
                className="py-3 rounded-xl bg-gold-500 text-navy-900 text-sm font-semibold hover:bg-gold-600 transition disabled:opacity-50"
              >
                {t(language, 'form.actions.continue')}
              </button>
            </div>
          </>
        )}
      </div>

      {/* ---------------- Review Source Document modal ---------------- */}
      {reviewSource && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm" onClick={() => setReviewSource(null)} />
          <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 max-h-[90vh] flex flex-col overflow-hidden">
            <div className="bg-navy-900 text-white px-5 py-4 flex items-center justify-between">
              <div>
                <h3 className="font-bold">{t(language, 'form.actions.reviewSource')}</h3>
                <p className="text-xs text-slate-300">{label(reviewSource)}</p>
              </div>
              <button onClick={() => setReviewSource(null)} className="text-slate-400 hover:text-white"><X size={20} /></button>
            </div>
            <div className="overflow-y-auto p-4 space-y-3">
              {reviewImageUrl ? (
                <img src={reviewImageUrl} alt="source scan" className="w-full rounded-xl border border-slate-200" />
              ) : (
                <div className="rounded-xl bg-slate-100 p-6 text-center text-slate-500 text-sm">
                  {t(language, 'form.noDocumentsYet')}
                </div>
              )}
              {reviewSource.source && (
                <div className="text-xs text-slate-600 space-y-1">
                  <div>{t(language, 'form.source.fromDocument')}: {reviewSource.source.doc_field_label || reviewSource.source.doc_type}</div>
                  {reviewSource.confidence != null && (
                    <div>{t(language, 'form.source.confidence')}: {Math.round(reviewSource.confidence)}%</div>
                  )}
                </div>
              )}
            </div>
            <div className="bg-slate-50 border-t border-slate-200 p-3">
              <button
                onClick={() => setReviewSource(null)}
                className="w-full py-2.5 rounded-xl bg-navy-900 text-white font-medium hover:bg-navy-800 transition"
              >
                {t(language, 'common.close')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ---------------- Final review before Continue ---------------- */}
      {stage === 'finalReview' && form && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm" onClick={() => setStage('ready')} />
          <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 max-h-[90vh] flex flex-col overflow-hidden">
            <div className="bg-navy-900 text-white px-5 py-4 flex items-center justify-between">
              <h3 className="font-bold">{t(language, 'form.continue.reviewTitle')}</h3>
              <button onClick={() => setStage('ready')} className="text-slate-400 hover:text-white"><X size={20} /></button>
            </div>
            <div className="overflow-y-auto p-4">
              <p className="text-xs text-slate-600 mb-3">{t(language, 'form.continue.reviewBody')}</p>
              {needsReview && (
                <div data-testid="blocked-review" className="rounded-xl border border-red-200 bg-red-50 p-3 text-red-800 text-xs mb-3">
                  <div className="font-semibold">{t(language, 'form.continue.blockedTitle')}</div>
                  <p className="mt-1">{t(language, 'form.continue.blockedBody')}</p>
                </div>
              )}
              <div className="space-y-2">
                {form.fields.filter((f) => f.value).map((f) => (
                  <div key={f.field_id} className="flex items-center justify-between gap-2 text-xs border border-slate-200 rounded-lg px-3 py-2">
                    <span className="font-semibold text-navy-900">{label(f)}</span>
                    <span className="text-slate-700 truncate max-w-[55%]">{f.value}</span>
                  </div>
                ))}
              </div>
              <label className="mt-4 flex items-start gap-2 text-sm text-slate-700 cursor-pointer">
                <input
                  type="checkbox"
                  checked={finalConfirmChecked}
                  onChange={(e) => setFinalConfirmChecked(e.target.checked)}
                  data-testid="final-confirm-checkbox"
                  className="mt-0.5"
                />
                <span>{t(language, 'form.continue.confirmLabel')}</span>
              </label>
            </div>
            <div className="bg-slate-50 border-t border-slate-200 p-4 flex gap-3">
              <button
                onClick={() => setStage('ready')}
                className="flex-1 py-3 rounded-xl border border-slate-300 text-slate-700 font-medium hover:bg-slate-100 transition"
              >
                {t(language, 'form.continue.cancel')}
              </button>
              <button
                onClick={async () => {
                  if (!finalConfirmChecked || needsReview || !form || !session) return
                  // PDF gate (Phase 6): the customer just reviewed every value,
                  // so record the confirmation for each populated field.
                  const ids = form.fields.filter((f) => f.value).map((f) => f.field_id)
                  if (ids.length) {
                    await api.confirmApplicationFields(form.application_id, session.sessionId, ids).catch(() => null)
                  }
                  await api.saveApplication(form.application_id, session.sessionId).catch(() => null)
                  const view = await api.getApplicationForm(form.application_id, session.sessionId).catch(() => null)
                  if (view) setForm(view)
                  setStage('done')
                }}
                disabled={!finalConfirmChecked || needsReview}
                data-testid="proceed-continue"
                className="flex-1 py-3 rounded-xl bg-navy-900 text-white font-medium hover:bg-navy-800 transition disabled:opacity-50"
              >
                {t(language, 'form.continue.proceed')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ---------------- Done (prototype: nothing submitted) ---------------- */}
      {stage === 'done' && form && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-slate-900/60" />
          <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 p-6 text-center">
            <CheckCircle2 size={44} className="mx-auto text-emerald-600" />
            <h3 className="font-bold text-navy-900 mt-3">{t(language, 'form.continue.reviewTitle')}</h3>
            <p className="text-sm text-slate-600 mt-2">{t(language, 'form.warnings.saved')}</p>
            <p className="text-xs text-slate-500 mt-2">
              {t(language, 'form.referenceNumber')}: {form.application_id}
            </p>
            <button
              onClick={() => navigate(`/application/pdf/${form.service_id}`)}
              data-testid="continue-to-pdf"
              className="mt-5 w-full py-3 rounded-xl bg-gold-500 text-navy-900 font-semibold hover:bg-gold-600 transition flex items-center justify-center gap-2"
            >
              <FileDown size={16} />
              {t(language, 'form.continue.goPdf')}
            </button>
            <p className="text-[11px] text-slate-400 mt-1.5">{t(language, 'form.continue.goPdfNote')}</p>
            <button
              onClick={() => setStage('ready')}
              className="mt-2 w-full py-2.5 rounded-xl border border-slate-300 text-slate-700 font-medium hover:bg-slate-100 transition"
            >
              {t(language, 'common.close')}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
