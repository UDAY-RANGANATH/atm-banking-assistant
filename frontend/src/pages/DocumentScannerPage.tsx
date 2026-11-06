import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  ArrowLeft, Camera, CameraOff, RefreshCw, Upload, CheckCircle,
  AlertTriangle, ShieldCheck, ScanLine, Eye, XCircle, Loader2, Lock,
} from 'lucide-react'
import { t, Language } from '../i18n'
import { useSession } from '../hooks/useSession'
import { api } from '../services/api'
import {
  ScanProcessResponse,
  ScanField,
  ScanQuality,
  ScanResult,
} from '../types'

type Stage = 'camera' | 'processing' | 'review' | 'confirmed' | 'error'

/**
 * DocumentScannerPage (Phase 4)
 *
 * 1. Live camera preview with framing guides (MediaDevices API).
 * 2. Capture / upload-from-device -> POST /api/scanner/capture|upload.
 * 3. Processing state -> server runs preprocessing + real OCR + extraction.
 * 4. Review screen: fields shown with real OCR confidences; the customer can
 *    edit any value; confirm posts corrections; rescan restarts the loop.
 *
 * Teaching focus: OCR output is never presented as document authentication,
 * extracted values are shown exactly as printed (no translation), missing
 * fields are shown as "not read" - never invented.
 */
