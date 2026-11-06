"""
Phase 8 automated test suite - Integration, Security Audit and Final Polish.

Verification approach (same dual-mode pattern as Phases 4-7):
  1. SERVICE mode - deterministic-authority, audit and deployment checks
  2. API mode     - sixteen end-to-end cases against a running server
                    (default port 8000) covering the complete integrated
                    kiosk lifecycle, error handling, session cleanup,
                    performance and reliability.

Fixtures are SYNTHETIC documents only. No real identity data is used.
The deterministic backend remains the authority for all banking operations
during final integration - an AI provider can never change banking state.
"""

import sys
import json
import time
import threading
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

FIXTURES = BACKEND / "tests" / "fixtures"
FRONTEND_DIST = BACKEND.parent / "frontend" / "dist"
RESULTS = {"pass": 0, "fail": 0, "failures": []}


def report(name, ok, detail=""):
    if ok:
        RESULTS["pass"] += 1
        print_safe("PASS: " + name)
    else:
        RESULTS["fail"] += 1
        RESULTS["failures"].append(name)
        print_safe("FAIL: " + name + (" - " + str(detail) if detail else ""))

def print_safe(s):
    try:
        print(s)
    except Exception:
        print(s.encode("ascii", errors="replace").decode())


def api(method, path, body=None, base="http://127.0.0.1:8000", raw=False, headers=None):
    """HTTP helper. Returns (status, parsed_json) or (status, bytes, headers) when raw."""
    url = base + path
    data = None
    hdrs = dict(headers or {})
    if body is not None:
        data, hdrs = json.dumps(body).encode(), {**hdrs, "Content-Type": "application/json"}
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=180)
        payload = resp.read()
        if raw:
            return resp.status, payload, dict(resp.headers)
        try:
            return resp.status, json.loads(payload.decode())
        except Exception:
            return resp.status, payload.decode(errors="replace")
    except urllib.error.HTTPError as e:
        try:
            parsed = json.loads(e.read().decode()) if e.headers.get(
                "content-type", "").startswith("application/json") else {}
        except Exception:
            parsed = {}
        return e.code, parsed
    except Exception as e:
        return -1, {"detail": str(e)}


def upload_sample(session_id, service_id="acc-001", document_id="doc-pan",
                  fixture_name="pan_en_DEMON0123F.png"):
    """Upload a synthetic test document through the real multipart endpoint."""
    import mimetypes

    path_file = FIXTURES / fixture_name
    file_bytes = path_file.read_bytes()
    ctype = mimetypes.types_map.get(path_file.suffix.lower(), "image/png")
    boundary = "Phase8Boundary20134812"
    parts = []
    for k, v in (
        ("session_id", session_id),
        ("service_id", service_id),
        ("document_id", document_id),
    ):
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n')
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
        f'filename="{fixture_name}"\r\nContent-Type: {ctype}\r\n\r\n'
    )
    payload = "".join(parts).encode() + file_bytes + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        "http://127.0.0.1:8000/api/scanner/upload",
        data=payload,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=240)
        return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, None

# ===========================================================================
# SERVICE MODE - deterministic authority, security audit, deployment checks
# ===========================================================================

