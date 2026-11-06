# AI-Powered ATM Banking Assistant (Prototype)

Educational prototype of an AI-powered ATM kiosk banking assistant. Built in phases following a strict separation-of-concerns architecture.

> **IMPORTANT:** This is a demonstration prototype, NOT an actual banking platform. No real money transfers, account openings, KYC verification, or banking transactions are implemented. Generated applications are demonstration documents and are not submitted to any bank.

## Technology Stack

**Frontend:** React, TypeScript, Vite, Tailwind CSS, Lucide React icons  
**Backend:** Python, FastAPI, Pydantic, SQLAlchemy, SQLite  
**PDF:** PyMuPDF 2.x Story/HTML layout with HarfBuzz complex-script shaping (ReportLab evaluated and rejected for Indic shaping)  
**OCR:** Tesseract 5.4 (local, offline) via pytesseract, with OpenCV preprocessing  
**AI:** Multilingual AI engine over a configurable LLM provider (`AI_PROVIDER`; default deterministic `mock`), with catalogue-grounded fallback that never depends on an external service

## Project Structure

```
atm-banking-assistant/
├── backend/
│   ├── .env.example
│   ├── requirements.txt
│   ├── tessdata/                # OCR language data (eng, hin, tel - tessdata_fast)
│   ├── temp_scans/              # Temporary scan images (auto-purged)
│   ├── scripts/
│   │   └── generate_test_docs.py # Synthetic (fake) test document generator
│   ├── tests/
│   │   ├── test_phase4.py       # Phase 4 automated test suite (54 tests)
│   │   ├── test_phase5.py       # Phase 5 automated test suite (73 tests)
│   │   ├── test_phase6.py       # Phase 6 automated test suite (86 tests)
│   │   ├── test_phase7.py       # Phase 7 automated test suite (104 tests)
│   │   ├── test_phase8.py       # Phase 8 E2E + security/deployment audit suite
│   │   ├── SECURITY_AUDIT.md    # Security & privacy audit findings (Phase 8)
│   │   └── fixtures/            # Generated synthetic test documents
│   └── app/
│       ├── __init__.py
│       ├── main.py              # FastAPI entry point
│       ├── core/
│       │   └── config.py        # Environment config (no hardcoded keys)
│       ├── db/
│       │   └── database.py      # SQLAlchemy SQLite setup (+ lazy migration)
│       ├── models.py            # DB models (Session, Conversation, Application, DocumentScan)
│       ├── api/
│       │   ├── routes.py        # REST endpoints (session, language, chat, services, applications)
│       │   ├── scanner_routes.py # Scanner & OCR endpoints (Phase 4)
│       │   ├── form_routes.py   # Application form autofill endpoints (Phase 5)
│       │   ├── pdf_routes.py    # PDF export endpoints (Phase 6)
│       │   └── ai_routes.py     # Multilingual AI assistant endpoints (Phase 7)
│       └── services/
│           ├── session.py       # Session management
│           ├── ai.py            # Multilingual AI engine (Phase 7 orchestrator)
│           ├── ai_provider.py   # Configurable LLM provider abstraction (Phase 7)
│           ├── ai_safety.py     # Input sanitisation + guardrail classification + reply validation (Phase 7)
│           ├── ai_knowledge.py  # Catalogue-grounded intents, matching, glossary, templates (Phase 7)
│           ├── ai_conversation.py # Bounded in-memory conversation store (Phase 7)
│           ├── ai_prompts.py    # Guardrailed prompt builder, no sensitive data (Phase 7)
│           ├── banking_services.py  # Configurable banking service catalogue
│           ├── document_engine.py   # Document requirement engine (Phase 3)
│           ├── image_processing.py  # Preprocessing + quality detection (Phase 4)
│           ├── ocr_engine.py        # Modular OCR engine - Tesseract provider (Phase 4)
│           ├── extraction.py        # Classification + structured extraction (Phase 4)
│           ├── scanner.py           # Scan lifecycle, transitions, temp cleanup (Phase 4)
│           ├── form_engine.py       # Canonical form fields, service schemas, OCR→form mappings (Phase 5)
│           ├── form_service.py      # Autofill engine, field states, persistence (Phase 5)
│           └── pdf_engine.py        # Multilingual PDF template engine (Phase 6)
└── frontend/
    ├── index.html
    ├── package.json
    ├── vite.config.ts
    ├── tailwind.config.js
    ├── postcss.config.js
    ├── tsconfig.json
    └── src/
        ├── main.tsx
        ├── index.css
        ├── App.tsx              # Routing
        ├── i18n/                # Centralized translations (en, te, hi)
        │   ├── index.ts
        │   ├── en.ts
        │   ├── te.ts
        │   └── hi.ts
        ├── types/               # TypeScript types
        ├── services/            # API service module
        ├── hooks/               # React hooks (useSession)
        ├── components/          # Reusable UI components
        │   ├── DocumentItem.tsx
        │   ├── DocumentProgress.tsx
        │   ├── HelpModal.tsx
        │   ├── KioskShell.tsx
        │   ├── LanguageSelector.tsx
        │   ├── ChatPanel.tsx
        │   └── ProgressIndicator.tsx
        └── pages/               # Page components
            ├── DocumentChecklistPage.tsx
            ├── DocumentScannerPage.tsx   # Camera scanner + extraction review (Phase 4)
            ├── ApplicationFormPage.tsx   # Application form autofill + review (Phase 5)
            ├── LanguageSelect.tsx
            └── Home.tsx
```

