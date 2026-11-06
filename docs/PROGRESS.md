# Development Progress Tracker

## Phase 1 – Foundation and ATM Interface ✅ COMPLETE

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

**Testing:** All Phase 1 backend API endpoints tested and passing.

---

## Phase 2 – Banking Service Catalogue ✅ COMPLETE

**Features implemented:**
- Full banking service catalogue (all 4 categories, all specified services)
- Service-specific prototype form numbers (ACC-001, KYC-001, CARD-001, LOAN-001, INV-001, etc.)
- Configurable banking service data module (backend: `banking_services.py`)
- Search and filtering functionality (search by name/description, category filter)
- Help button with AI explanation (7-part detailed explanation per service)
- Eligibility and process information per service
- Required documents with mandatory/optional/conditional classifications
- Start Application workflow (API + session context update)
- Help modal with service details, documents, eligibility, estimated time
- Prototype form number notices on every service card
- 59 services across Categories A-D implemented

**Testing:** All Phase 2 backend API endpoints tested and passing.

---

## Phase 3 – Intelligent Document Requirement Engine ✅ COMPLETE

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
- Backend API endpoints:
  - GET /api/documents/catalogue
  - GET /api/documents/service/{service_id}
  - GET /api/documents/{document_id}
  - GET /api/documents/service/{service_id}/checklist
  - POST /api/documents/checklist/{application_id}/update
  - GET /api/documents/checklist/{application_id}/progress
- Frontend components:
  - DocumentChecklistPage - full document checklist view
  - DocumentItem - individual document with scan/help/retake
  - DocumentProgress - progress indicator with status summary
- Navigation from service catalogue to document checklist
- Document help modal with detailed explanations
- Checklist progress tracking (percentage, mandatory completion)

**Statistics:**
- Services mapped: 59
- Document definitions: 39
- Document mappings: 145
- Document categories: 8 (A-H)

**Testing:** All document engine backend API endpoints tested and passing.
TypeScript compilation: Zero errors.

---

## Phase 4 – Camera Scanner and Intelligent OCR Engine ✅ COMPLETE

