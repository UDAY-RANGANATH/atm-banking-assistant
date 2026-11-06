export type Language = 'en' | 'te' | 'hi'

export interface AppSession {
  sessionId: string
  language: Language
  currentStep: string
  selectedService?: string
  documentsScanned?: Record<string, any>
  confirmedInfo?: Record<string, any>
  applicationId?: string
}

export interface DocumentRequirement {
  name: string
  mandatory: boolean
  conditional: boolean
  purpose: string
  extractedFields: string[]
  alternatives: string[]
}

export interface BankingService {
  id: string
  category: string
  name: string
  formNumber: string
  isPrototype: boolean
  description: string
  helpText: string
  fullExplanation: string
  eligibility: string
  documents: DocumentRequirement[]
  estimatedTime: string
}

export interface ServiceCategory {
  key: string
  label: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

export interface DocumentItem {
  name: string
  mandatory: boolean
  purpose: string
  extractedFields: string[]
  alternatives?: string[]
  scanned: boolean
}

export interface SessionResponse {
  session_id: string
  language: string
  current_step: string
}

export interface ChatResponse {
  response: string
  source: string
  session_id: string
}

// ---- Phase 7: Multilingual AI Assistant Types ----

export interface AIChatAction {
  type: string
  service_id?: string
  label?: string
}

export interface AIChatResponse extends ChatResponse {
  language: Language
  actions: AIChatAction[]
  suggestions: string[]
}

export interface AIHealthStatus {
  provider: string
  configured: boolean
  model: string
  active_source: string
  rate_limited: boolean
  last_error: string | null
  last_ok_at: number | null
  language_detection: string
  knowledge_source: string
  conversation_sessions: number
}

export interface AISuggestionsResponse {
  language: Language
  suggestions: string[]
}

export interface StartApplicationResponse {
  session_id: string
  service_id: string
  service_name: string
  form_number: string
  current_step: string
}

// ---- Phase 3: Document Requirement Engine Types ----

export interface DocumentTranslation {
  name: string
  description: string
  purpose: string
}

export interface DocumentDefinition {
  id: string
  category: string
  name: Record<string, string>
  description: Record<string, string>
  purpose: Record<string, string>
  extracted_fields: string[]
  alternatives: string[]
  validation_requirements: string[]
  is_sensitive: boolean
}

export interface ServiceDocumentMapping {
  service_id: string
  document_id: string
  mandatory: boolean
  conditional: boolean
  conditional_reason: string | null
  service_specific_purpose: Record<string, string> | null
  alternatives: string[]
  notes: string | null
}

export interface DocumentChecklistItem {
  document_id: string
  name: string
  category: string
  description: string
  purpose: string
  mandatory: boolean
  conditional: boolean
  conditional_reason: string | null
  extracted_fields: string[]
  alternatives: string[]
  status: string
  scanned_at: string | null
  ocr_confidence: number | null
}

export interface DocumentChecklist {
  service_id: string
  service_name: string
  form_number: string
  documents: DocumentChecklistItem[]
  total_required: number
  total_optional: number
  total_conditional: number
}

export interface ChecklistUpdate {
  application_id: string
  document_id: string
  status: string
  scanned_at: string | null
  ocr_confidence: number | null
}

export interface ChecklistProgress {
  application_id: string
  service_id: string
  total_documents: number
  completed: number
  pending: number
  optional: number
  not_applicable: number
  needs_rescan: number
  percentage: number
  all_mandatory_complete: boolean
}

export type DocumentStatus = 'pending' | 'uploaded' | 'readable' | 'needs_rescan' | 'optional' | 'not_applicable'

// ---- Phase 4: Scanner & OCR Types ----

export interface ScanQuality {
  status: 'GOOD' | 'WARNING' | 'POOR'
  issues: string[]
  metrics: Record<string, any>
  explanations: string[]
}

export interface ScanField {
  label: string
  value: string | null
  confidence: number | null
  source_line: string | null
  source?: 'ocr' | 'customer'
}

export interface ScanClassification {
  expected_type: string
  detected_type: string | null
  match: 'MATCH' | 'MISMATCH' | 'UNKNOWN'
  evidence: string[]
}

export interface ScanPreprocessInfo {
  boundary_detected: boolean
  perspective_corrected: boolean
  rotation_corrected: boolean
  estimated_rotation_deg: number
  original_size: [number, number]
  processed_size: [number, number]
}

export interface ScanResult {
  ocr_available: boolean
  message?: string
  engine?: string
  languages_used?: string[]
  ocr_confidence?: number
  extraction_status: 'SUCCESS' | 'PARTIAL' | 'EMPTY_OCR' | 'OCR_UNAVAILABLE'
  classification: ScanClassification
  doc_type?: string
  fields: Record<string, ScanField>
  preprocess?: ScanPreprocessInfo
}

export interface ScanProcessResponse {
  scan_id: string
  status: string
  quality: ScanQuality
  result: ScanResult
}

export interface ScanRecordView {
  scan_id: string
  session_id: string
  service_id: string
  document_id: string
  source: 'camera' | 'upload'
  status: string
  created_at: string
  quality: ScanQuality | null
  result: ScanResult | null
  confirmed_by_customer: boolean
  history: Array<{ status: string; at: string }>
}

export interface OcrEngineStatus {
  ocr_available: boolean
  engine: string | null
  languages_available: string[]
  languages_requested: string[]
  supported: { eng: boolean; hin: boolean; tel: boolean }
}

// ---- Phase 5: Intelligent Application Form Autofill Types ----

export type FieldStatus =
  | 'AUTO_FILLED'
  | 'LOW_CONFIDENCE'
  | 'CONFLICT'
  | 'MISSING'
  | 'CUSTOMER_EDITED'
  | 'CUSTOMER_CONFIRMED'

export interface FormFieldSource {
  scan_id: string
  document_id: string | null
  doc_type: string
  doc_field: string
  doc_field_label: string | null
  note?: string
  corroborated_by?: string[]
}

export interface FieldConflictCandidate {
  value: string
  confidence: number | null
  scan_id: string
  document_id: string | null
  doc_type: string
  doc_field_label: string | null
}

export interface FormFieldView {
  field_id: string
  label: Record<string, string>
  type: 'text' | 'date' | 'select' | 'number' | 'masked'
  options: string[] | null
  pattern: string | null
  sensitive: boolean
  value: string | null
  status: FieldStatus
  confidence: number | null
  source: FormFieldSource | null
  conflicts: FieldConflictCandidate[] | null
}

export interface ApplicationFormView {
  application_id: string
  service_id: string
  service_name: string
  form_number: string
  status: string
  language?: string | null
  fields: FormFieldView[]
  autofill_runs: number
  last_autofill_at: string | null
  prototype_notice: string
}

export interface FieldRecord {
  value: string | null
  status: FieldStatus
  confidence: number | null
  source: FormFieldSource | null
  conflicts?: FieldConflictCandidate[] | null
}

export interface CompletionWarning {
  kind: 'conflict' | 'low_confidence' | 'missing'
  fields: string[]
}

export interface CompletionStatus {
  application_id: string
  service_id: string
  total_fields: number
  filled_fields: number
  counts: Record<FieldStatus, number>
  warnings: CompletionWarning[]
  ready_to_continue: boolean
  note: string
  pdf_ready?: boolean
  pdf_blocked_reason?: 'review_required' | 'unconfirmed_fields' | 'no_confirmation' | 'unknown' | null
}

export interface FieldMappingRule {
  doc_type: string
  doc_field: string
  form_field: string
  note?: string
}

// ---- Phase 6: Application PDF Generation & Export Types ----

export interface PdfFileInfo {
  file_name: string
  file_size: number
  page_count: number | null
  generated_at: string
}

export interface PdfStatusView {
  application_id: string
  service_id: string
  service_name: string
  form_number: string
  pdf_exists: boolean
  pdf: PdfFileInfo | null
  completion: CompletionStatus
}

export interface PdfGenerateMeta {
  application_id: string
  service_id: string
  service_name: string
  form_number: string
  language: string
  status: string
  generated_at: string
  file_name: string
  file_size: number
  page_count: number
  prototype_banner: string
}