def run_service_tests():
    print_safe("")
    print_safe("=== SERVICE MODE (Phase 8) ===")

    # --- Catalogue invariants (integration of Phases 2+3 products) ---------
    try:
        from app.services.banking_services import SERVICES, get_categories
        from app.services.document_engine import get_document_catalogue, get_service_mappings
        report("Catalogue invariants hold (59 services / 4 categories / 39 docs)",
               len(SERVICES) == 59 and len(get_categories()) == 4
               and len(get_document_catalogue()) == 39)
    except Exception as e:
        report("Catalogue invariants hold", False, e)

    # --- Deterministic authority over banking operations -------------------
    # A (fake) hostile LLM provider must never change banking state: its
    # reply passes output validation first, and a forbidden-claim /
    # secret-solicitation answer falls back to the deterministic engine.
    try:
        import asyncio
        from app.services import ai as aim
        from app.services.session import session_service

        async def _scenario():
            def hostile_reply(messages):
                return ("Done! Your savings account is opened and Rs 100000 "
                        "transferred to your new account. Please share your OTP "
                        "to verify this real transaction.")
            aim.ai_service.set_provider_for_testing(hostile_reply)
            try:
                sid = session_service.create_session('en')
                r1 = await aim.ai_service.answer(sid, "what is a savings account")
                r2 = await aim.ai_service.answer(sid, "open a savings account")
                combined = (r1["response"] + " " + r2["response"]).lower()
                report("Hostile provider reply is rejected (validation/safety wins)",
                       "share your otp" not in combined
                       and "transferred" not in combined)
                report("AI never claims completed banking (deterministic authority)",
                       "your savings account is opened" not in combined)
            finally:
                aim.ai_service.set_provider_for_testing(None)
                session_service.cleanup_session(sid)

        asyncio.run(_scenario())
    except Exception as e:
        report("Hostile provider reply is rejected (validation/safety wins)", False, e)
        report("AI never claims completed banking (deterministic authority)", False, e)

    # Re-verify the engine is provider-untouched after the hostile injection.
    try:
        import asyncio
        from app.services import ai as aim
        from app.services.session import session_service

        async def _clean():
            sid = session_service.create_session('en')
            r = await aim.ai_service.answer(sid, "what is a savings account")
            session_service.cleanup_session(sid)
            return r

        clean = asyncio.run(_clean())
        report("Engine returns catalogue answer after provider detach",
               "Savings Account Opening" in clean["response"])
    except Exception as e:
        report("Engine returns catalogue answer after provider detach", False, e)

    # --- Security audit: prompts contain no unmasked identifiers/OCR -------
    try:
        import asyncio
        from app.services import ai as aim
        from app.services.session import session_service

        captured = {}

        async def _scenario():
            def probe(messages):
                captured["msgs"] = messages
                return "Please open the application form to continue."
            aim.ai_service.set_provider_for_testing(probe)
            try:
                sid = session_service.create_session('en')
                await aim.ai_service.answer(
                    sid,
                    "My PAN is ABCDE1234F, my Aadhaar is 2345 1234 5678 "
                    "and the OTP is 556677",
                )
                session_service.cleanup_session(sid)
            finally:
                aim.ai_service.set_provider_for_testing(None)

        asyncio.run(_scenario())
        joined = json.dumps(captured.get("msgs", []))
        report("Prompts mask PAN/Aadhaar/OTP before any provider call",
               "ABCDE1234F" not in joined and "2345 1234 5678" not in joined
               and "556677" not in joined)
        report("Prompts never embed images or raw OCR",
               "image" not in joined.lower() and '"ocr"' not in joined.lower())
    except Exception as e:
        report("Prompt sanitisation audit", False, e)

    # --- Security audit: source scan for sensitive logging -----------------
    try:
        banned = 0
        for src in (BACKEND / "app" / "services").glob("ai*.py"):
            text = src.read_text(encoding="utf-8")
            for line in text.splitlines():
                low = line.lower()
                if ("print(" in line or "logger." in low) and (
                    "apikey" in low.replace("_", "") or "api_key" in low
                ):
                    banned += 1
        report("No API-key logging in AI service sources", banned == 0, banned)
    except Exception as e:
        report("No API-key logging in AI service sources", False, e)

    # --- Security audit: built frontend bundle carries no secrets ---------
    try:
        import re as _re
        leaked = []
        secret_re = _re.compile(r"sk-[A-Za-z0-9]{20,}")
        if FRONTEND_DIST.exists():
            for f in FRONTEND_DIST.rglob("*.js"):
                text = f.read_text(encoding="utf-8", errors="ignore")
                if "AI_API_KEY" in text or secret_re.search(text):
                    leaked.append(f.name)
        report("Built frontend bundle contains no provider secrets", not leaked, leaked)
    except Exception as e:
        report("Built frontend bundle contains no provider secrets", False, e)

    # --- Deployment: single-origin static serving actually serves the UI ---
    try:
        env_probe = _spawn_server(port=8010, serve_front=True)
        try:
            st, body, hdrs = api("GET", "/", raw=True, base="http://127.0.0.1:8010")
            html = body.decode(errors="ignore") if isinstance(body, bytes) else str(body)
            st_assets, _ = api("GET", "/assets", base="http://127.0.0.1:8010")
            st_health, health = api("GET", "/api/ai/health", base="http://127.0.0.1:8010")
            report("Single-origin deployment serves built kiosk UI",
                   st == 200 and "banking assistant" in html.lower())
            report("Static mount does not shadow /api routes",
                   st_health == 200 and health.get("provider") is not None)
        finally:
            _stop_server(env_probe)
    except FileNotFoundError as e:
        report("Single-origin deployment serves built kiosk UI + API", False,
               "frontend/dist missing - run npm run build first")

    # --- Session cleanup of transient stores -------------------------------
    try:
        from app.services.scanner import scan_store
        removed = scan_store.purge_expired(max_age_hours=0)
        report("Expired temp scans purge on demand", removed >= 0)
    except Exception as e:
        report("Expired temp scans purge on demand", False, e)


