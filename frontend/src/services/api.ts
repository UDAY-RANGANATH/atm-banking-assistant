import {
  SessionResponse,
  ChatResponse,
  AIChatResponse,
  AIHealthStatus,
  AISuggestionsResponse,
  BankingService,
  ServiceCategory,
  StartApplicationResponse,
  DocumentDefinition,
  ServiceDocumentMapping,
  DocumentChecklist,
  ChecklistProgress,
  ScanProcessResponse,
  ScanRecordView,
  ApplicationFormView,
  FieldRecord,
  CompletionStatus,
  FieldMappingRule,
  PdfStatusView,
  PdfGenerateMeta,
} from '../types'

const API_BASE = '/api'

export const api = {
  async health() {
    const res = await fetch(`${API_BASE}/health`)
    return res.json()
  },

  async createSession(language: string = 'en'): Promise<SessionResponse> {
    const res = await fetch(`${API_BASE}/session?language=${encodeURIComponent(language)}`, {
      method: 'POST',
    })
    if (!res.ok) throw new Error('Failed to create session')
    return res.json()
  },

  async setLanguage(sessionId: string, language: string): Promise<SessionResponse> {
    const res = await fetch(`${API_BASE}/session/language`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, language }),
    })
    if (!res.ok) throw new Error('Failed to set language')
    return res.json()
  },

  async chat(sessionId: string, message: string): Promise<ChatResponse> {
    const res = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, message }),
    })
    if (!res.ok) throw new Error('Chat failed')
    return res.json()
  },

  // ---- Multilingual AI Assistant (Phase 7) ----

  /**
   * Rich AI chat: replies in the customer's SELECTED language and returns
   * navigation actions + suggested follow-up questions. Credentials stay
   * server-side; the client never sees provider secrets.
   */
  async aiChat(
    sessionId: string,
    message: string,
    language?: string,
  ): Promise<AIChatResponse> {
    const res = await fetch(`${API_BASE}/ai/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, message, language }),
    })
    if (!res.ok) {
      const e = new Error(`AI chat failed (${res.status})`) as Error & { status?: number }
      e.status = res.status
      throw e
    }
    return res.json()
  },

  /** Provider status without secrets (also used for the header health dot). */
  async aiHealth(): Promise<AIHealthStatus> {
    const res = await fetch(`${API_BASE}/ai/health`)
    if (!res.ok) throw new Error('AI health check failed')
    return res.json()
  },

  /** Language-aware suggested questions (session language wins). */
  async aiSuggestions(sessionId?: string, language?: string): Promise<AISuggestionsResponse> {
    const params = new URLSearchParams()
    if (sessionId) params.set('session_id', sessionId)
    if (language) params.set('language', language)
    const q = params.toString() ? `?${params.toString()}` : ''
    const res = await fetch(`${API_BASE}/ai/suggestions${q}`)
    if (!res.ok) throw new Error('Failed to fetch AI suggestions')
    return res.json()
  },

  /**
   * Clears one conversation. Ownership enforced server-side via
   * X-Session-Id; the kiosk client always sends its own session id.
   */
  async clearConversation(sessionId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/ai/conversation/${encodeURIComponent(sessionId)}`, {
      method: 'DELETE',
      headers: { 'X-Session-Id': sessionId },
    })
    if (!res.ok) throw new Error('Failed to clear conversation')
  },

  async getSession(sessionId: string): Promise<SessionResponse> {
    const res = await fetch(`${API_BASE}/session/${sessionId}`)
    if (!res.ok) throw new Error('Session not found')
    return res.json()
  },

  async deleteSession(sessionId: string) {
    await fetch(`${API_BASE}/session/${sessionId}`, { method: 'DELETE' })
  },

  // ---- Service Catalogue (Phase 2) ----

  async getServiceCategories(): Promise<ServiceCategory[]> {
    const res = await fetch(`${API_BASE}/services/categories`)
    if (!res.ok) throw new Error('Failed to fetch service categories')
    return res.json()
  },

  async getServices(category?: string): Promise<BankingService[]> {
    const url = category
      ? `${API_BASE}/services?category=${encodeURIComponent(category)}`
      : `${API_BASE}/services`
    const res = await fetch(url)
    if (!res.ok) throw new Error('Failed to fetch services')
    return res.json()
  },

  async getServiceDetails(serviceId: string): Promise<BankingService> {
    const res = await fetch(`${API_BASE}/services/${serviceId}`)
    if (!res.ok) throw new Error('Service not found')
    return res.json()
  },

  async startApplication(
    sessionId: string,
    serviceId: string,
  ): Promise<StartApplicationResponse> {
    const res = await fetch(`${API_BASE}/application/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, service_id: serviceId }),
    })
    if (!res.ok) throw new Error('Failed to start application')
    return res.json()
  },

  // ---- Document Requirement Engine (Phase 3) ----

  async getDocumentsCatalogue(): Promise<DocumentDefinition[]> {
    const res = await fetch(`${API_BASE}/documents/catalogue`)
    if (!res.ok) throw new Error('Failed to fetch document catalogue')
    return res.json()
  },

  async getDocumentsForService(serviceId: string): Promise<ServiceDocumentMapping[]> {
    const res = await fetch(`${API_BASE}/documents/service/${serviceId}`)
    if (!res.ok) throw new Error('Failed to fetch documents for service')
    return res.json()
  },

  async getDocumentDetail(documentId: string): Promise<DocumentDefinition> {
    const res = await fetch(`${API_BASE}/documents/${documentId}`)
    if (!res.ok) throw new Error('Document not found')
    return res.json()
  },

  async getServiceChecklist(serviceId: string, applicationId?: string): Promise<DocumentChecklist> {
    const q = applicationId ? `?application_id=${encodeURIComponent(applicationId)}` : ''
    const res = await fetch(`${API_BASE}/documents/service/${serviceId}/checklist${q}`)
    if (!res.ok) throw new Error('Failed to fetch service checklist')
    return res.json()
  },

  async updateChecklistItem(
    applicationId: string,
    documentId: string,
    status: string,
  ) {
    const res = await fetch(
      `${API_BASE}/documents/checklist/${applicationId}/update`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          application_id: applicationId,
          document_id: documentId,
          status,
        }),
      },
    )
    if (!res.ok) throw new Error('Failed to update checklist item')
    return res.json()
  },

  async getChecklistProgress(
    applicationId: string,
    serviceId: string,
  ): Promise<ChecklistProgress> {
    const res = await fetch(
      `${API_BASE}/documents/checklist/${applicationId}/progress?service_id=${encodeURIComponent(serviceId)}`,
    )
    if (!res.ok) throw new Error('Failed to fetch checklist progress')
    return res.json()
  },

  // ---- Scanner & OCR (Phase 4) ----

  async submitScan(
    endpoint: 'capture' | 'upload',
    sessionId: string,
    serviceId: string,
    documentId: string,
    file: Blob | File,
    filename: string,
  ): Promise<ScanProcessResponse> {
    const form = new FormData()
    form.append('session_id', sessionId)
    form.append('service_id', serviceId)
    form.append('document_id', documentId)
    form.append('file', file, filename)
    const res = await fetch(`${API_BASE}/scanner/${endpoint}`, {
      method: 'POST',
      body: form,
    })
    if (!res.ok) {
      let detail = 'Scan submission failed'
      try {
        const err = await res.json()
        if (err?.detail) detail = typeof err.detail === 'string' ? err.detail : detail
      } catch { /* ignore parse errors */ }
      throw new Error(detail)
    }
    return res.json()
  },

  async reprocessScan(scanId: string): Promise<ScanProcessResponse> {
    const res = await fetch(`${API_BASE}/scanner/process/${encodeURIComponent(scanId)}`, {
      method: 'POST',
    })
    if (!res.ok) throw new Error('Failed to reprocess scan')
    return res.json()
  },

  async getScanResult(scanId: string): Promise<ScanRecordView> {
    const res = await fetch(`${API_BASE}/scanner/result/${encodeURIComponent(scanId)}`)
    if (!res.ok) throw new Error('Scan not found')
    return res.json()
  },

  async confirmScan(
    scanId: string,
    corrections?: Record<string, string>,
  ): Promise<ScanRecordView> {
    const res = await fetch(`${API_BASE}/scanner/confirm/${encodeURIComponent(scanId)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(corrections ? { corrections } : {}),
    })
    if (!res.ok) throw new Error('Failed to confirm scan')
    return res.json()
  },

  async rescanScan(scanId: string): Promise<ScanRecordView> {
    const res = await fetch(`${API_BASE}/scanner/rescan/${encodeURIComponent(scanId)}`, {
      method: 'POST',
    })
    if (!res.ok) throw new Error('Failed to request rescan')
    return res.json()
  },

  async scanImageUrl(scanId: string, variant: 'processed' | 'original' = 'processed'): Promise<string> {
    return `${API_BASE}/scanner/image/${encodeURIComponent(scanId)}?variant=${variant}`
  },

  async getOcrEngineStatus() {
    const res = await fetch(`${API_BASE}/scanner/engine/status`)
    if (!res.ok) throw new Error('Failed to fetch OCR engine status')
    return res.json()
  },

  async getSessionScans(sessionId: string) {
    const res = await fetch(`${API_BASE}/scanner/status/${encodeURIComponent(sessionId)}`)
    if (!res.ok) throw new Error('Failed to fetch session scans')
    return res.json()
  },

  async deleteScan(scanId: string) {
    const res = await fetch(`${API_BASE}/scanner/${encodeURIComponent(scanId)}`, {
      method: 'DELETE',
    })
    if (!res.ok) throw new Error('Failed to delete scan')
    return res.json()
  },

  // ---- Application Form Autofill (Phase 5) ----

  /**
   * API errors carry i18n-able detail keys (e.g. "pattern.mobile_number").
   * FormApiError exposes them to the UI; values are never logged server-side.
   */
  async _formError(res: Response): Promise<never> {
    let detail = 'Form request failed'
    try {
      const err = await res.json()
      if (err?.detail) detail = typeof err.detail === 'string' ? err.detail : detail
    } catch { /* ignore parse errors */ }
    const e = new Error(`Form API error ${res.status}`) as Error & { detail?: string; status?: number }
    e.detail = detail
    e.status = res.status
    throw e
  },

  async initApplication(sessionId: string, serviceId: string): Promise<ApplicationFormView> {
    const res = await fetch(`${API_BASE}/applications/init`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, service_id: serviceId }),
    })
    if (!res.ok) return this._formError(res)
    return res.json()
  },

  async getApplicationForm(
    applicationId: string,
    sessionId: string,
    language?: string,
  ): Promise<ApplicationFormView> {
    const q = language ? `&language=${encodeURIComponent(language)}` : ''
    const res = await fetch(
      `${API_BASE}/applications/${encodeURIComponent(applicationId)}/form?session_id=${encodeURIComponent(sessionId)}${q}`,
    )
    if (!res.ok) return this._formError(res)
    return res.json()
  },

  async autofillApplication(
    applicationId: string,
    sessionId: string,
    language?: string,
  ): Promise<ApplicationFormView> {
    const q = language ? `&language=${encodeURIComponent(language)}` : ''
    const res = await fetch(
      `${API_BASE}/applications/${encodeURIComponent(applicationId)}/autofill?session_id=${encodeURIComponent(sessionId)}${q}`,
      { method: 'POST' },
    )
    if (!res.ok) return this._formError(res)
    return res.json()
  },

  async getFieldMappings(
    applicationId: string,
    sessionId: string,
  ): Promise<{ application_id: string; mappings: FieldMappingRule[] }> {
    const res = await fetch(
      `${API_BASE}/applications/${encodeURIComponent(applicationId)}/field-mappings?session_id=${encodeURIComponent(sessionId)}`,
    )
    if (!res.ok) return this._formError(res)
    return res.json()
  },

  async patchApplicationField(
    applicationId: string,
    sessionId: string,
    fieldId: string,
    action: 'edit' | 'clear' | 'confirm' | 'accept',
    value?: string,
  ): Promise<{ application_id: string; field_id: string; record: FieldRecord }> {
    const res = await fetch(
      `${API_BASE}/applications/${encodeURIComponent(applicationId)}/fields/${encodeURIComponent(fieldId)}`,
      {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, action, value }),
      },
    )
    if (!res.ok) return this._formError(res)
    return res.json()
  },

  async confirmApplicationFields(
    applicationId: string,
    sessionId: string,
    fieldIds: string[],
  ): Promise<{ application_id: string; confirmed: string[]; skipped: Record<string, string> }> {
    const res = await fetch(
      `${API_BASE}/applications/${encodeURIComponent(applicationId)}/fields/confirm`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, field_ids: fieldIds }),
      },
    )
    if (!res.ok) return this._formError(res)
    return res.json()
  },

  async saveApplication(
    applicationId: string,
    sessionId: string,
  ): Promise<{ application_id: string; status: string; saved_at: string; note: string }> {
    const res = await fetch(
      `${API_BASE}/applications/${encodeURIComponent(applicationId)}/save?session_id=${encodeURIComponent(sessionId)}`,
      { method: 'POST' },
    )
    if (!res.ok) return this._formError(res)
    return res.json()
  },

  async getCompletionStatus(
    applicationId: string,
    sessionId: string,
  ): Promise<CompletionStatus> {
    const res = await fetch(
      `${API_BASE}/applications/${encodeURIComponent(applicationId)}/completion-status?session_id=${encodeURIComponent(sessionId)}`,
    )
    if (!res.ok) return this._formError(res)
    return res.json()
  },

  // ---- Application PDF Generation (Phase 6) ----

  /**
   * PDF API errors carry human-readable details (blocked gate 409,
   * cross-session 403, unknown reference 404). Values are never logged.
   */
  async _pdfError(res: Response): Promise<never> {
    let detail = 'PDF request failed'
    try {
      const err = await res.json()
      if (err?.detail) detail = typeof err.detail === 'string' ? err.detail : detail
    } catch { /* ignore parse errors */ }
    const e = new Error(`PDF API error ${res.status}`) as Error & { detail?: string; status?: number }
    e.detail = detail
    e.status = res.status
    throw e
  },

  async getPdfStatus(applicationId: string, sessionId: string): Promise<PdfStatusView> {
    const res = await fetch(
      `${API_BASE}/applications/${encodeURIComponent(applicationId)}/pdf/status?session_id=${encodeURIComponent(sessionId)}`,
    )
    if (!res.ok) return this._pdfError(res)
    return res.json()
  },

  async generatePdf(
    applicationId: string,
    sessionId: string,
    language: string = 'en',
  ): Promise<PdfGenerateMeta> {
    const res = await fetch(
      `${API_BASE}/applications/${encodeURIComponent(applicationId)}/generate-pdf`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, language }),
      },
    )
    if (!res.ok) return this._pdfError(res)
    return res.json()
  },

  /** Fetches the stored PDF bytes after the ownership check. */
  async getPdfBlob(applicationId: string, sessionId: string): Promise<Blob> {
    const res = await fetch(
      `${API_BASE}/applications/${encodeURIComponent(applicationId)}/pdf?session_id=${encodeURIComponent(sessionId)}`,
    )
    if (!res.ok) return this._pdfError(res)
    return res.blob()
  },

  async deletePdf(
    applicationId: string,
    sessionId: string,
  ): Promise<{ application_id: string; status: string }> {
    const res = await fetch(
      `${API_BASE}/applications/${encodeURIComponent(applicationId)}/pdf?session_id=${encodeURIComponent(sessionId)}`,
      { method: 'DELETE' },
    )
    if (!res.ok) return this._pdfError(res)
    return res.json()
  },
}
