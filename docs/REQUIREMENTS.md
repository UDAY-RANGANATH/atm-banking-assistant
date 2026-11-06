# Project Requirements Document

## Overview

**Project:** AI-Powered ATM Banking Assistant (Educational Prototype)

**Objective:** Build an intelligent ATM banking assistant that helps customers complete banking applications without needing assistance from a bank employee.

**Important:** This is a demonstration prototype, NOT an actual banking platform. No real money transfers, real account opening, real card issuance, actual KYC verification or actual banking transactions are implemented.

## Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | React, TypeScript, Vite, Tailwind CSS, Lucide React icons |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy, SQLite |
| PDF | PyMuPDF 2.x Story/HTML layout (HarfBuzz complex-script shaping; ReportLab evaluated and rejected for Indic shaping) |
| OCR | Tesseract 5.4 (local, offline) via pytesseract + OpenCV preprocessing (Phase 4) |
| AI | Modular AI service with configurable provider (env var) |

## Functional Requirements

### Phase 1: Foundation and ATM Interface
- [x] Project folder structure (frontend + backend separated)
- [x] FastAPI backend with SQLite database
- [x] Session management (session ID, language, current step)
- [x] REST API endpoints: health, create session, set language, chat, get/delete session
- [x] Modular AI service with mock fallback
- [x] Centralized i18n system (English, Telugu, Hindi)
- [x] ATM kiosk visual design (navy, white, slate, gold palette)
- [x] Landing screen: language selection
- [x] Welcome chatbot screen in selected language
- [x] Persistent chatbot panel
- [x] Responsive, touchscreen-optimized layout
- [x] Navigation: home, restart, change language, help

### Phase 2: Banking Service Catalogue
- [x] 4 banking categories (Account, Cards & Cheque, Loans, Investments/Insurance/Wealth)
- [x] 59 banking services with prototype form numbers
- [x] Search and filtering functionality
- [x] Service-specific form numbers (ACC-001, KYC-001, CARD-001, LOAN-001, INV-001, etc.)
- [x] Help button with 7-part AI explanation per service
- [x] Eligibility and process information
- [x] Required documents with mandatory/optional/conditional classifications
- [x] Start Application workflow
- [x] Help modal with service details

### Phase 3: Document Requirement Engine
- [x] Centralized document configuration system (39 document definitions)
- [x] Document categories A-H (Identity, Address, Financial, Educational, Photo/Signature, Property/Asset, Business, Insurance/Investment)
- [x] Service-to-document mappings for all 59 services (145 mappings)
- [x] Mandatory/optional/conditional classifications
- [x] Conditional requirement rules with reasons
- [x] Accepted alternatives per document
- [x] Information extraction fields per document
- [x] Validation requirements per document
- [x] Multilingual document support (EN, TE, HI)
- [x] Dynamic document checklist interface
- [x] Document progress tracking
- [x] Backend API endpoints for document engine
- [x] Frontend components: DocumentChecklistPage, DocumentItem, DocumentProgress

### Phase 4: Camera Scanner and OCR
- [x] Camera access (MediaDevices API)
- [x] Image capture, preview, retake
- [x] Upload from device
- [x] Image cropping, rotation, enhancement
- [x] Blur and readability checks
- [x] OCR integration (Tesseract 5.4 chosen; PaddleOCR has no Python 3.13 Windows wheel)
- [x] Real OCR engine only (no fake OCR output; failing engines surface an "OCR unavailable" state)
- [x] Multilingual OCR (eng, hin, tel language data bundled)
- [x] Document classification (MATCH / MISMATCH / UNKNOWN; mismatch warns, never silently accepted)
- [x] Structured field extraction (per-document-type schemas; ~34 types, 131 fields)
- [x] Confidence-based validation (real engine confidences shown per field)
- [x] Null preservation (unread fields are null, never invented)
- [x] Extracted values preserved untranslated
- [x] Extraction review screen with confirm / edit / rescan
- [x] Customer confirmation workflow
- [x] Scan status lifecycle with valid transitions
- [x] Checklist status sync (UPLOADED / READABLE / NEEDS_RESCAN; mandatory never auto-N/A)
- [x] Sensitive identifier masking (Aadhaar, PAN, passport, account numbers)
- [x] No raw OCR text persisted; temp images auto-purged (cleanup + 6h expiry)
- [x] Multilingual scanning UI (EN, TE, HI)
- [x] Synthetic (watermarked) test fixtures only — no real identity documents
- [x] Automated test suite (54 tests, service layer + API)