## Phase 1 Status: ✅ Complete

**Features implemented:**
- Project folder structure (frontend + backend separated)
- FastAPI backend with SQLite database
- Session management (session ID, language, current step)
- REST API endpoints: health, create session, set language, chat, get/delete session
- Modular AI service with mock fallback (no hardcoded API keys)
- Centralized i18n system (English, Telugu, Hindi)
- ATM kiosk visual design (navy, white, slate, gold palette)
- Landing screen: language selection
- Welcome chatbot screen in selected language
- Persistent chatbot panel
- Service catalogue browsing (Phase 1 preview)
- Responsive, touchscreen-optimized layout
- Navigation: home, restart, change language, help

## Phase 2 Status: ✅ Complete

**Features implemented:**
- Full banking service catalogue (all 4 categories, all specified services from the requirements master prompt)
- Service-specific prototype form numbers (ACC-001, KYC-001, CARD-001, LOAN-001, INV-001, etc.)
- Configurable banking service data module (backend: `banking_services.py`)
- Search and filtering functionality (search by name/description, category filter)
- Help button with AI explanation (7-part detailed explanation per service)
- Eligibility and process information per service
- Required documents with mandatory/optional/conditional classifications
- Start Application workflow (API + session context update)
- Help modal with service details, documents, eligibility, estimated time
- Prototype form number notices on every service
- All 59 services across Categories A-D implemented

## Phase 3 Status: ✅ Complete

**Features implemented:**
- Centralized document configuration system (`document_engine.py`)
- 39 reusable document definitions across 8 categories (A-H)
- Multilingual document names, descriptions, purposes (EN, TE, HI)
- Service-to-document mappings for all 59 services (145 total mappings)
- Mandatory/optional/conditional classifications
- Conditional requirement rules with reasons
- Accepted alternatives per document
- Information extraction fields per document
- Validation requirements per document
- Dynamic document checklist interface
- Document progress tracking (percentage, mandatory completion)
- Backend API endpoints:
  - GET /api/documents/catalogue
  - GET /api/documents/service/{service_id}
  - GET /api/documents/{document_id}
  - GET /api/documents/service/{service_id}/checklist
  - POST /api/documents/checklist/{application_id}/update
  - GET /api/documents/checklist/{application_id}/progress
- Frontend components: DocumentChecklistPage, DocumentItem, DocumentProgress
- Navigation from service catalogue to document checklist
- Document help modal with detailed explanations

## Installation & Execution

### Prerequisites
- Node.js (v18+) and npm
- Python 3.9+ and pip

### Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Optional: configure a real LLM provider (see AI Provider Configuration below).
# Without it the assistant runs fully deterministically on the local catalogues.
uvicorn app.main:app --reload
```

Backend runs at: http://localhost:8000  
API docs: http://localhost:8000/docs

#### AI Provider Configuration (Phase 7)

All provider settings are environment variables read by `app/core/config.py`; API keys never leave the backend and are never sent to the frontend:

```bash
AI_PROVIDER=mock            # mock | openai_compatible
AI_API_KEY=                 # server-side only
AI_BASE_URL=                # e.g. https://api.openai.com/v1
AI_MODEL=                   # model identifier requested from the provider
AI_TIMEOUT_SECONDS=20
AI_MAX_RETRIES=1
AI_RATE_LIMIT_COOLDOWN=10   # seconds of cooldown after HTTP 429
AI_MAX_MESSAGE_LENGTH=500
AI_HISTORY_TURNS=10
```

With `AI_PROVIDER=mock` (default) the assistant is 100% deterministic and offline: every answer is derived from the real service/document catalogues, with a clearly-labelled fallback template when no grounded answer applies. A configured provider is consulted opportunistically with the guardrailed prompt; its replies pass output validation (forbidden-claims / secret-solicitation / injected-identifier checks) before reaching the customer, otherwise the deterministic answer is used.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at: http://localhost:5173  
The frontend proxies `/api` requests to the backend.

### Run both

Open two terminals:
1. Terminal 1: backend (`uvicorn app.main:app --reload`)
2. Terminal 2: frontend (`npm run dev`)

Then open http://localhost:5173 in your browser.

## Testing Checklist (Phase 1 & Phase 2)

### Phase 1
- [ ] Backend health endpoint responds (`GET /api/health`)
- [ ] Session creation works (`POST /api/session`)
- [ ] Language selection persists (EN, TE, HI all render correctly)
- [ ] Welcome chatbot appears in the selected language
- [ ] Navigation between language screen and home screen works
- [ ] Responsive layout on mobile and desktop
- [ ] No hardcoded API keys in source code

### Phase 2
- [ ] Service categories endpoint responds (`GET /api/services/categories`)
- [ ] All services endpoint responds (`GET /api/services`)
- [ ] Service detail endpoint responds (`GET /api/services/{id}`)
- [ ] Start application endpoint responds (`POST /api/application/start`)
- [ ] All 59 services display correctly across 4 categories
- [ ] Search filters services by name and description
- [ ] Category filter shows correct services
- [ ] Help modal opens with 7-part explanation
- [ ] Start Application button updates session context
- [ ] Prototype form numbers display on every service card
- [ ] Document requirements show mandatory/optional/conditional badges
- [ ] All three languages (EN, TE, HI) render correctly
- [ ] Responsive layout on mobile and desktop

### Phase 3
- [ ] Document catalogue endpoint responds (`GET /api/documents/catalogue`)
- [ ] Documents for service endpoint responds (`GET /api/documents/service/{id}`)
- [ ] Document detail endpoint responds (`GET /api/documents/{document_id}`)
- [ ] Service checklist endpoint responds (`GET /api/documents/service/{id}/checklist`)
- [ ] Checklist update endpoint responds (`POST /api/documents/checklist/{app_id}/update`)
- [ ] Checklist progress endpoint responds (`GET /api/documents/checklist/{app_id}/progress`)
- [ ] All 59 services have document mappings
- [ ] 39 document definitions across 8 categories (A-H)
- [ ] Mandatory/optional/conditional classifications work correctly
- [ ] Conditional requirements display with reasons
- [ ] Document checklist page renders correctly
- [ ] Document progress indicator updates correctly
- [ ] Document help modal opens with detailed explanations
- [ ] All three languages (EN, TE, HI) render correctly for documents
- [ ] Navigation from service catalogue to document checklist works

### Phase 5
- [ ] Create session + upload/confirm a synthetic document in the scanner
- [ ] Start Application → checklist → "Start Form" opens `/application/form/{serviceId}`
- [ ] Form shows the three-language labels EN/TE/HI for the selected session language
- [ ] Autofill populates fields only from confirmed scans; source doc + confidence shown
- [ ] Missing fields show MISSING badge and can be typed manually
- [ ] Edit Field / Accept Value / Clear Value all update the status badge correctly
- [ ] Low-confidence and conflicting fields require review before Continue works
- [ ] Review Source Document opens the scan preview modal
- [ ] Save Progress shows the "Nothing has been submitted" note
- [ ] Continue requires the explicit confirmation checkbox, then states nothing was submitted
- [ ] Restarting the backend keeps saved progress (applications table persistence)

## Phase 4 Status: ✅ Complete

**Camera Scanner and Intelligent OCR Engine** — scans documents at the kiosk, reads text with a real local OCR engine (Tesseract 5.4), classifies the document, extracts structured fields, and requires the customer to review and confirm every value before it is recorded.

**Features implemented:**
- Camera access via MediaDevices API with framing guides (kiosk camera, `facingMode: environment`)
- Capture, preview, retake, and upload-from-device flows
- Real OCR processing pipeline (no fake OCR output ever generated):
  1. Preprocessing: resize → document boundary detection → perspective correction → rotation correction → grayscale → denoising (fastNlMeans) → contrast (CLAHE) → sharpening → optional adaptive threshold
  2. Quality assessment: sharpness (Laplacian variance), resolution, brightness/exposure, contrast, document boundary/rotation/cropping → GOOD / WARNING / POOR with customer-facing issue explanations
  3. **Best-of-two OCR**: enhanced-grayscale and adaptively-thresholded variants are both OCRed; the higher real-confidence result is kept
- Modular OCR service (`ocr_engine.py`): provider selection centralised; single Tesseract provider (5.4, UB-Mannheim). PaddleOCR rejected (no Python 3.13 Windows wheel), EasyOCR rejected (multi-GB Torch dependency). Languages are probed from the actual `*.traineddata` files in the project `backend/tessdata/` — eng, hin, tel (tessdata_fast) support English, Hindi and Telugu prints
- Document classification: OCR keyword evidence per type, with the selected checklist document as primary context → MATCH / MISMATCH / UNKNOWN; mismatch is reported as a warning and never silently accepted
- Structured field extraction: per-document-type schemas (≈35 document types covered), label-based matching on same line and stacked next-line labels, identifier/date/amount regexes requiring label context for amounts
- **Real confidence values only**: every field carries the actual Tesseract word/line confidence of the line it came from; no artificial confidence numbers
- **Nulls are never invented**: unread fields are returned as null and displayed as "Not read from document"
- **Extracted values preserved untranslated**: Hindi/Telugu text in scanned prints stays exactly as printed (script-preserving OCR, no translation layer)
- Extraction review screen: field-by-field display with real confidence badges, tap-to-edit corrections (marked as customer edits), confirm, or rescan
- Customer confirmation workflow: confirm (optionally with corrections) → scan `confirmed` → checklist item `readable`; rescan → `needs_rescan`
- Scan status lifecycle with valid transitions: `uploaded → ocr_processing → readable / confirmation_pending → confirmed / needs_rescan`
- Security & privacy by design:
  - Sensitive identifiers (Aadhaar, PAN, passport, account numbers) are **masked** before leaving the extraction module
  - **Raw OCR text is never persisted** — the DB stores only masked structured extraction JSON, quality, classification and status
  - Temp images stored under `backend/temp_scans/{session_id}/` with server-generated names; purged on confirm-complete, session cleanup, and a 6-hour expiry sweep
  - Server-side validation of session/service/document relationships (client IDs are never trusted)
- Checklist integration: scan status maps to Phase 3 checklist statuses (UPLOADED / READABLE / NEEDS_RESCAN); mandatory documents can never be silently marked NOT_APPLICABLE by this workflow
- Multilingual scanning UI: full scanner/review i18n strings in EN, TE, HI
- Backend API endpoints (11):
  - POST /api/scanner/upload, POST /api/scanner/capture
  - POST /api/scanner/process/{scan_id}, GET /api/scanner/result/{scan_id}
  - POST /api/scanner/confirm/{scan_id} (optional field corrections), POST /api/scanner/rescan/{scan_id}
  - GET /api/scanner/status/{session_id}, GET /api/scanner/image/{scan_id}
  - DELETE /api/scanner/{scan_id}, POST /api/scanner/cleanup/{session_id}
  - GET /api/scanner/engine/status
- Automated tests (`backend/tests/test_phase4.py`): 54 tests covering preprocessing, quality detection (blur/dark/small/tilted), real OCR on synthetic fixtures (EN/HI/TE), classification (MATCH/MISMATCH/UNKNOWN), extraction, masking, null preservation, empty-OCR handling, association validation, status transitions, checklist sync, and all API endpoints — all passing
- **Important distinction enforced in code and UI**: scanning reads *text from an image*. It is never claimed to verify a document's authenticity (that is KYC authentication, out of scope for OCR).

**Testing documents:** synthetic test documents are generated by `backend/scripts/generate_test_docs.py` into `backend/tests/fixtures/` — clearly watermarked "SYNTHETIC TEST DOCUMENT – NOT A REAL DOCUMENT". No real identity documents are used in tests or the demo.

### Installing the OCR engine (local, offline)

The OCR runs fully offline with Tesseract 5.4:

```bash
# Windows (winget) - UB-Mannheim build
winget install --id UB-Mannheim.TesseractOCR
# The app auto-detects tesseract.exe; language data lives in backend/tessdata/
```

## Phase 5 Status: ✅ Complete

**Intelligent Application Form Autofill** — connects the Phase 4 OCR extraction stage with Phase 2 application forms: fields are auto-populated only from the customer's *confirmed* document scans, every value is clearly labelled with its status, and the customer reviews, edits and explicitly approves each field before continuing.

**Features implemented:**
- Reusable form configuration engine (`form_engine.py`): canonical form field types with EN/TE/HI labels, input types and prototype validation patterns; per-category base schemas + per-service overrides generate a relevant form for **each of the 59 services** — 59 services without 59 implementations. Service form numbers (ACC-001, KYC-001, LOAN-001, …) come straight from Phase 2.
- OCR→form mapping registry (`FIELD_MAPPINGS`): document-type → form-field rules covering PAN (name/DOB/identifier→PAN number), Aadhaar (name/DOB/gender/address), salary slips (employee/employer/net salary→monthly income), bank statements (account holder / account number / bank / **IFSC**), utility bills, rent agreements, income/employment certificates, ITR, birth certificates, passports, voter IDs, driving licences, GST/business documents, insurance, demat and more.
- Autofill engine (`form_service.py`) with strict guarantees:
  - **Nothing is invented** — only values actually extracted by OCR from *confirmed or readable* scans of the same session *and same service* are used; `needs_rescan` scans are never used; unconfirmed scans are ignored until the customer confirms them in the Phase 4 review screen.
  - **Uncertain values are flagged, not trusted** — per-field OCR confidence < 60 ⇒ `LOW_CONFIDENCE`; missing confidence also requires review.
  - **Conflicts are never auto-resolved** — two documents disagreeing on a field ⇒ `CONFLICT` with every candidate value (original OCR values preserved) shown for the customer's decision.
  - **Customer decisions are final** — re-running autofill never overwrites `CUSTOMER_EDITED` / `CUSTOMER_CONFIRMED` values, and an explicit *Clear Value* stays cleared.
  - Extracted personal data (names, addresses, identifiers) is **preserved untranslated**, identifiers only ever in their masked form.
- Field status vocabulary exactly as specified — `AUTO_FILLED`, `LOW_CONFIDENCE`, `CONFLICT`, `MISSING`, `CUSTOMER_EDITED`, `CUSTOMER_CONFIRMED` — each with a colour-coded badge in the UI.
- Application Form page (`/application/form/:serviceId`):
  - Application name, prototype form number, reference number, service name
  - Auto-populated fields with source-document info (document label, OCR confidence, corroborating scans)
  - Editable inputs (manual completion of anything OCR could not read; the prototype never asks the customer to type full sensitive identifiers), *Edit Field / Accept Value / Clear Value / Review Source Document / Save Progress / Continue* actions
  - Missing-information and conflict warning banners; conflict candidates with a "Use this value" choice
  - *Review Source Document* modal showing the actual scan preview
- Multilingual UI: full `form.*` i18n section in EN, TE, HI (labels, warnings, actions, validation messages).
- Backend API (8 endpoints, all session-ownership enforced, nothing silently submitted):
  - POST /api/applications/init, GET /api/applications/{id}/form
  - POST /api/applications/{id}/autofill, GET /api/applications/{id}/field-mappings
  - PATCH /api/applications/{id}/fields/{field_id} (edit/clear/confirm/accept)
  - POST /api/applications/{id}/fields/confirm, POST /api/applications/{id}/save
  - GET /api/applications/{id}/completion-status
- Database: `applications` table extended with `service_id` + `session_key` columns (lazy SQLite migration); form state persisted as JSON in the existing `application_data` column — no schema duplication.
- Session lifecycle: DELETE /api/session/{id} now also purges that session's scans (incl. temp files) and applications — expired sessions lose access (403/404) immediately.
- Prototype honesty: the form carries a persistent educational-prototype notice; "Continue" opens a final review summary and **does not submit anything to any bank** (submission flow is later-phase scope).

**Testing:**
- Backend `backend/tests/test_phase5.py`: **73 tests** (mapping registry integrity incl. all spec examples, 59-service form resolution, multilingual labels, population from confirmed scans, null preservation, needs_rescan exclusion, low-confidence blocking, conflict detection with preserved candidates, edit/clear/confirm semantics, autofill non-overwrite of customer decisions, validation guardrails incl. manual sensitive-identifier rejection, prototype notice, session ownership (403), session cleanup/expiry, and API-mode tests of all endpoints on a real server, including a real synthetic-PAN OCR→autofill round trip via the Phase 4 pipeline).
- Phase 4 regression `backend/tests/test_phase4.py`: **54/54 passing**; Phase 2/3 endpoints re-verified.
- Frontend: 9 vitest unit tests (multilingual form i18n + API contract), 2 Playwright E2E flows, ESLint (new flat config) and production build.

## Phase 6 Status: ✅ Complete

**Application PDF Generation and Document Export** — turns the customer's reviewed form data into a professional, multilingual application PDF for **every one of the 59 services from one generic template engine** (no per-service generators), with strict gating, prominent prototype disclaimers and controlled temporary storage.

**Features implemented:**
- **Customer-confirmation gate**: PDF generation is refused (HTTP 409 with readable reason) until every populated field carries a customer decision (`CUSTOMER_CONFIRMED` or `CUSTOMER_EDITED`) and at least one confirmed field exists; low-confidence/conflict fields still under review also block the gate.
- **Confirmed data only**: values are printed exactly as confirmed (identifiers already masked upstream); blank fields are printed as "— not provided —"; visible per-field review status column (Customer-confirmed / Customer-edited / Not provided).
- **Professional A4 layout**: margins, styled headings, striped tables, header band with prototype form number and "Page X of Y", footer banner and generation date; multi-page pagination that never splits a table row across pages, repeats table headers at the top of continuation pages and never orphans a section heading.
- **PDF identity metadata**: application reference number, prototype form number, service name, generation date (UTC), document language and the customer-confirmation status on the first page.
- **Content sections are service-relevant only**: Application Details, Applicant / Contact / Address / Account / Service-Specific Information, Uploaded Document Checklist (reuses the Phase 3 checklist engine), Customer Declarations and Customer Confirmation.
- **Multilingual PDFs (EN / TE / HI)**: built on **PyMuPDF 2.x Story/HTML layout with HarfBuzz complex-script shaping** (ReportLab was evaluated and rejected: no OpenType shaping — Devanagari pre-base matras and conjuncts rendered in wrong visual order). Bundled Noto Sans + Noto Sans Devanagari + Noto Sans Telugu (Regular+Bold, SIL OFL) render every script correctly (visually verified at raster: bā lāgā-like conjuncts, Telugu vattu subscripts, no tofu). Latin `liga` features are renamed in cached derived fonts (fontTools) so text extraction/search still matches plain ASCII ("affiliated", "confirmed") while all Indic shaping features stay intact.
- **Prominent prototype banner on every page**: "EDUCATIONAL PROTOTYPE — NOT AN OFFICIAL BANK DOCUMENT" plus disclaimers — not affiliated with or issued by HDFC Bank, not valid for banking transactions, not valid for KYC verification, no application has been submitted. No official logos, seals or signatures; original prototype visual identity only.
- **Frontend PDF export page** (`/application/pdf/:serviceId`): reference number, service, form number, PDF status (Ready / Not generated yet / Generation blocked) with the blocking reason and completed-field summary; PDF language selector (EN/TE/HI); actions **Generate (button disabled + blocked reason when the gate fails) / Preview (inline viewer) / Download / Print / Delete / Return to Application**; meaningful error messages for 409 (blocked), 403 (cross-session) and 404.
- **Backend APIs** (all session-ownership enforced): POST `/api/applications/{id}/generate-pdf`, GET `/api/applications/{id}/pdf` (inline, no-store), GET `/api/applications/{id}/pdf/status`, DELETE `/api/applications/{id}/pdf`.
- **Controlled storage & cleanup**: PDFs live only in `backend/generated_pdfs/{session_key}/` (no static mount, no public URL, `no-store` cache headers); removed when the session is deleted or expires, plus a 6-hour retention sweep; nothing sensitive is logged.
- **Form-page hook-up**: a "Confirm All Filled Fields" bulk action records review decisions for every populated field (required by the PDF gate), and the final-review confirmation flow ends in "Continue to PDF Export".

**Testing:**
- Backend `backend/tests/test_phase6.py`: **86 tests** (service + API modes): gate blocking (409 with reason codes), missing fields not blocking, EN/TE/HI generation with localized chrome and disclaimers, confirmed values printed exactly, masked identifiers preserved, multi-page output, page-boundary chunking, regeneration overwrite, delete, session purge, expiry sweep, no public URL, ownership (403) and invalid-reference (404) checks, session-deletion cleanup.
- Full regression: Phase 5 **73/73** (service + api), Phase 4 **54/54**, Phase 2/3 endpoint smoke (59 services, checklists, acc-001), frontend vitest **9/9**, `tsc --noEmit` clean, ESLint clean, production build green, Playwright E2E **4/4** (incl. new PDF flow: blocked → confirm-all → generate → preview → real %PDF- download).
- Visual verification: EN/TE/HI PDFs rasterized and inspected — correct shaping, no missing-glyph boxes, banner/disclaimers/layout confirmed.

## Phase 7 Status: ✅ Complete

**Multilingual AI Integration** — a catalogue-grounded multilingual assistant over a configurable LLM provider abstraction. The kiosk never depends on an external AI service: with no provider configured (default `AI_PROVIDER=mock`), every answer is computed deterministically from the real Phase 2/3/5 data, and a configured provider is only consulted opportunistically with heavily guardrailed prompts.

**Features implemented:**
- **AI provider abstraction** (`ai_provider.py`): `AI_PROVIDER` of `mock | openai_compatible` (OpenAI Chat Completions shape over `AI_BASE_URL`), model from `AI_MODEL`, stdlib `urllib` calls inside `asyncio.to_thread` (no new dependencies), per-call timeout (`AI_TIMEOUT_SECONDS`), bounded retries for transient errors only (`AI_MAX_RETRIES`; never for 4xx), a cooldown window after HTTP 429 (`AI_RATE_LIMIT_COOLDOWN`), `AIProviderError(detail, status, retryable)`, `health_ping()` and a secret-free `status()` for `GET /api/ai/health`. A deterministic test seam (`set_provider_for_testing`) powers all mocked-provider tests — **no paid API calls anywhere in the test suite**.
- **Banking knowledge layer** (`ai_knowledge.py`): intents (greeting, list services, documents, eligibility, procedure, time, progress, PDF, autofill, scan-rejection, unavailable-fees) with EN/TE/HI keyword phrase lists; service matching (form-number regex → verbatim catalogue name → curated aliases → token-overlap scoring) whose only source of truth is `banking_services.py` / `document_engine.py` / `form_service.py`; a 11-term neutral glossary admitted only for definitional questions (never over an explicitly mentioned prototype form number); fully-grounded EN/TE/HI reply templates. Fees/rates/policies are explicitly answered with "unavailable in this prototype" — never invented.
- **What it answers**: descriptions of all 4 categories and all 59 services, required document checklists (real Phase 3 mappings, mandatory first), eligibility, procedures + prototype form numbers, estimated time, application progress (real Phase 5 completion status from the session's active application), PDF export guidance, autofill guidance (directs to the form, never fills it), scan-rejection explanations (quality/checklist causes), mid-session language switching ("reply in telugu…"), and conversational context within the session.
- **Language handling**: replies always in the customer's SELECTED language (spec), tolerant of mixed-language and typo'd input; script detection (Telugu 0C00–0C7F, Devanagari 0900–097F) for transliterated/mixed requests; centralised en/te/hi templates and suggestions. Names, addresses, account numbers and any extracted personal data are never translated.
- **Safety guardrails** (`ai_safety.py`): input sanitisation masks PAN/Aadhaar/long-digit identifiers and OTP/secret phrases (`[PAN-REDACTED]`, `[ID-REDACTED]`, `[NUMBER-REDACTED]`, `[SECRET-REDACTED]`), strips control characters, caps length; classification refuses real transactions/balance/withdrawal requests with a clear prototype explanation, and warns on PIN/CVV/OTP/password sharing without ever echoing the secret. Provider replies are validated before display: forbidden claims (account access, real transactions, RBI/HDFC submission, document verification), secret solicitation, injected unknown identifiers, empty/overlong replies all fall back to the deterministic answer. Document images / raw OCR and sensitive identifiers never enter any prompt; the assistant can never modify fields, confirm documents, approve applications or generate PDFs — it only offers navigation.
- **Conversation architecture** (`ai_conversation.py`): bounded in-memory store (40 messages, `AI_HISTORY_TURNS` context window), last-service/last-intent context for follow-ups ("which documents do I need?" after naming a service); `DELETE /api/ai/conversation/{id}` requires `X-Session-Id` ownership (403 otherwise) and DELETE `/api/session/{id}` purges it too.
- **API** (`ai_routes.py`, registered under `/api`): POST `/api/ai/chat` → `{response, source, session_id, language, actions, suggestions}` (`assistant | provider | fallback | safety`; actions offer-only `navigate_service`), GET `/api/ai/health` (+ opt-in bounded `?probe=1`), GET `/api/ai/suggestions?language=/session_id=`, DELETE `/api/ai/conversation/{session_id}`. The legacy Phase 1 POST `/api/chat` keeps its exact `{response, source, session_id}` contract and now routes through the same engine.
- **Conversational UI** (`ChatPanel.tsx`): language-aware suggestions chips (server `suggestions` of the last reply, or `/api/ai/suggestions`), service navigation action buttons, clear-chat button (ownership-enforced DELETE + local reset), localized typing indicator and error messages, internet-header health styling unchanged; kiosk design preserved; desktop/tablet/mobile responsive split layout; used on Home and the document-checklist page.
- **i18n**: new `chat.*` keys (typing, suggestions, clearChat, chatCleared, online) in en/te/hi, type-checked for key parity.

**Testing:**
- Backend `backend/tests/test_phase7.py`: **104/104** (service + API modes, dual-mode like Phases 4-6).

## Phase 8 Status: ✅ Complete

**Integration, Testing and Final Polish** — the final phase. Every module built in Phases 1–7 was verified as one integrated system, hardening fixes were applied where probing exposed real defects, and a deployment path was added.

**What Phase 8 delivered:**

- **End-to-end integration suite** (`backend/tests/test_phase8.py`, dual-mode like Phases 4–7):
  - **11 service-mode checks**: catalogue invariants (59 services / 4 categories / 39 documents), deterministic-authority verification (a hostile injected "LLM provider" whose reply claims a completed transfer and solicits an OTP is rejected by the guardrails — the engine's own catalogue answer wins), prompt-mask audit through the real engine path (PAN/Aadhaar/OTP never leave unredacted), source scan for API-key logging, built-bundle secret scan, single-origin deployment probe, and temp-scan purge verification.
  - **16 numbered API E2E cases (E2E-01 … E2E-16)** against the live server covering the complete kiosk lifecycle: session → application → checklist → scan upload → autofill → per-field confirmation → PDF gate → generate → real `%PDF-` download (E2E-01); grounded progress answers (E2E-02); legacy contract stability (E2E-03); byte-stable deterministic answers (E2E-04); real-transaction refusal (E2E-05); Telugu/Hindi conversations (E2E-06); same-application multi-language PDF export (E2E-06b); checklist-grounded document answers (E2E-07); scan-rejection help (E2E-08); autofill never mutates the form (E2E-09); PDF guidance (E2E-10); no invented rates (E2E-11); 404s + unsupported-language fallback (E2E-12); conversation + session purge (E2E-13); cross-session 403s (E2E-14); performance budgets (E2E-15); concurrency + determinism + health (E2E-16).
- **Real engine defects found by the E2E suite and fixed** (probing as designed):
  - `ai_knowledge.match_intent` used bare substring matching, so the greeting keyword `"hi"` matched inside `"which"` and hijacked unrelated questions — replaced with word-boundary matching for Latin keywords (plain containment kept for Indic scripts).
  - `ai_safety._REAL_TRANSACTION_RE` missed `"transfer Rs 5000"` (currency group absent from the transfer pattern) — transaction verb groups extended with `rs|rupees|inr|amount|<digits>` so money-movement requests of every common phrasing are refused.
- **Security & privacy audit** (`backend/tests/SECURITY_AUDIT.md`): prompted-secret/redaction audit through the engine path, guardrail coverage, no API-key logging, no secrets in the built bundle, session-ownership (403) enforcement everywhere, temp-only storage purges, synthetic-data-only test fixtures.
- **Session lifecycle & cleanup verification**: conversation + session delete purge access end to end (deleted session → chat 404); temp scan areas purge on demand and on expiry.
- **Multilingual verification**: Telugu/Hindi chat answers in the selected script; the same application exports EN/TE/HI PDFs through the Phase 6 engine (correct shaping previously verified visually in Phase 6).
- **Responsive ATM kiosk interface**: new Playwright spec (`frontend/e2e/full-journey.spec.ts`) verifies the Home layout at mobile 390×844 and tablet 820×1180 — chat + catalogue grid stacks vertically (`flex-col-reverse lg:flex-row`), both panels visible and interactive, no horizontal overflow.
- **Performance & reliability budgets**: full services catalogue < 2 s; 8 consecutive AI answers < 12 s; 6 concurrent chat threads across independent sessions return identical byte-stable answers; `/api/ai/health` stays healthy throughout.
- **Error handling & recovery**: invalid service/application/chat → 404; unsupported language → deterministic `en` fallback; blocked PDF gates return readable reason codes; ownership violations → 403 on every route family.
- **Deployment configuration**: `SERVE_FRONTEND_DIST=1` mounts the built kiosk UI (`frontend/dist`) from FastAPI itself for a **single-origin** production deployment — no CORS or reverse proxy required. The deterministic backend remains the sole authority for all banking operations; the mount serves static files only. Documented in `backend/.env.example`.
- **Final documentation**: this README (deployment instructions below), `docs/PROGRESS.md` Phase 8 section, and all Phase 8 requirement checkboxes.

**Testing (final matrix):**

```
Backend (dual-mode suites against live uvicorn)
  Phase 4 : 54/54      Phase 5 : 73/73      Phase 6 : 86/86
  Phase 7 : 104/104    Phase 8 : 28/28 (11 service checks + 17 E2E reports, 16 cases)