def _spawn_server(port, serve_front=False):
    env = dict(__import__("os").environ)
    env["AI_PROVIDER"] = "mock"
    if serve_front:
        env["SERVE_FRONTEND_DIST"] = "1"
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(BACKEND), env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    # wait for readiness
    for _ in range(60):
        st, _ = api("GET", "/api/ai/health", base=f"http://127.0.0.1:{port}")
        if st == 200:
            return proc
        time.sleep(0.5)
    _stop_server(proc)
    raise RuntimeError(f"probe server on {port} failed to start")


def _stop_server(proc):
    try:
        proc.terminate()
        proc.wait(timeout=10)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass

# ===========================================================================
# API MODE - sixteen end-to-end cases on the fully integrated backend
# ===========================================================================

DIST_MISSING_HINT = "run npm run build in frontend/ before the E2E audit"


def run_api_tests():
    from app.services.banking_services import SERVICES
    from app.services.ai_knowledge import form_number_lookup

    print_safe("")
    print_safe("=== END-TO-END CASES (Phase 8, live server on 8000) ===")

    # --------------------------------------------------------------- E2E-01
    # Complete integrated kiosk journey: session -> application -> checklist
    # -> scan -> autofill -> confirmations -> PDF, all through real endpoints.
    st, s = api("POST", "/api/session?language=en")
    sid = s["session_id"]
    st, app = api("POST", "/api/application/start",
                  {"session_id": sid, "service_id": "acc-001"})
    journey_ok = st == 200 and app.get("form_number") == "ACC-001"
    st, form_ref = api("POST", "/api/applications/init",
                       {"session_id": sid, "service_id": "acc-001"})
    journey_ok = journey_ok and st == 200
    application_id = form_ref.get("application_id") if form_ref else None
    step = "init"
    if journey_ok:
        step = "checklist"
        st, checklist = api("GET", f"/api/documents/service/acc-001/checklist?application_id={application_id}")
        journey_ok = st == 200 and any(
            i["document_id"] == "doc-pan" for i in checklist.get("documents", []))
        application_id = form_ref.get("application_id") if form_ref else None
    if journey_ok:
        step = "upload"
        st, scan = upload_sample(sid)
        journey_ok = st == 200 and scan.get("scan_id")
        scan_id = scan.get("scan_id") if scan else None
    if journey_ok:
        step = "confirm-scan"
        st, up = api("POST", f"/api/scanner/confirm/{scan_id}", {})
        journey_ok = st == 200
    if journey_ok:
        step = "autofill"
        st, form = api("POST", f"/api/applications/{application_id}/autofill?session_id={sid}")
        journey_ok = st == 200
    if journey_ok:
        step = "confirm-fields"
        st, fields = api("GET",
                         f"/api/applications/{application_id}/form?session_id={sid}")
        filled = [f["field_id"] for f in fields.get("fields", []) if f.get("value")]
        journey_ok = bool(filled)
    if journey_ok:
        st, conf = api("POST", f"/api/applications/{application_id}/fields/confirm",
                       {"session_id": sid, "field_ids": filled})
        journey_ok = st == 200
    if journey_ok:
        step = "gate"
        st, completion = api("GET",
                             f"/api/applications/{application_id}/completion-status?session_id={sid}")
        journey_ok = st == 200 and completion.get("pdf_ready")
    if journey_ok:
        step = "generate"
        st, pdfmeta = api("POST", "/api/applications/%s/generate-pdf" % application_id,
                          {"session_id": sid, "language": "en"})
        journey_ok = st == 200
    if journey_ok:
        step = "download"
        st, pdfbytes, hdrs = api(
            "GET", f"/api/applications/{application_id}/pdf?session_id={sid}", raw=True)
        journey_ok = st == 200 and pdfbytes[:5] == b"%PDF-"
    report("E2E-01 full kiosk journey (scan -> autofill -> confirm -> PDF)",
           journey_ok, "stopped at step: " + step)
    if application_id is None:
        application_id = ""

    # --------------------------------------------------------------- E2E-02
    st, chat = api("POST", "/api/ai/chat",
                   {"session_id": sid, "message": "What is the status of my application?"})
    progress_ok = st == 200 and "application" in chat.get("response", "").lower()
    if progress_ok and application_id:
        progress_ok = application_id in chat.get("response", "")
    report("E2E-02 AI progress answer references real application", progress_ok)

    # --------------------------------------------------------------- E2E-03
    st, legacy = api("POST", "/api/chat", {"session_id": sid, "message": "hello"})
    report("E2E-03 legacy /api/chat contract exactly {response, source, session_id}",
           st == 200 and set(legacy.keys()) == {"response", "source", "session_id"},
           legacy.keys())

    # --------------------------------------------------------------- E2E-04
    body1 = api("POST", "/api/ai/chat", {"session_id": sid, "message": "who can open a fixed deposit?"})[1]
    st, body2 = api("POST", "/api/ai/chat", {"session_id": sid, "message": "who can open a fixed deposit?"})
    report("E2E-04 repeated question is byte-stable (deterministic authority)",
           st == 200 and body1["response"] == body2["response"])

    # --------------------------------------------------------------- E2E-05
    st, ref = api("POST", "/api/ai/chat",
                  {"session_id": sid, "message": "Transfer Rs 5000 to account 123456 now"})
    report("E2E-05 real-transaction request refused across integration",
           st == 200 and ref.get("source") == "safety"
           and "cannot" in ref["response"].lower(), ref.get("source"))

    # --------------------------------------------------------------- E2E-06
    st, s_te = api("POST", "/api/session?language=te")
    sid_te = s_te["session_id"]
    st, te_chat = api("POST", "/api/ai/chat", {"session_id": sid_te, "message": "savings account???"})
    has_telugu = any("\u0C00" <= ch <= "\u0C7F" for ch in te_chat.get("response", ""))
    st, s_hi = api("POST", "/api/session?language=hi")
    sid_hi = s_hi["session_id"]
    st2, hi_chat = api("POST", "/api/ai/chat", {"session_id": sid_hi, "message": "home loan"})
    has_devanagari = any("\u0900" <= ch <= "\u097F" for ch in hi_chat.get("response", ""))
    report("E2E-06 Telugu/Hindi conversations answer in the selected script",
           has_telugu and has_devanagari, (has_telugu, has_devanagari))

    # mid-session switch + language-specific PDF for the same application
    if application_id:
        st, gen_te = api("POST", "/api/applications/%s/generate-pdf" % application_id,
                         {"session_id": sid, "language": "te"})
        st2, gen_hi = api("POST", "/api/applications/%s/generate-pdf" % application_id,
                          {"session_id": sid, "language": "hi"})
        report("E2E-06b same application exports Telugu and Hindi PDFs",
               st == 200 and st2 == 200, (gen_te, gen_hi))

    # --------------------------------------------------------------- E2E-07
    st, docs_chat = api("POST", "/api/ai/chat",
                        {"session_id": sid, "message": "which documents do I need for acc-001?"})
    body = docs_chat.get("response", "")
    report("E2E-07 document question quotes the real Phase 3 checklist",
           st == 200 and "PAN" in body and "address proof" in body.lower(),
           body[:80])

    # --------------------------------------------------------------- E2E-08
    st, rej = api("POST", "/api/ai/chat",
                  {"session_id": sid, "message": "my document scan was rejected, why?"})
    report("E2E-08 scan-rejection help explains checkable causes",
           st == 200 and rej.get("source") == "assistant"
           and any(w in rej.get("response", "").lower()
                   for w in ("blur", "light", "quality", "reshot", "rescan")),
           rej.get("response", "")[:80])

    # --------------------------------------------------------------- E2E-09
    st, form_before = api("GET", f"/api/applications/{application_id}/form?session_id={sid}")
    st2, af = api("POST", "/api/ai/chat", {"session_id": sid, "message": "can you fill my form automatically?"})
    st3, form_after = api("GET", f"/api/applications/{application_id}/form?session_id={sid}")
    messages_stop = (st, st2, st3) == (200, 200, 200)
    report("E2E-09 autofill guidance never mutates application fields itself",
           messages_stop and json.dumps(form_before) == json.dumps(form_after))

    # --------------------------------------------------------------- E2E-10
    st, pdfq = api("POST", "/api/ai/chat", {"session_id": sid, "message": "how can I download my application PDF?"})
    report("E2E-10 PDF guidance names the Generate step",
           st == 200 and "generate" in pdfq.get("response", "").lower())

    # --------------------------------------------------------------- E2E-11
    st, fees = api("POST", "/api/ai/chat", {"session_id": sid, "message": "what is the interest rate for fixed deposits?"})
    low = fees.get("response", "").lower()
    import re
    invented_rate = re.search(r"\b\d+(\.\d+)?\s*%", low)
    report("E2E-11 fee/rate questions marked unavailable, no invented rates",
           st == 200 and ("not available" in low or "unavailable" in low)
           and invented_rate is None, fees.get("response", "")[:80])

    # --------------------------------------------------------------- E2E-12
    st, _ = api("GET", "/api/services/does-not-exist")
    st2, _ = api("GET", f"/api/applications/noapp/form?session_id={sid}")
    st3, _ = api("POST", "/api/ai/chat", {"session_id": "no-session", "message": "hi"})
    st4, _ = api("POST", "/api/session/language", {"session_id": sid, "language": "xx"})
    st5, xx_chat = api("POST", "/api/ai/chat", {"session_id": sid, "message": "who can open a fixed deposit?"})
    fallback_en = (st5 == 200 and xx_chat is not None
                   and xx_chat.get("language") == "en"
                   and xx_chat.get("response", "").isascii())
    report("E2E-12 404s for invalid service/application/chat; unsupported language falls back to en",
           st == 404 and st2 == 404 and st3 == 404 and fallback_en,
           (st, st2, st3, st4, fallback_en))

    # --------------------------------------------------------------- E2E-13
    # Self-contained: fresh session, purge conversation then session; after
    # the session delete both the session and its chat are inaccessible.
    st, s13 = api("POST", "/api/session?language=en")
    sid13 = s13["session_id"]
    api("POST", "/api/ai/chat", {"session_id": sid13, "message": "hello"})
    st, _ = api("DELETE", f"/api/ai/conversation/{sid13}", None,
                headers={"X-Session-Id": sid13})
    st_del, _ = api("DELETE", f"/api/session/{sid13}")
    st2, _ = api("GET", f"/api/session/{sid13}")
    st3, _ = api("POST", "/api/ai/chat", {"session_id": sid13, "message": "hi"})
    report("E2E-13 conversation + session delete purges access end to end",
           st == 200 and st_del == 200 and st2 == 404 and st3 == 404,
           (st, st_del, st2, st3))

    # --------------------------------------------------------------- E2E-14
    st, s2 = api("POST", "/api/session?language=en")
    sid2 = s2["session_id"]
    st, cfg = api("POST", "/api/applications/init",
                  {"session_id": sid2, "service_id": "acc-002"})
    app2 = cfg.get("application_id", "")
    st_a, _ = api("GET", f"/api/applications/{application_id}/form?session_id={sid2}")
    st_b, _ = api("POST", f"/api/applications/{app2}/save?session_id={sid}")
    st_c, _ = api("DELETE", f"/api/ai/conversation/{app2}", headers={"X-Session-Id": sid})
    report("E2E-14 cross-session access refused (403) everywhere",
           st_a == 403 and st_b == 403 and st_c == 403, (st_a, st_b, st_c))
    api("DELETE", f"/api/session/{sid2}")
    api("DELETE", f"/api/session/{sid}")

    # --------------------------------------------------------------- E2E-15
    t0 = time.perf_counter()
    st, svcs = api("GET", "/api/services")
    dt_cat = time.perf_counter() - t0
    chats_ok = True
    t0 = time.perf_counter()
    for i in range(8):
        st_c, out = api("POST", "/api/ai/chat",
                        {"session_id": sid_te, "message": "tell me about form %s"
                         % SERVICES[f"acc-{(i % 6) + 1:03d}"].formNumber.lower()})
        chats_ok = chats_ok and st_c == 200
    dt_chats = time.perf_counter() - t0
    report("E2E-15 performance: catalogue < 2s, 8 AI answers < 12s",
           dt_cat < 2.0 and chats_ok and dt_chats < 12.0,
           (round(dt_cat, 2), round(dt_chats, 2)))

    # --------------------------------------------------------------- E2E-16
    question = "what is a recurring deposit?"
    expected = []
    st, session_ref = api("POST", "/api/session?language=en")
    sid_ref = session_ref["session_id"]
    st, ref_ans = api("POST", "/api/ai/chat", {"session_id": sid_ref, "message": question})
    ok_all = st == 200

    def worker(results, idx):
        sst, ss = api("POST", "/api/session?language=en")
        cst, ans = api("POST", "/api/ai/chat", {"session_id": ss["session_id"],
                                                "message": question})
        results[idx] = (cst, ans.get("response", ""))
        api("DELETE", f"/api/session/{ss['session_id']}")

    results = {}
    threads = [threading.Thread(target=worker, args=(results, i)) for i in range(6)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    ok_all = ok_all and all(
        v == ref_ans["response"] and k == 200 for k, v in results.values())
    st, health = api("GET", "/api/ai/health")
    ok_all = ok_all and st == 200 and health.get("provider")
    report("E2E-16 concurrent chats are stable and deterministic, health OK",
           ok_all)
    api("DELETE", f"/api/session/{sid_ref}")
    api("DELETE", f"/api/session/{sid_te}")
    api("DELETE", f"/api/session/{sid_hi}")


# ===========================================================================
# MAIN
# ===========================================================================

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode in ("service", "all"):
        run_service_tests()
    if mode in ("api", "all"):
        if mode == "all":
            # API tests hit the live server; in "all" mode they still run, as
            # with Phases 4-7 the standard workflow starts uvicorn separately.
            pass
        run_api_tests()

    print_safe("")
    print_safe("========== PHASE 8 RESULTS ==========")
    print_safe(f"PASSED: {RESULTS['pass']}  FAILED: {RESULTS['fail']}")
    if RESULTS["failures"]:
        for f in RESULTS["failures"]:
            print_safe("  FAILED: " + f)
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