export function DocumentScannerPage() {
  const { session } = useSession()
  const language: Language = (session?.language as Language) || 'en'
  const navigate = useNavigate()
  const { serviceId, documentId } = useParams<{ serviceId: string; documentId: string }>()

  const [stage, setStage] = useState<Stage>('camera')
  const [cameraError, setCameraError] = useState<string | null>(null)
  const [cameraOn, setCameraOn] = useState(false)
  const [pendingFile, setPendingFile] = useState<{ blob: Blob; name: string; source: 'camera' | 'upload' } | null>(null)
  const [scan, setScan] = useState<ScanProcessResponse | null>(null)
  const [editedValues, setEditedValues] = useState<Record<string, string>>({})
  const [editMode, setEditMode] = useState<Record<string, boolean>>({})
  const [, setConfirmed] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [showGuides] = useState<boolean>(true)

  const videoRef = useRef<HTMLVideoElement | null>(null)
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach((tr) => tr.stop())
    streamRef.current = null
    setCameraOn(false)
  }, [])

  useEffect(() => {
    if (!session) {
      navigate('/')
    }
  }, [session, navigate])

  // Tear down the camera stream on unmount
  useEffect(() => () => stopCamera(), [stopCamera])

  const startCamera = async () => {
    setCameraError(null)
    if (!navigator.mediaDevices?.getUserMedia) {
      setCameraError(t(language, 'scanner.cameraError'))
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment', width: { ideal: 1920 }, height: { ideal: 1080 } },
        audio: false,
      })
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
      }
      setCameraOn(true)
    } catch {
      setCameraError(t(language, 'scanner.cameraError'))
    }
  }

  const capture = () => {
    if (!cameraOn || !videoRef.current || !canvasRef.current) return
    const video = videoRef.current
    const canvas = canvasRef.current
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.drawImage(video, 0, 0)
    stopCamera()
    canvas.toBlob(
      (blob) => {
        if (blob) {
          setPendingFile({ blob, name: 'capture.jpg', source: 'camera' })
          setStage('processing')
        }
      },
      'image/jpeg',
      0.92,
    )
  }

  const onFilePicked = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    stopCamera()
    setPendingFile({ blob: file, name: file.name, source: 'upload' })
    setStage('processing')
    e.target.value = ''
  }

  // Submit the pending file to the pipeline
  useEffect(() => {
    if (stage !== 'processing' || !pendingFile) return
    let cancelled = false
    ;(async () => {
      if (!serviceId || !documentId || !session) return
      try {
        const res = await api.submitScan(
          pendingFile.source === 'camera' ? 'capture' : 'upload',
          session.sessionId,
          serviceId,
          documentId,
          pendingFile.blob,
          pendingFile.name,
        )
        if (!cancelled) {
          setScan(res)
          setEditedValues({})
          setEditMode({})
          setConfirmed(false)
          setStage('review')
        }
      } catch (err: any) {
        if (!cancelled) {
          setErrorMsg(err?.message || 'Scan failed')
          setStage('error')
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [stage, pendingFile, serviceId, documentId, session])

  const buildCorrections = (): Record<string, string> | undefined => {
    if (!scan) return undefined
    const corrections: Record<string, string> = {}
    for (const [field, value] of Object.entries(editedValues)) {
      const original: ScanField | undefined = scan.result.fields[field]
      if (original && original.value !== value) corrections[field] = value
    }
    return Object.keys(corrections).length ? corrections : undefined
  }

  const handleConfirm = async () => {
    if (!scan) return
    setStage('processing')
    try {
      await api.confirmScan(scan.scan_id, buildCorrections())
      setConfirmed(true)
      setStage('confirmed')
    } catch (err: any) {
      setErrorMsg(err?.message || 'Confirm failed')
      setStage('error')
    }
  }

  const handleRescan = async () => {
    if (!scan) return
    try {
      await api.rescanScan(scan.scan_id)
    } catch { /* non-fatal - user continues to a fresh capture */ }
    setScan(null)
    setPendingFile(null)
    setEditedValues({})
    setEditMode({})
    setConfirmed(false)
    setStage('camera')
  }

  const backToChecklist = () => {
    navigate(`/documents/${serviceId}`)
  }

  const qualityBanner = useMemo(() => {
    const q: ScanQuality | null = scan?.quality ?? null
    if (!q) return null
    const titles: Record<ScanQuality['status'], string> = {
      GOOD: t(language, 'scanner.quality.good'),
      WARNING: t(language, 'scanner.quality.warning'),
      POOR: t(language, 'scanner.quality.poor'),
    }
    const colors: Record<ScanQuality['status'], string> = {
      GOOD: 'bg-green-50 border-green-200 text-green-800',
      WARNING: 'bg-amber-50 border-amber-200 text-amber-800',
      POOR: 'bg-red-50 border-red-200 text-red-800',
    }
    const translatedIssues = q.issues.map((issue) => t(language, `scanner.quality.${issue}`))
    const issues = q.explanations.length
      ? q.explanations
      : translatedIssues.filter((v, idx) => v !== `scanner.quality.${q.issues[idx]}`)
    return (
      <div className={`rounded-xl border p-4 mb-4 ${colors[q.status]}`}>
        <div className="font-semibold text-sm flex items-center gap-2">
          <ScanLine size={16} />
          {t(language, 'scanner.quality.title')}: {titles[q.status]}
        </div>
        {issues.length > 0 && (
          <ul className="mt-2 space-y-1 text-xs list-disc list-inside">
            {issues.map((ex, i) => <li key={i}>{ex}</li>)}
          </ul>
        )}
      </div>
    )
  }, [scan, language])

  const classificationBanner = useMemo(() => {
    const r: ScanResult | null = scan?.result ?? null
    if (!r) return null
    const match = r.classification.match
    if (match === 'MATCH') {
      return (
        <div className="rounded-xl border border-green-200 bg-green-50 p-4 mb-4 text-green-800">
          <div className="font-semibold text-sm flex items-center gap-2">
            <ShieldCheck size={16} />
            {t(language, 'scanner.classification.matched')}
          </div>
          <p className="text-xs mt-1 opacity-80">{t(language, 'scanner.classification.neverAuthentication')}</p>
        </div>
      )
    }
    if (match === 'MISMATCH') {
      return (
        <div className="rounded-xl border border-red-300 bg-red-50 p-4 mb-4 text-red-800">
          <div className="font-semibold text-sm flex items-center gap-2">
            <XCircle size={16} />
            {t(language, 'scanner.classification.mismatch')}
          </div>
          <p className="text-xs mt-1 opacity-80">{t(language, 'scanner.classification.neverAuthentication')}</p>
        </div>
      )
    }
    return (
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 mb-4 text-amber-800">
        <div className="font-semibold text-sm flex items-center gap-2">
          <AlertTriangle size={16} />
          {t(language, 'scanner.classification.unknown')}
        </div>
        <p className="text-xs mt-1 opacity-80">{t(language, 'scanner.classification.neverAuthentication')}</p>
      </div>
    )
  }, [scan, language])

  const fieldsArray = useMemo(() => {
    if (!scan?.result?.fields) return []
    return Object.entries(scan.result.fields)
  }, [scan])

  const allEmpty = fieldsArray.length === 0 || fieldsArray.every(([key, f]) => !f.value && !editMode[key])

  // ------------------------------------------------------------------ render
  return (
    <div className="min-h-screen bg-slate-100 flex flex-col">
      <canvas ref={canvasRef} className="hidden" />

      {/* Header */}
      <div className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between">
        <button onClick={backToChecklist} className="flex items-center gap-2 text-slate-600 hover:text-navy-900 transition">
          <ArrowLeft size={18} />
          <span>{t(language, 'nav.back')}</span>
        </button>
        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold text-navy-900">{t(language, 'scanner.title')}</span>
          <span className="text-[10px] bg-gold-100 text-gold-700 px-2 py-0.5 rounded">
            {t(language, 'scanner.deviceNote')}
          </span>
        </div>
      </div>

      <div className="flex-1 max-w-3xl w-full mx-auto p-6 overflow-y-auto">
        {/* Privacy / teaching notes - always visible */}
        <div className="mb-4 rounded-xl border border-slate-200 bg-white p-4 text-xs text-slate-600 space-y-1">
          <p className="flex items-start gap-2">
            <Lock size={14} className="mt-0.5 shrink-0 text-slate-400" />
            {t(language, 'scanner.privacyNote')}
          </p>
          <p className="flex items-start gap-2">
            <Eye size={14} className="mt-0.5 shrink-0 text-slate-400" />
            {t(language, 'scanner.ocrReading')}
          </p>
        </div>

        {/* ------------------------------------------------ Stage: camera -- */}
        {stage === 'camera' && (
          <div>
            <div className="relative rounded-2xl overflow-hidden bg-slate-900 aspect-video mb-4">
              <video ref={videoRef} playsInline muted className="absolute inset-0 w-full h-full object-cover" />
              {!cameraOn && (
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 text-slate-300">
                  <CameraOff size={40} />
                  <p className="text-sm px-6 text-center">
                    {t(language, 'scanner.loadingCamera')}
                  </p>
                </div>
              )}
              {cameraOn && showGuides && (
                <div className="absolute inset-0 pointer-events-none">
                  <div className="absolute inset-6 border-2 border-dashed border-white/60 rounded-xl" />
                  <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 text-white/70 text-xs bg-black/40 px-3 py-1 rounded">
                    {language === 'te' ? 'పత్రాన్ని ఫ్రేమ్‌లో ఉంచండి' : language === 'hi' ? 'दस्तावेज़ फ्रेम में रखें' : 'Fit the document inside the frame'}
                  </div>
                </div>
              )}
            </div>

            {cameraError && (
              <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-amber-800 text-sm mb-4">
                {cameraError}
              </div>
            )}

            <div className="grid grid-cols-3 gap-3">
              {!cameraOn ? (
                <button
                  onClick={startCamera}
                  className="py-4 rounded-xl bg-navy-900 text-white text-sm font-medium hover:bg-navy-800 transition flex items-center justify-center gap-2"
                >
                  <Camera size={18} />
                  {t(language, 'scanner.startCamera')}
                </button>
              ) : (
                <button
                  onClick={capture}
                  className="py-4 rounded-xl bg-gold-500 text-navy-900 text-sm font-semibold hover:bg-gold-600 transition flex items-center justify-center gap-2"
                >
                  <Camera size={18} />
                  {t(language, 'scanner.capture')}
                </button>
              )}
              <button
                onClick={() => fileInputRef.current?.click()}
                className="py-4 rounded-xl bg-white border border-slate-300 text-slate-700 text-sm font-medium hover:bg-slate-50 transition flex items-center justify-center gap-2"
              >
                <Upload size={18} />
                {t(language, 'scanner.uploadFile')}
              </button>
              <button
                onClick={backToChecklist}
                className="py-4 rounded-xl bg-white border border-slate-300 text-slate-700 text-sm font-medium hover:bg-slate-50 transition flex items-center justify-center gap-2"
              >
                <ArrowLeft size={18} />
                {t(language, 'scanner.actions.backToChecklist')}
              </button>
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp,image/bmp"
              onChange={onFilePicked}
              className="hidden"
            />
            <p className="mt-4 text-center text-xs text-slate-500">{t(language, 'scanner.languageNote')}</p>
          </div>
        )}

        {/* --------------------------------------------- Stage: processing -- */}
        {stage === 'processing' && (
          <div className="text-center py-20">
            <Loader2 size={40} className="mx-auto animate-spin text-navy-900" />
            <p className="mt-4 text-slate-600 text-sm">{t(language, 'scanner.processing')}</p>
          </div>
        )}

        {/* ------------------------------------------------ Stage: review -- */}
        {stage === 'review' && scan && (
          <div>
            <h2 className="text-xl font-bold text-navy-900 mb-1">{t(language, 'scanner.reviewTitle')}</h2>
            <p className="text-xs text-slate-600 mb-4">{t(language, 'scanner.reviewNote')}</p>

            {qualityBanner}
            {classificationBanner}

            {!scan.result.ocr_available && (
              <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 mb-4 text-amber-800 text-sm">
                <div className="font-semibold">{t(language, 'scanner.ocrUnavailableTitle')}</div>
                <p className="text-xs mt-1">
                  {scan.result.message || t(language, 'scanner.ocrUnavailableBody')}
                </p>
              </div>
            )}

            <div className="rounded-2xl border border-slate-200 bg-white p-5 mb-4">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs text-slate-500">{t(language, 'scanner.fields.editable')}</span>
                {scan.result.ocr_confidence != null && scan.result.ocr_confidence > 0 && (
                  <span className="text-xs bg-slate-100 text-slate-600 px-2 py-1 rounded">
                    {t(language, 'scanner.fields.confidence')}: {Math.round(scan.result.ocr_confidence)}%
                  </span>
                )}
              </div>

              {allEmpty && (
                <p className="text-sm text-slate-500 py-6 text-center">
                  {t(language, 'scanner.fields.empty')}
                </p>
              )}

              <div className="space-y-3">
                {fieldsArray.map(([field, f]) => (
                  <FieldRow
                    key={field}
                    field={field}
                    item={f}
                    language={language}
                    value={editedValues[field] ?? f.value ?? ''}
                    editing={!!editMode[field]}
                    onToggleEdit={() =>
                      f.value != null &&
                      setEditMode((m) => ({ ...m, [field]: !m[field] }))
                    }
                    onChange={(v) => setEditedValues((s) => ({ ...s, [field]: v }))}
                  />
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <button
                onClick={handleConfirm}
                disabled={allEmpty && !scan.result.ocr_available}
                className={`py-4 rounded-xl text-sm font-medium transition flex items-center justify-center gap-2 ${
                  allEmpty && !scan.result.ocr_available
                    ? 'bg-slate-300 text-slate-500 cursor-not-allowed'
                    : 'bg-navy-900 text-white hover:bg-navy-800'
                }`}
              >
                <CheckCircle size={18} />
                {t(language, 'scanner.actions.confirmExtraction')}
              </button>
              <button
                onClick={handleRescan}
                className="py-4 rounded-xl bg-white border border-slate-300 text-slate-700 text-sm font-medium hover:bg-slate-50 transition flex items-center justify-center gap-2"
              >
                <RefreshCw size={18} />
                {t(language, 'scanner.actions.rescan')}
              </button>
              <button
                onClick={backToChecklist}
                className="py-4 rounded-xl bg-white border border-slate-300 text-slate-700 text-sm font-medium hover:bg-slate-50 transition flex items-center justify-center gap-2"
              >
                <ArrowLeft size={18} />
                {t(language, 'scanner.actions.backToChecklist')}
              </button>
            </div>
          </div>
        )}

        {/* ----------------------------------------------- Stage: confirmed -- */}
        {stage === 'confirmed' && (
          <div className="text-center py-16">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <CheckCircle size={32} className="text-green-600" />
            </div>
            <h2 className="text-xl font-bold text-navy-900 mb-2">{t(language, 'scanner.confirmedTitle')}</h2>
            <p className="text-sm text-slate-600 max-w-md mx-auto mb-8">{t(language, 'scanner.confirmedBody')}</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-md mx-auto">
              <button
                onClick={handleRescan}
                className="py-4 rounded-xl bg-white border border-slate-300 text-slate-700 text-sm font-medium hover:bg-slate-50 transition flex items-center justify-center gap-2"
              >
                <ScanLine size={18} />
                {t(language, 'scanner.takeAnother')}
              </button>
              <button
                onClick={backToChecklist}
                className="py-4 rounded-xl bg-navy-900 text-white text-sm font-medium hover:bg-navy-800 transition flex items-center justify-center gap-2"
              >
                <ArrowLeft size={18} />
                {t(language, 'scanner.actions.backToChecklist')}
              </button>
            </div>
          </div>
        )}

        {/* --------------------------------------------------- Stage: error -- */}
        {stage === 'error' && (
          <div className="text-center py-16">
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <AlertTriangle size={32} className="text-red-600" />
            </div>
            <h2 className="text-lg font-bold text-navy-900 mb-2">{t(language, 'common.error')}</h2>
            <p className="text-sm text-slate-600 mb-8">{errorMsg}</p>
            <button
              onClick={() => { setStage('camera'); setPendingFile(null); setErrorMsg(null) }}
              className="py-3 px-8 rounded-xl bg-navy-900 text-white text-sm font-medium hover:bg-navy-800 transition"
            >
              <RefreshCw size={16} className="inline mr-2" />
              {t(language, 'scanner.retake')}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Field row: shows value, real OCR confidence, marker (OCR vs customer edit)
// ---------------------------------------------------------------------------

function FieldRow({
  field,
  item,
  language,
  value,
  editing,
  onToggleEdit,
  onChange,
}: {
  field: string
  item: ScanField
  language: Language
  value: string
  editing: boolean
  onToggleEdit: () => void
  onChange: (v: string) => void
}) {
  const conf = item.confidence
  const isCustomer = item.source === 'customer'
  const lowConf = conf != null && conf < 60

  return (
    <div className="border border-slate-200 rounded-xl p-3">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-medium text-slate-500">{item.label || field}</span>
        <div className="flex items-center gap-2">
          {isCustomer && (
            <span className="text-[10px] bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
              {t(language, 'scanner.markers.customer')}
            </span>
          )}
          {!isCustomer && conf != null && (
            <span
              className={`text-[10px] px-2 py-0.5 rounded ${
                lowConf ? 'bg-amber-100 text-amber-700' : 'bg-green-100 text-green-700'
              }`}
            >
              {t(language, 'scanner.markers.ocr')} {Math.round(conf)}%
            </span>
          )}
          {!isCustomer && (conf == null || lowConf) && (
            <span className="text-[10px] text-amber-700">
              {conf == null ? t(language, 'scanner.markers.unknownConf') : t(language, 'scanner.markers.lowConf')}
            </span>
          )}
        </div>
      </div>

      {editing ? (
        <div className="flex items-center gap-2">
          <input
            autoFocus
            value={value}
            onChange={(e) => onChange(e.target.value)}
            className="flex-1 px-3 py-2 border border-navy-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-navy-900/20"
          />
          <button onClick={onToggleEdit} className="text-xs text-navy-900 font-medium px-2">
            {t(language, 'common.save')}
          </button>
        </div>
      ) : (
        <button
          onClick={onToggleEdit}
          disabled={item.value == null && !value}
          className="w-full text-left"
        >
          {item.value == null && !value ? (
            <span className="text-sm text-slate-400 italic">
              {language === 'te' ? 'చదవబడలేదు' : language === 'hi' ? 'पढ़ा नहीं जा सका' : 'Not read from document'}
            </span>
          ) : (
            <span className="text-sm text-navy-900 font-medium break-words">{value}</span>
          )}
        </button>
      )}
    </div>
  )
}