Frontend
  vitest unit           15/15
  TypeScript (tsc)      0 errors
  ESLint                0 errors
  Production build      green (frontend/dist)
  Playwright E2E        10/10 (application-form 2 + chat 3 + PDF export 2 + full journey 1 + responsive kiosk 2)
```

## Deployment (production-style run)

Single-origin deployment — the FastAPI backend serves both the API and the built kiosk UI:

```bash
# 1. Build the frontend
cd frontend
npm run build                      # outputs frontend/dist

# 2. Configure the backend (backend/.env)
#    SERVE_FRONTEND_DIST=1
#    FRONTEND_DIST_PATH=../frontend/dist
#    AI_PROVIDER=mock               # deterministic engine; or configure a provider
#    # AI_API_KEY / AI_BASE_URL / AI_MODEL  (server-side only, never sent to the UI)

# 3. Run without --reload
cd ../backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
#    UI:  http://<host>:8000/      API:  http://<host>:8000/api
```

Development mode stays unchanged: backend `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000` + frontend `npm run dev` (vite on 5173 proxies `/api` to 8000).

## Security & Demo Notes

- No real banking credentials, OTPs, PINs, or CVVs are collected.
- No actual banking transactions are performed.
- API keys must be stored in environment variables (`.env`), never hardcoded.
- With no provider configured the AI assistant is fully deterministic/clearly-labelled (`AI_PROVIDER=mock`), grounded in the local catalogues; provider replies are validated against guardrails before ever reaching the customer.