**Features implemented:**
- Camera access via MediaDevices API with framing guides
- Image capture, preview, retake; upload from device
- Image preprocessing: resize, boundary detection, perspective + rotation correction, grayscale, denoising, CLAHE contrast, sharpening, adaptive thresholding
- Quality detection: blur (Laplacian variance), resolution, brightness/under/over-exposure, contrast, document boundary/rotation/cropping → GOOD / WARNING / POOR with customer-facing explanations
- OCR integration: **Tesseract 5.4** (local, offline) via pytesseract; provider isolated in a modular `ocr_engine.py`; language availability probed from `backend/tessdata/` (eng, hin, tel — tessdata_fast)
- Best-of-two OCR: enhanced-grayscale vs adaptive-threshold variants; higher real confidence wins
- Document classification: keyword evidence per doc type, checklist selection as primary context → MATCH / MISMATCH / UNKNOWN (mismatch warns, never silently accepted)
- Structured field extraction: per-document-type schemas (≈35 doc types), label-based + stacked-label matching, regexes for identifiers/dates/amounts; amounts require label context
- Real OCR confidence from Tesseract word outputs — no artificial scores; nulls never invented
- Extracted values preserved untranslated (script-preserving: EN/HI/TE prints stay as printed)
- Extraction review screen: field rows with confidence badges, tap-to-edit, confirm with corrections, or rescan
- Scan status lifecycle with valid transitions; checklist sync (UPLOADED/READABLE/NEEDS_RESCAN); mandatory docs never auto-marked N/A
- 11 scanner API endpoints under /api/scanner/*
- Security: sensitive identifiers masked before leaving the module, raw OCR text never persisted, temp images under backend/temp_scans purged on cleanup and 6-hour expiry
- Multilingual scanning UI strings in EN, TE, HI
- Checklist GET endpoint now overlays per-application statuses (`?application_id=`)

**Statistics:**
- OCR engine: Tesseract 5.4 (UB-Mannheim), 3 languages (eng, hin, tel)
- Document types with extraction schemas: 34
- Extractable fields across schemas: 131
- Scanner API endpoints: 11
- Automated tests: 54 (all passing)
- Synthetic test fixtures: 9 (PAN/Aadhaar EN+HI+TE, marksheet EN+TE, salary slip, GST, bank statement)

**Testing:** `python backend/tests/test_phase4.py` — 54/54 passing (service layer + HTTP API). TypeScript: zero errors; production build green.
**Important:** OCR-based recognition is contextual document *reading* only. The system never claims to authenticate document genuineness (no KYC verification is performed).

---

## Phase 5 – Intelligent Application Form Autofill ✅ COMPLETE

**Plan (was):**
- Reuse Phase 2 service catalogue (59 services), Phase 3 checklist mappings, Phase 4 scan store + extraction schemas — no duplication.
- Reusable form configurations: canonical FORM_FIELD_TYPES (multilingual labels EN/TE/HI, validation, sensitive flags) + per-category SERVICE_FORM_SCHEMAS with per-service overrides (59 services without 59 implementations).
- OCR→form mapping registry: document field keys per doc type → canonical form fields (PAN name → Applicant Name; PAN identifier → PAN Number; salary net → Monthly Income; statement account holder → Account Holder Name; IFSC → IFSC Code, etc.).
- Autofill engine: aggregates confirmed/readable scans of the application's service; multi-document aggregation with conflict detection (same field, different values → CONFLICT + candidates, never an auto-pick); confidence threshold → LOW_CONFIDENCE; nothing invented → MISSING.
- Field statuses with visual indicators: AUTO_FILLED, LOW_CONFIDENCE, CONFLICT, MISSING, CUSTOMER_EDITED, CUSTOMER_CONFIRMED; low-confidence/conflict fields block Continue until reviewed.
- Form API: applications init, form, autofill, field-mappings, PATCH field, confirm fields, save, completion-status — all session-ownership validated; masked values only; no raw OCR sent anywhere; explicit customer confirmation before any "continue".
- Frontend: ApplicationFormPage (route /application/form), status badges, edit/accept/clear actions, review-source-document modal (scan preview), missing/conflict warnings, save/continue gating, i18n EN/TE/HI.
- Tests: backend/tests/test_phase5.py (mapping, population, conflicts, low-confidence, missing, editing, confirmation, persistence, ownership, i18n, 59-service integration); frontend form page lint/build + E2E smoke.

**Delivered:**
- `backend/app/services/form_engine.py` — canonical form field registry (34+ fields, EN/TE/HI labels, patterns, sensitive flags), per-category base schemas keyed by real service-id prefixes (acc/kyc/card/cheq/cash/dd/neft/rtgs/imps/loan/scheme/ins/inv), per-service overrides, `FIELD_MAPPINGS` registry (60+ rules across 24 document types incl. all spec examples), status model (`FIELD_STATUSES`, `LOW_CONFIDENCE_THRESHOLD=60`), prototype `validate_field_value` with i18n error keys.
- `backend/app/services/form_service.py` — application lifecycle (ensure/get/purge with reference numbers APP-XXXXXXXX), autofill harvest from eligible scans (confirmed/readable, same session AND service), normalized corroboration, CONFLICT candidate preservation, LOW_CONFIDENCE flagging, MISSING semantics, edit/clear/confirm/accept + bulk confirm (never overwrites customer decisions; explicit Clear persists), form view builder with prototype notice, completion status with warnings and ready_to_continue.
- `backend/app/api/form_routes.py` — 8 endpoints under /api/applications/* (init, form, autofill, field-mappings, PATCH field, fields/confirm, save, completion-status), session ownership enforced everywhere; validation errors surface as 422 with i18n keys; conflicts can only be resolved by an explicit customer action (409 otherwise).
- `backend/app/models.py` — Application gains `service_id` and `session_key` (indexed) columns; `backend/app/db/database.py` gains a lazy SQLite migration (ALTER TABLE on startup). Form state stored as JSON in the existing `application_data` column (no schema duplication).
- Session lifecycle: DELETE /api/session/{id} now also purges scans (incl. temp files) and applications; expired sessions immediately lose access (403/404).
- Phase 4 extension: BANK_STATEMENT extraction schema adds `ifsc` (RE_IFSC) so statements can feed IFSC Code per spec.
- Frontend: `ApplicationFormPage.tsx` (route `/application/form/:serviceId`; checklist now navigates with the service id), status badges (distinct colours + test ids), inline edit/Accept/Clear/Review-Source actions, conflict candidate chooser, missing/low-confidence/conflict warning banners, Save Progress toast, Continue gated behind a final-review modal with an explicit confirmation checkbox; Review-Source modal shows the real scan preview image.
- i18n: complete `form.*` section added to en.ts / te.ts / hi.ts (title, statuses, actions, warnings, final review, validation errors). Extracted personal values are never passed through t().

**Statistics:**
- Canonical form field types: 34 (all with EN/TE/HI labels)
- Services with generated forms: 59/59 (13 category schemas + overrides; verified non-empty for every service id)
- OCR→form mapping rules: 60+ across 24 document types
- New backend endpoints: 8
- Automated tests: backend 73/73 passing (test_phase5.py), Phase 4 regression 54/54, frontend vitest 9/9, Playwright E2E 2 flows, ESLint clean, production build green

**Testing:** `python tests/test_phase5.py` (service + API modes) — all passing; `python tests/test_phase4.py` — 54/54; `npx tsc --noEmit` — 0 errors; `npm run lint`, `npm test`, `npm run build`, `npx playwright test` — all green.

**Security notes:** only masked/structured values leave the OCR layer; form API returns identifiers only in masked form; the prototype rejects manual entry of full sensitive identifiers; nothing is ever submitted without the explicit final-review confirmation; no personal values are written to logs.

---

## Phase 6 – Application PDF Generation and Document Export ✅ COMPLETE

**Turns customer-reviewed application form data into professional multilingual PDFs — one generic template engine for all 59 services, strict customer-confirmation gating, prominent prototype disclaimers, controlled temporary storage.**

**Delivered:**
- `backend/app/services/pdf_engine.py` — the reusable template engine:
  - Built on **PyMuPDF 2.x Story/HTML layout with HarfBuzz complex-script shaping**. ReportLab was evaluated first and **rejected** (no OpenType shaping: Devanagari pre-base matras and conjuncts render in visually wrong order — verified at raster DPI). Reason documented in the module docstring.
  - Fonts: bundled Noto Sans + Noto Sans Devanagari + Noto Sans Telugu (Regular+Bold, hinted TTFs, SIL OFL) in `backend/fonts/`; `subset_fonts()` (fontTools) shrinks files to ~145–240 KB. Latin `liga/hlig/dlig` features are renamed to `ligaX` in cached derived copies (`backend/fonts/derived/`) so HarfBuzz stops emitting ligature glyphs — text extraction/search of plain ASCII words stays exact while every Indic shaping feature is untouched.
  - Block-based builder (`_build_blocks`): title + prototype banner, application-details meta table, then only the sections relevant to the service (Applicant / Contact / Address / Account / Service-Specific fields partitioned from the service's form config), Uploaded Document Checklist (reuses the Phase 3 checklist engine), Customer Declarations and Customer Confirmation.
  - Unbreakable layout chunks (≤6 table rows per block): rows never split across pages; the table header is re-injected when a continuation chunk lands at a page top; a section heading always travels with its first rows (no orphaned headings). `_measure()` pre-measures each block with the same Story engine; `insert_htmlbox` shrink-fallback retries disallow text shrinking.
  - `_draw_furniture()`: header band ("PROTOTYPE BANKING FORM", reference + service, prototype form number, "Page X of Y") and footer banner + generation date — original identity, no bank artifacts.
  - `generate_application_pdf()` re-checks the Phase 5 gate (`completion_status().pdf_ready`) and raises `PdfGenerationError(409, reason)` with human-readable messages (`PDF_READY_BLOCK_MESSAGES`); population of files under `backend/generated_pdfs/{session_key}/{reference}.pdf`; `pdf_info` (metadata only), `read_pdf_bytes`, `delete_pdf`, `purge_session`, `purge_expired` (6 h retention).
  - Localized chrome strings (`PDF_STRINGS`) complete in EN/TE/HI, including banner title/subtitle and the four compliance disclaimers.
- `backend/app/api/pdf_routes.py` — 4 endpoints (all session-owned): POST `.../generate-pdf`, GET `.../pdf` (inline, `no-store`), GET `.../pdf/status` (completion + file metadata, no content), DELETE `.../pdf`.
- `backend/app/api/routes.py` — DELETE `/api/session/{id}` now also purges the session's generated PDFs and runs the retention sweep.
- `backend/requirements.txt` — `pymupdf>=2.1.0`, `fonttools>=4.68.0` (with engine-choice comment).
- Frontend: `PdfExportPage.tsx` (route `/application/pdf/:serviceId`) — meta card (reference, form number, service, PDF status incl. Ready / Not generated / Blocked + blocking reason), completion info (missing fields printed as "not provided"), PDF language selector (EN/TE/HI), actions Generate (disabled by the gate) / Preview (inline iframe) / Download / Print / Delete / Return to Application; API layer gains `getPdfStatus`, `generatePdf`, `getPdfBlob`, `deletePdf` with status-aware error mapping (409 blocked / 403 unauthorized / 404 not found).
- `ApplicationFormPage.tsx` — "Confirm All Filled Fields" bulk action (records review decisions for every populated field; the PDF gate requires them); the final-review Proceed now records those confirmations and the done modal offers "Continue to PDF Export".
- i18n: complete `pdf.*` section plus `form.actions.confirmAll` / `form.continue.goPdf` in en.ts / te.ts / hi.ts.

**Statistics:**
- Generic template engine covering all 59 services (single implementation, config-driven)
- New backend endpoints: 4
- PDF languages: 3 (EN / TE / HI), complete localized chrome + disclaimers
- Fonts: 6 bundled Noto TTFs (+ 6 derived liga-stripped cache copies)
- File size: ~145–240 KB per PDF after subsetting; 2 pages for a typical savings-account application
- Automated tests: backend 86/86 (test_phase6.py, service + API modes), Phase 5 regression 73/73 (service + api), Phase 4 regression 54/54, Phase 2/3 endpoint smoke OK; frontend vitest 9/9, `tsc --noEmit` 0 errors, ESLint clean, production build green, Playwright E2E 4/4 (incl. real generate→preview→%PDF-download flow)

**Security notes:** generation gate enforced twice (service + engine); only customer-reviewed values are rendered; identifiers stay masked; PDFs live exclusively in controlled temp storage with no public/static URL and `no-store` download responses; files purge on session delete/expiry and via a 6-hour sweep; no serverside logs contain personal values; every page carries the educational-prototype banner and the four disclaimers (no HDFC affiliation, invalid for transactions, invalid for KYC, nothing submitted).

**Visual verification:** EN (page 1 + page 2), TE and HI PDFs rasterized and inspected — correct HarfBuzz shaping (Devanagari reph/pre-base matras/conjuncts, Telugu vattu subscripts), no missing-glyph boxes, professional layout, banner/disclaimers/page numbers all present. Sample rasters: `backend/generated_pdfs/preview_en.png`, `preview_te.png`, `preview_hi.png`.

**Known limitations (Phase 6 additions):**
- **Indic text extraction from the PDF is degraded**: TE/HI *rendering* is correct and verified, but MuPDF's ToUnicode table for shaped complex-script clusters only yields an approximation — searching/copying Telugu/Hindi strings inside the PDF finds garbled text. This is an inherent PyMuPDF limitation for shaped Indic runs; Latin text (all confirmed customer values, reference numbers, English GUI chrome) extracts exactly. Test suite asserts Indic codepoint presence + exact Latin values instead of Indic string search.
- Fields left blank are printed as "— not provided —" (allowed by the gate); they are not silently dropped, so the PDF shows the true form state.
- The PDF regeneration timestamp uses UTC; the header band carries the English-language "PROTOTYPE BANKING FORM" caption in all locales (localized UI headings are inside the body).
- `purge_expired` sweeps by file age inside session folders; a session folder is removed only when every file in it is expired.
- Print uses the browser print pipeline (iframe `contentWindow.print()` with a `window.open` fallback); print margins come from the browser, not the PDF engine.

---

## Phase 7 – Multilingual AI Integration (PENDING)
## Phase 8 – Integration, Testing and Final Polish (PENDING)

---

## Current Status

**Phase 6 (Application PDF Generation and Document Export) is complete and verified: backend 86/86, Phase 5 regression 73/73 (service + api), Phase 4 regression 54/54, Phase 2/3 smoke OK, frontend unit 9/9, Playwright E2E 4/4, ESLint clean, production build green, EN/TE/HI PDFs visually verified.** Waiting for approval before proceeding to Phase 7 (Multilingual AI Integration).

**Known limitations (Phase 6 additions):**
- Telugu/Hindi text inside generated PDFs is not text-searchable (shaped-cluster ToUnicode approximation in MuPDF); rendering itself is correct and customer values in Latin script extract exactly
- PDF generation requires the customer-confirmation gate (by design): all populated fields must be customer-confirmed/edited and at least one field confirmed
- PDFs are regenerated wholesale (no incremental edits); regeneration overwrites the session's stored file
- Print margins rely on the browser print pipeline
- Test suite checks Indic content by codepoint presence rather than string search (see extraction limitation above)

**Known limitations (Phase 5 additions):**
- Autofill reads only `readable`/`confirmed` scans of the *same service*; scans made for a different service never leak into another service's form (by design)
- Field validation is prototype-level (regex patterns); it is not real bank-form validation
- Conflict resolution requires the customer to pick one candidate or type a value — the system never guesses which document is "more official"
- Form state is stored per (session, service) as one draft row; multiple parallel drafts of the same service reuse the same row
- The final "Continue" intentionally does NOT submit anything — real submission remains later-phase work (PDF export is now a Phase 6 deliverable)
- The "Accept Value" flow is per-field; there is no bulk "Accept all" (deliberate, to force individual review)
- Legacy translations for some Telugu/Hindi interface strings use placeholder text in pre-existing spots (carried over from earlier phases)

**Phase 4 limitations remain:**
- Document checklist status is stored in-memory (not persisted to database yet); scan records persist masked metadata in SQLite
- README/docs translations for some Telugu/Hindi interface strings use placeholder text in some pre-existing spots
- Handwriting, low-quality prints, and heavily skewed photos OCR poorly; quality gate prompts a rescan
- Aadhaar in Hindi classifies UNKNOWN in some synthetic cases when print is noisy (reported honestly, neither accepted silently nor rejected)
- OCR confidence reflects engine word confidence, which is deliberately conservative on binarized text
- Camera access requires browser camera permission and a secure context (localhost/HTTPS)

---

## Phase 7 — Multilingual AI Integration ✅ COMPLETE

**A catalogue-grounded multilingual assistant over a configurable LLM provider abstraction. The kiosk never depends on an external AI service: with no provider configured (`AI_PROVIDER=mock`, the default) every answer is computed deterministically from the real Phase 2/3/5 data; a configured provider is consulted opportunistically with guardrailed prompts, and failures/timeouts/429s degrade silently to the deterministic answer.**

**Features implemented:**
- **AI provider abstraction (`ai_provider.py`)**: `AI_PROVIDER` of `mock | openai_compatible` (OpenAI Chat Completions shape, base URL + model from env), stdlib-`urllib` calls inside `asyncio.to_thread` (no new dependencies), per-call timeout (`AI_TIMEOUT_SECONDS`), bounded retries for transient errors only (never for 4xx), HTTP 429 cooldown window, `AIProviderError(detail, status, retryable)`, `health_ping()` + secret-free `status()`. Keys are server-side only and never exposed to the frontend. A deterministic test seam (`set_provider_for_testing`) powers all mocked-provider tests — no paid API calls in the suite.
- **Banking knowledge layer (`ai_knowledge.py`)**: intent keywords (greeting, list services, documents, eligibility, procedure, time, progress, PDF, autofill, scan-rejection, unavailable-fees) in EN/TE/HI; service matching (prototype form-number regex → verbatim catalogue name → curated aliases → token-overlap scoring, threshold-based) with the real catalogues as the only source of truth; 11-term neutral glossary admitted only for definitional questions (never over an explicitly mentioned prototype form number); grounded EN/TE/HI reply templates. All 4 categories and all 59 services are discoverable by name and by prototype form number.
- **Context-aware workflow assistance**: real document checklists (Phase 3 mappings, mandatory first), eligibility, procedures + form numbers, estimated time, application progress via the session's real Phase 5 completion status, PDF export guidance (names the Generate step), autofill guidance (directs to the form; the assistant never fills fields), scan-rejection explanations (checkable quality/checklist causes). Fees/rates/policy questions are answered "unavailable in this prototype" — never invented.
- **Multilingual conversation**: always replies in the SELECTED language; mixed-language/typo-tolerant; script detection (Telugu/Devanagari ranges) for transliterated input; explicit mid-session switching ("reply in telugu/hindi/english") flips the session language and answers in it; bounded conversation memory keeps follow-up context ("which documents?" after naming a service); names/addresses/account numbers/personal data are never translated.
- **Safety guardrails (`ai_safety.py`)**: input sanitisation masks PAN/Aadhaar/long-digit identifiers and OTP/secret phrases before any use (`[PAN-REDACTED]`, `[ID-REDACTED]`, `[NUMBER-REDACTED]`, `[SECRET-REDACTED]`); real-transaction/balance/withdrawal requests refused with a clear prototype explanation; PIN/CVV/OTP/password sharing warned without echoing the secret. Provider replies are validated before display (forbidden claims of account access/transactions/HDFC submission/doc verification, secret solicitation, injected identifiers, empty/overlong → deterministic fallback). No document images/raw OCR, no sensitive identifiers in any prompt; the assistant cannot modify fields, confirm documents, approve or generate PDFs — it only offers navigation actions.
- **Conversation architecture (`ai_conversation.py`)**: bounded in-memory store (40 messages), last-service/last-intent context, session purge on DELETE `/api/ai/conversation/{id}` (ownership via `X-Session-Id`, 403 otherwise) and on session delete.
- **Backend endpoints (`ai_routes.py`)**: POST `/api/ai/chat` (`{response, source, session_id, language, actions, suggestions}`, sources `assistant | provider | fallback | safety`), GET `/api/ai/health` (+ optional bounded `?probe=1` live ping), GET `/api/ai/suggestions`, DELETE `/api/ai/conversation/{session_id}`. Legacy Phase 1 POST `/api/chat` keeps its exact contract and delegates to the same engine.
- **Conversational UI (`ChatPanel.tsx`)**: suggestions chips, offer-only service navigation buttons ("Open {service}") that start the application on the customer's explicit tap, clear-chat button, localized typing indicator, clear error messages, bilingual welcome; kiosk design preserved; responsive split layout (chat full-width column below the catalogue on mobile/tablet); wired on both Home and the document checklist page.
- **i18n**: `chat.*` keys (typing, suggestions, clearChat, chatCleared, online) in en/te/hi with type-enforced key parity.

**Statistics:**
- New backend modules: 6 (`ai_provider`, `ai_safety`, `ai_knowledge`, `ai_conversation`, `ai_prompts`, `ai_routes` + engine rewrite of `ai.py`)
- New backend endpoints: 4 (+ legacy `/api/chat` delegation)
- AI provider kinds: 2 (`mock` default; `openai_compatible` over `AI_BASE_URL`/`AI_MODEL`)
- Guardrail rejection categories: 5 (empty, too_long, forbidden_claim, secret_solicitation, unsanitised_identifier); 4 sanitiser redaction classes
- Automated tests: backend 104/104 (test_phase7.py, service + API modes), Phase 5 regression 73/73, Phase 4 regression 54/54, Phase 6 regression 86/86, Phase 2/3 catalogue smoke OK; frontend vitest 15/15, `tsc --noEmit` 0 errors, ESLint clean, production build green, Playwright E2E 7/7 (3 new chat flows)

**Testing:** `python tests/test_phase4.py` → 54/54, `test_phase5.py` → 73/73, `test_phase6.py` → 86/86, `test_phase7.py` → 104/104; `npm test`, `npx tsc --noEmit`, `npm run build`, `npx playwright test` all green.

**Known limitations carried into the final phase:**
- Some Telugu document-name translations in the pre-existing Phase 3 document catalogue are corrupted/mixed-script (data-quality issue inherited from Phase 3; assistant replies quote them verbatim rather than invent corrections).
- Six prototype form numbers are duplicated across two services each (ACC-003…ACC-008; Phase 2 catalogue artifact); form-number lookup resolves deterministically to the lowest service id.
- Vocabulary/intent lists are curated keyword-phrase based (no embeddings); they are tolerant of common typos/mixing but not open-domain paraphrases.

---

## Phase 8 — Integration, Testing and Final Polish ✅ COMPLETE

**The final phase: every module from Phases 1–7 verified as one integrated system, two real engine defects found and fixed by end-to-end probing, a security/privacy audit, deployment configuration, final documentation, and acceptance testing. The deterministic backend remains the authority for all banking operations — including during deployment.**

**Features delivered:**
- **End-to-end integration suite (`backend/tests/test_phase8.py`, dual-mode)**: 11 service-mode checks (catalogue invariants, deterministic-authority verification against a hostile injected provider, prompt-mask audit through the real engine path, no API-key logging, built-bundle secret scan, live single-origin deployment probe, temp purge) + **16 numbered API E2E cases (`E2E-01…E2E-16`)** over the live server: full kiosk journey (session → application → checklist → scan → autofill → confirm → PDF gate → generate → `%PDF-` download), grounded progress, legacy contract, byte-stable determinism, transaction refusal, Telugu/Hindi script correctness, multi-language PDF export, checklist-grounded answers, scan-rejection help, autofill non-mutation, PDF guidance, no invented rates, 404/fallback handling, purge end-to-end, cross-session 403s, performance budgets, and concurrency/determinism/health.
- **Real engine fixes (found by the E2E suite)**: `match_intent` word-boundary keyword matching (greeting `"hi"` no longer matches inside `"which"`; Indic keywords keep plain containment) and `_REAL_TRANSACTION_RE` extended with currency/amount groups so `"transfer Rs 5000 …"` is refused. Full regression over Phases 4–7 re-run green after both fixes.
- **Real frontend fix (found in final manual QA)**: on a fresh browser, selecting a language on the landing page navigated to Home in the same React batch that created the session, so Home re-read `localStorage` before it was persisted and bounced straight back to the landing screen. `useSession` now persists the session synchronously before navigation (`createSession`/`setLanguage`); verified live end-to-end (landing → Home stays, session present) and re-verified the full battery (vitest/tsc/ESLint/Playwright/build).
- **Security & privacy audit** (`backend/tests/SECURITY_AUDIT.md`): provider trust boundary, prompt redaction evidence, no key logging, bundle secret scan, ownership enforcement, storage/retention cleanup, credentials checklist, deployment posture, residual limitations.
- **Session lifecycle & cleanup**: conversation + session delete purge verified end to end; temp scans purge on demand and expiry.
- **Responsive kiosk verification**: new Playwright spec `frontend/e2e/full-journey.spec.ts` — mobile 390×844 and tablet 820×1180: vertical stacking (`flex-col-reverse lg:flex-row`), both panels visible/interactive, no horizontal overflow.
- **Performance & reliability**: catalogue < 2 s, 8 AI answers < 12 s, 6 concurrent sessions byte-stable, health stable.
- **Deployment configuration**: `SERVE_FRONTEND_DIST=1` mounts the built `frontend/dist` from FastAPI itself — **single-origin production deployment, no CORS/reverse-proxy surface** (static files only; all banking operations remain in the deterministic backend). Documented in `.env.example` and README's deployment runbook (`npm run build` + uvicorn without `--reload`).
- **Final documentation**: README Phase 8 section + production deployment instructions; PROGRESS.md (this section); REQUIREMENTS.md Phase 8 checkboxes ticked.

**Statistics:**
- New backend test suite: `tests/test_phase8.py` (11 service checks + 16 E2E cases).
- E2E cases executed: **17/17 pass** (16 numbered cases + E2E-06b multi-language PDF sub-case).
- Real engine defects fixed by the phase: **2** (`ai_knowledge.match_intent`, `ai_safety._REAL_TRANSACTION_RE`) + **1 frontend defect** (`useSession` fresh-browser navigation, found in manual QA).
- Deployment settings added: 2 (`SERVE_FRONTEND_DIST`, `FRONTEND_DIST_PATH`) + app static mount on the FastAPI app.
- New frontend Playwright spec: `e2e/full-journey.spec.ts` (full journey + 2 responsive viewports).

**Testing:** backend: `test_phase8.py` **28/28** (service+API), regression `test_phase4.py` **54/54**, `test_phase5.py` **73/73**, `test_phase6.py` **86/86**, `test_phase7.py` **104/104** (all against a freshly restarted uvicorn so the fixes were live). Frontend: `npm test` **15/15**, `npx tsc --noEmit` **0 errors**, `npx eslint src --max-warnings=0` **clean**, `npm run build` **green**, `npx playwright test` **10/10**.

**Remaining known limitations (final, honest):**
- Assistant vocabulary/intent lists remain curated-keyword based; not open-domain NLU.
- The AI layer is an *advisory* layer only by design — there is no real submission, no real transaction execution, no real KYC verification (educational prototype scope).
- Prototype-level rate limiting / real secrets management / HTTPS kiosk hardening are out of scope (documented in `SECURITY_AUDIT.md` §6–7).
- All previously-carried limitations from Phases 4–7 remain listed in their sections above.
