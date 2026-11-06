# Security & Privacy Audit — Phase 8

**Project:** ATM AI Banking Assistant (educational prototype)
**Scope:** final integrated audit over Phases 1–7 outputs, executed in Phase 8.
**Method:** automated audit checks inside `backend/tests/test_phase8.py` (service mode) plus manual review of route/service sources. Evidence below cites the passing test names.

**Architectural decision underpinning everything below:** the **deterministic backend is the sole authority for all banking operations** — including during final integration and deployment. The AI assistant only ever *consults* a provider opportunistically; its output is validated before display and it can never create, modify, approve, confirm, reject, or submit anything.

## 1. AI provider trust boundary (PROMPT-INJECTION / hostle-output hardening)

| # | Finding | Evidence |
|---|---------|----------|
| 1.1 | A (fake) hostile provider reply claiming *"your savings account is opened and Rs 100000 transferred, please share your OTP"* is **rejected by output validation**; the deterministic catalogue answer is shown instead. | `Hostile provider reply is rejected (validation/safety wins)` |
| 1.2 | The assistant never claims completed banking, even under injection. | `AI never claims completed banking (deterministic authority)` |
| 1.3 | After detaching the hostile provider the engine returns pure catalogue answers — no state was mutated by the injection. | `Engine returns catalogue answer after provider detach` |
| 1.4 | Guardrail rejection categories: `empty`, `too_long`, `forbidden_claim`, `secret_solicitation`, `unsanitised_identifier` (verified in the Phase 7 suite, still green in Phase 8 regression). | Phase 7 suite 104/104 |

## 2. Privacy — sensitive data never reaches prompts, logs or the browser

| # | Finding | Evidence |
|---|---------|----------|
| 2.1 | PAN / Aadhaar / long-digit identifiers are masked (`[PAN-REDACTED]`, `[ID-REDACTED]`, `[NUMBER-REDACTED]`) **before** prompt assembly; OTP/secret phrases are masked and never echoed. Verified through the real engine path by capturing the prompt a provider would receive. | `Prompts mask PAN/Aadhaar/OTP before any provider call` |
| 2.2 | No document images or raw OCR text enter any prompt — only masked, summarised context. | `Prompts never embed images or raw OCR` |
| 2.3 | No AI service source logs or prints API keys. | `No API-key logging in AI service sources` |
| 2.4 | API keys live only in server-side environment variables (`.env`, see `.env.example`); nothing sensitive is bundled into the frontend build — the built `frontend/dist` JS was scanned with no `AI_API_KEY` strings or `sk-…`-shaped secrets found. | `Built frontend bundle contains no provider secrets` |
| 2.5 | PDFs contain only customer-confirmed values; identifiers remain masked on the PDF exactly as the customer confirmed them (Phase 6 gate verified again in regression). | Phase 6 suite 86/86 |

## 3. Session lifecycle, ownership and data cleanup

| # | Finding | Evidence |
|---|---------|----------|
| 3.1 | Every application/form/PDF/AI route enforces session ownership; cross-session access returns **403** across form, save, PDF and conversation routes. | `E2E-14 cross-session access refused (403) everywhere`; Phase 7 suite |
| 3.2 | Deleting the conversation (owner-header required, 403 without it) then the session makes both inaccessible — subsequent chat returns **404**. | `E2E-13 conversation + session delete purges access end to end` |
| 3.3 | Temporary scan images are stored only under `backend/temp_scans/` with retention/expiry; expired areas purge on demand (`purge_expired`) and on session cleanup/cleanup endpoints. | `Expired temp scans purge on demand`; Phase 4 suite 54/54 |
| 3.4 | Generated PDFs live only under `backend/generated_pdfs/{session}/` with no public URL, `no-store` responses, deletion on session delete and a 6-hour sweep. | Phase 6 suite (regression green) |
| 3.5 | Invalid service / application / chat-session references return **404**, never leak details; unsupported language codes fall back to deterministic `en`. | `E2E-12` |

## 4. Secrets and credentials checklist

- [x] All provider configuration via environment (`AI_PROVIDER`, `AI_API_KEY`, `AI_BASE_URL`, `AI_MODEL`); documented in `backend/.env.example`; `dev-secret` defaults are prototype-only and not used for anything security-relevant.
- [x] No API keys in frontend source or built bundle (scan: pass).
- [x] No API keys or sensitive identifiers in logs (`ai_safety.py` logs category codes only).
- [x] `.env` is git-ignored; only `.env.example` (empty values) is committed.
- [x] Test secrets are synthetic only; no real credentials, OTPs, PINs, CVVs anywhere in tests (all fixtures watermarked *SYNTHETIC TEST DOCUMENT*).

## 5. Real-transaction / fraud-surface refusal

| # | Finding | Evidence |
|---|---------|----------|
| 5.1 | Actual money-movement requests ("transfer Rs 5000 to account 123456 now") are classified and refused with a clear prototype explanation across the integrated stack. (Phase 8 **fixed** the regex gap here.) | `E2E-05 real-transaction request refused across integration` |
| 5.2 | PIN/OTP/CVV/password typed into chat is warned about without echoing the secret. | Phase 7 suite (regression green) |
| 5.3 | Fee/interest-rate questions are answered "unavailable in this prototype" — the assistant never invents numbers. | `E2E-11` |

## 6. Deployment posture

- Single-origin serving via `SERVE_FRONTEND_DIST=1` (`frontend/dist` mounted by FastAPI; no CORS surface in production mode). Verified live by the Phase 8 probe server: UI served from `/`, `/api/*` routes unshadowed. Evidence: `Single-origin deployment serves built kiosk UI`, `Static mount does not shadow /api routes`.
- `--reload` disabled in production runbook; uvicorn run from `backend/` with environment config only.
- HTTPS termination, kiosk device hardening and a real secrets manager belong to the customer's production infrastructure and are out of scope for this educational prototype.

## 7. Residual limitations (honest disclosure)

- The prototype stores prototype-level "secret key" defaults and no rate limiting/brute-force protection on API routes — acceptable for a single-kiosk educational prototype, not for production banking.
- Conversation memory is in-process (bounded); a multi-worker deployment would need an external store for shared conversation state.
- OCR masking protects against pipelines consuming it, but the prototype does accept fingerprints of scanned synthetic docs into SQLite as masked metadata only.