### Phase 5: Automatic Form Filling (Intelligent Application Form Autofill)
- [x] Dynamic application form engine (reusable canonical field types for all 59 services — not 59 implementations)
- [x] Form schemas (per-category base schemas + per-service overrides; service form numbers from Phase 2)
- [x] OCR-to-form field mapping (registry of document-type → form-field rules incl. PAN/Aadhaar/salary slip/bank statement examples from the spec)
- [x] Missing field detection (MISSING status + warnings; customer can type values manually)
- [x] Cross-document conflict detection (CONFLICT status with every candidate preserved; never auto-picked)
- [x] Confidence thresholds (LOW_CONFIDENCE below 60; low-confidence values must be reviewed)
- [x] Field status display (AUTO_FILLED / LOW_CONFIDENCE / CONFLICT / MISSING / CUSTOMER_EDITED / CUSTOMER_CONFIRMED badges)
- [x] Editable forms (Edit Field / Accept Value / Clear Value / Review Source Document with scan preview / Save Progress / Continue)
- [x] Customer data confirmation (explicit per-field confirm + final review gate; nothing silently submitted)
- [x] Multilingual EN/TE/HI interface labels; extracted personal data preserved untranslated
- [x] Session ownership enforced on every endpoint; only masked values ever leave the OCR layer
- [x] Automated tests (backend: 73 in Phase 5 suite; frontend: 9 vitest unit tests; 2 Playwright E2E flows)

### Phase 6: Application PDF Generation and Document Export
- [x] PDF generation blocked until every populated field is customer-confirmed (409 gate with readable reason codes)
- [x] PDFs built exclusively from customer-confirmed data (populated-confirmed/edited fields printed exactly; blank fields printed as "not provided")
- [x] Professional template layout (A4, margins, headings, styled tables, typography, header band, page numbers)
- [x] Reusable generic template engine driven by the existing form/checklist configurations — one engine renders all 59 services
- [x] Reference number, prototype form number, generation date and customer-confirmation status printed on the PDF
- [x] Sections only where relevant: Applicant / Contact / Address / Account / Service-Specific Info, Uploaded Document Checklist, Customer Declarations, Customer Confirmation
- [x] Multi-page pagination without splitting table rows; repeated table headers on continuation pages; no orphaned section headings
- [x] Complete EN/TE/HI PDF versions with correct Unicode shaping (HarfBuzz: Devanagari matras/reph, Telugu vattu/subjoined forms) — visually verified, no missing-glyph boxes
- [x] Bundled Noto Sans + Noto Sans Devanagari + Noto Sans Telugu (SIL OFL); font subsetting via fontTools
- [x] Prominent "EDUCATIONAL PROTOTYPE — NOT AN OFFICIAL BANK DOCUMENT" banner on every page + disclaimers (no HDFC affiliation, not valid for transactions/KYC, nothing submitted)
- [x] No official bank logos, seals or signatures in the PDF; original prototype visual identity only
- [x] Frontend PDF export page (reference number, service, form number, generation status, completion info)
- [x] Actions: Generate / Preview (inline viewer) / Download / Print / Delete + Return to Application, with meaningful error messages (409 blocked / 403 unauthorized / 404 not found)
- [x] APIs: POST .../generate-pdf, GET .../pdf, GET .../pdf/status, DELETE .../pdf (all session-ownership enforced)
- [x] Controlled temp storage only (backend/generated_pdfs/{session}, no public/static PDF URL, no-store responses)
- [x] Automatic cleanup on session delete and 6-hour retention sweep
- [x] No sensitive information in logs
- [x] Automated tests (backend: 86 in the Phase 6 suite incl. EN/TE/HI, gating, disclaimers, ownership, cleanup; frontend: unit + Playwright E2E generate/preview/download flow)

### Phase 7: Multilingual AI Integration
- [x] AI chatbot integration
- [x] Context-aware responses
- [x] English/Telugu/Hindi support
- [x] Service-specific guidance
- [x] Document-scanning guidance
- [x] Error explanations
- [x] Conversational navigation

### Phase 8: Integration, Testing and Final Polish
- [x] End-to-end testing (16 test cases — E2E-01 … E2E-16 in `tests/test_phase8.py`, all passing; plus 11 service-mode audit checks)
- [x] Mobile and desktop browser testing (Playwright: mobile 390×844, tablet 820×1180, desktop; full kiosk journey E2E)
- [x] Bug fixes (3 real defects found by final testing and fixed: intent word-boundary matching; real-transaction regex coverage; fresh-session landing→home navigation lose persisted session)
- [x] Final polish (security/privacy audit in `tests/SECURITY_AUDIT.md`, single-origin deployment via `SERVE_FRONTEND_DIST`, README/PROGRESS/REQUIREMENTS finalized)

## Security Requirements

- [x] No real banking credentials collected
- [x] No OTP collection
- [x] No PIN or CVV collection
- [x] No real banking transactions
- [x] No real account creation
- [x] No actual KYC authentication
- [x] No storage of actual Aadhaar numbers
- [x] Temporary document storage only
- [x] Automatic cleanup after session
- [x] API keys stored in environment variables
- [x] Validate all uploaded files
- [x] Restrict file size and file types
- [x] Protect backend APIs
- [x] Avoid exposing extracted sensitive information in application logs

## Non-Functional Requirements

- [x] Responsive design (mobile and desktop)
- [x] Touch-friendly interface (ATM kiosk optimized)
- [x] Multilingual support (EN, TE, HI)
- [x] Centralized translation system
- [x] Configurable service catalogue
- [x] Configurable document requirements
- [x] Clear separation of concerns (business logic, AI, OCR, PDF)
- [x] Demonstration disclaimer on all outputs

## Deliverables

- Source code (frontend + backend)
- README.md with setup and execution instructions
- docs/PROGRESS.md with development progress
- docs/REQUIREMENTS.md with requirements tracking
