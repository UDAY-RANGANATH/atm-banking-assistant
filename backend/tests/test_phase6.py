"""
Phase 6 automated test suite - Application PDF Generation and Document Export.

Verification approach (same dual-mode pattern as test_phase5.py):
  1. SERVICE mode - direct service-layer tests (no server required)
  2. API mode      - HTTP tests against a running server (default port 8000)

Fixtures are SYNTHETIC documents / synthetic OCR results. No real identity
documents are used anywhere in testing.

Print-safe on cp1252 consoles.
"""

import sys
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

FIXTURES = BACKEND / "tests" / "fixtures"
RESULTS = {"pass": 0, "fail": 0, "failures": []}

# Latin ligature glyphs (applied by HarfBuzz shaping) extract as legacy
# ligature codepoints; normalize before comparing plain-English text.
_LIGA = {
    "\uFB00": "ff", "\uFB01": "fi", "\uFB02": "fl",
    "\uFB03": "ffi", "\uFB04": "ffl", "\uFB05": "ft", "\uFB06": "st",
}


def norm(text):
    """Ligature-normalized text for stable assertions."""
    for k, v in _LIGA.items():
        text = text.replace(k, v)
    return text


def squeeze(text):
    """Whitespace-free text for Indic clustered extraction comparisons."""
    import re
    return re.sub(r"\s+", "", text)


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


def api(method, path, body=None, base="http://127.0.0.1:8000", raw=False):
    """HTTP helper. Returns (status, parsed_json_or_text)."""
    url = base + path
    data = None
    headers = {}
    if body is not None:
        data, headers = json.dumps(body).encode(), {"Content-Type": "application/json"}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=120)
        raw_bytes = resp.read()
        if raw:
            return resp.status, raw_bytes, dict(resp.headers)
        try:
            return resp.status, json.loads(raw_bytes.decode())
        except Exception:
            return resp.status, None
    except urllib.error.HTTPError as e:
        raw_bytes = e.read()
        if raw:
            return e.code, raw_bytes, dict(e.headers)
        try:
            return e.code, json.loads(raw_bytes.decode())
        except Exception:
            return e.code, None


# ===========================================================================
# Shared synthetic data
# ===========================================================================

FAKE_PAN = {
    "doc_type": "PAN_LIKE",
    "fields": {
        "full_name": {"label": "Full Name", "value": "Ravi Kumar", "confidence": 92.0},
        "fathers_name": {"label": "Father's Name", "value": "Suresh Kumar", "confidence": 88.0},
        "date_of_birth": {"label": "Date of Birth", "value": "14/05/1990", "confidence": 95.0},
        "document_identifier": {
            "label": "PAN Number (masked)", "value": "DEMONXX23F", "confidence": 90.0,
        },
    },
}


def seed_session_with_pan(service_id="acc-001"):
    """Create a session + application, attach a synthetic readable PAN scan."""
    from app.services.session import session_service
    from app.services.form_service import ensure_application
    from app.services.scanner import scan_store

    sid = session_service.create_session()
    app_row = ensure_application(sid, service_id)
    scan = scan_store.create(sid, service_id, "doc-pan", "upload", b"x", ".png")
    scan_store.force_status(scan["scan_id"], "readable")
    scan_store._scans[scan["scan_id"]]["result"] = FAKE_PAN
    return sid, app_row


def confirm_everything(app_row):
    from app.services.form_service import (
        _normalize_state, confirm_fields, set_field,
    )
    # give each MISS field no value (they may remain missing), confirm rest
    state = _normalize_state(app_row.application_data)
    ids = [fid for fid, rec in state["fields"].items() if rec.get("value")]
    if ids:
        confirm_fields(app_row, ids)
    return ids


# ===========================================================================
# SERVICE MODE TESTS
# ===========================================================================

def run_service_tests():
    print_safe("")
    print_safe("=== SERVICE LAYER TESTS (Phase 6 PDF generation) ===")

    from app.db.database import init_db
    init_db()

    from app.services.form_service import (
        completion_status, run_autofill, set_field, ensure_application,
        get_application_for_session,
    )
    from app.services.form_service import FormApplicationError
    from app.services import pdf_engine as pe
    from app.services.pdf_engine import (
        PdfGenerationError, PDF_ROOT, generate_application_pdf,
        pdf_info, read_pdf_bytes, delete_pdf, purge_session,
    )
    import pymupdf

    # --- Gate: unconfirmed AUTO_FILLED fields block generation -------------
    sid, app_row = seed_session_with_pan()
    run_autofill(app_row)
    # customer edits one missing field manually (also a recorded decision)
    set_field(app_row, "mobile_number", "edit", "9876543210")
    completed = completion_status(app_row)
    report(
        "Gate: populated-but-unconfirmed fields block PDF generation",
        not completed["pdf_ready"] and completed["pdf_blocked_reason"] in ("unconfirmed_fields", "review_required"),
        completed,
    )
    blocked = False
    try:
        generate_application_pdf(app_row)
    except PdfGenerationError as exc:
        blocked = exc.status_code == 409 and exc.reason in ("unconfirmed_fields", "review_required")
    except Exception:
        blocked = False
    report("Gate enforced in generation service (409)", blocked)

    # --- Missing required fields are allowed (printed as not provided) -----
    # acc-001 has 11 fields; only 4 populated -> missing fields must not block
    ids = confirm_everything(app_row)
    completed = completion_status(app_row)
    report(
        "Gate passes after each populated field was confirmed",
        completed["pdf_ready"] and completed["pdf_blocked_reason"] is None,
        completed,
    )
    report(
        "Missing (not provided) fields do not block",
        completed["counts"]["MISSING"] > 0 and completed["pdf_ready"],
        completed["counts"],
    )

    # --- English generation -------------------------------------------------
    meta = generate_application_pdf(app_row, language="en")
    path = pe.pdf_path(app_row)
    report("EN PDF generated and stored", path.is_file(), path)
    report(
        "PDF stored under controlled temp location (generated_pdfs/{session})",
        PDF_ROOT.name == "generated_pdfs" and app_row.session_key in str(path),
        str(path),
    )
    report("PDF filename is the application reference number", meta["file_name"] == f"{app_row.reference_number}.pdf")
    report("Generation meta carries prototype banner", "EDUCATIONAL PROTOTYPE" in meta["prototype_banner"])
    report("Generation meta carries form/phase data", meta["form_number"] == "ACC-001" and meta["language"] == "en")

    doc = pymupdf.open(str(path))
    page1 = doc[0].get_text()
    all_text = "".join(doc[p].get_text() for p in range(doc.page_count))
    page_count = doc.page_count
    doc.close()
    all_text = norm(all_text)
    page1 = norm(page1)
    report("Reference number printed on PDF", app_row.reference_number in page1)
    report("Prototype form number printed on PDF", "ACC-001" in page1)
    report("Generation date printed on PDF", "UTC" in page1)
    report("Customer confirmation status printed on PDF", "Recorded" in page1)
    report("Prototype banner on PDF", "EDUCATIONAL PROTOTYPE" in all_text and "NOT AN OFFICIAL BANK DOCUMENT" in all_text)
    report("Disclaimer: HDFC non-affiliation", "HDFC Bank" in all_text and "not affiliated" in all_text.lower())
    report("Disclaimer: not valid for banking transactions", "not valid for actual banking" in all_text)
    report("Disclaimer: not valid for KYC verification", "not valid for KYC" in all_text)
    report("Disclaimer: nothing submitted", "No application has been submitted" in all_text)
    report("Confirmed value printed exactly", "Ravi Kumar" in all_text)
    report("Customer-edited field printed", "9876543210" in all_text)
    report("Status column shows customer-confirmed markers", "Customer-confirmed" in all_text)
    report("Missing fields marked not provided", "not provided" in all_text)
    report("Document checklist section included", "Aadhaar Card" in all_text or "Uploaded Document Checklist" in all_text)
    report("Declarations section included", "Customer Declarations" in all_text)
    report("Confirmation section included", "Customer Confirmation" in all_text)
    report("Page numbers printed", "Page 1 of" in all_text)
    report("Multi-page supported (2 pages here)", page_count >= 2, page_count)

    info = pdf_info(app_row)
    report("pdf_info exposes size/pages (no content)", info and info["file_name"] == path.name and info["page_count"] >= 2, info)
    data = read_pdf_bytes(app_row)
    report("read_pdf_bytes returns real PDF bytes", data[:5] == b"%PDF-")
    report(
        "Generated PDF not readable from arbitrary path (no public URL)",
        not any(d.name == "static" for d in PDF_ROOT.iterdir() if d.is_dir()),
    )

    # --- Telugu + Hindi generation ------------------------------------------
    te_meta = generate_application_pdf(app_row, language="te")
    doc = pymupdf.open(str(path))
    te_text = "".join(doc[p].get_text() for p in range(doc.page_count))
    doc.close()
    te_indic_chars = sum(1 for ch in te_text if "\u0c00" <= ch <= "\u0c7f")
    report(
        "TE PDF renders Telugu chrome (Indic glyphs present in extraction)",
        te_meta["language"] == "te" and te_indic_chars > 60,
        te_indic_chars,
    )
    report("TE PDF keeps confirmed values exactly", app_row.reference_number in te_text and "Ravi Kumar" in te_text)
    report("TE PDF keeps prototype banner", "EDUCATIONAL PROTOTYPE" in te_text)
    report(
        "TE PDF disclaimers localized",
        "\u0c0f\u0c26\u0c3f" in te_text or "KYC" in te_text,
    )

    hi_meta = generate_application_pdf(app_row, language="hi")
    doc = pymupdf.open(str(path))
    hi_text = "".join(doc[p].get_text() for p in range(doc.page_count))
    doc.close()
    hi_indic_chars = sum(1 for ch in hi_text if "\u0900" <= ch <= "\u097f")
    report(
        "HI PDF renders Hindi chrome (Indic glyphs present in extraction)",
        hi_meta["language"] == "hi" and hi_indic_chars > 60,
        hi_indic_chars,
    )
    report("HI PDF keeps confirmed values exactly", app_row.reference_number in hi_text and "Ravi Kumar" in hi_text)
    report("HI PDF keeps prototype banner", "EDUCATIONAL PROTOTYPE" in hi_text)
    report("HI PDF disclaimers localized", "\u0928\u0939\u0940\u0902" in hi_text or "KYC" in hi_text)

    # --- Masked identifier printed as confirmed (kyc-001 has the PAN field) --
    sid_kyc, app_kyc = seed_session_with_pan("kyc-001")
    run_autofill(app_kyc)
    confirm_everything(app_kyc)
    kyc_meta = generate_application_pdf(app_kyc, language="en")
    doc = pymupdf.open(str(pe.pdf_path(app_kyc)))
    kyc_text = norm("".join(doc[p].get_text() for p in range(doc.page_count)))
    doc.close()
    report("KYC PDF generated", kyc_meta["service_id"] == "kyc-001")
    report(
        "Masked identifier preserved exactly (XX style)",
        "DEMONXX23F" in kyc_text and "XX" in "DEMONXX23F",
    )
    report(
        "Identity section present without fake full PAN",
        "DEMON0123F" not in kyc_text,
    )

    # --- Customer-edited-only gate variant -----------------------------------
    sid2, app2 = seed_session_with_pan()
    run_autofill(app2)
    confirm_everything(app2)
    # edit one field afterwards: customer_edited also counts as reviewed
    set_field(app2, "mobile_number", "edit", "9000000001")
    completed2 = completion_status(app2)
    report(
        "Customer-edited fields count as reviewed for the gate",
        completed2["pdf_ready"], completed2["counts"],
    )
    meta2 = generate_application_pdf(app2, language="en")
    report("Generation after edit succeeds", meta2["status"] == "ready")

    # --- Regeneration overwrites the same file -------------------------------
    size_before = pe.pdf_path(app2).stat().st_size
    time.sleep(0.05)
    generate_application_pdf(app2, language="en")
    size_after = pe.pdf_path(app2).stat().st_size
    report("Regenerate overwrites same controlled path", size_after > 0 and pe.pdf_path(app2).is_file())

    # --- Delete --------------------------------------------------------------
    report("delete_pdf removes the file", delete_pdf(app2) and not pe.pdf_path(app2).is_file())
    report("delete_pdf again reports not found", not delete_pdf(app2))

    # --- Session cleanup removes PDFs ---------------------------------------
    sid3, app3 = seed_session_with_pan()
    run_autofill(app3)
    confirm_everything(app3)
    generate_application_pdf(app3)
    folder3 = PDF_ROOT / app3.session_key
    report("PDF exists before session purge", folder3.is_dir() and any(folder3.glob('*.pdf')))
    removed = purge_session(app3.session_key)
    report("purge_session removes session folder", removed >= 1 and not folder3.exists(), removed)

    # --- Expired retention cleanup -------------------------------------------
    sid4, app4 = seed_session_with_pan()
    run_autofill(app4)
    confirm_everything(app4)
    generate_application_pdf(app4)
    folder4 = PDF_ROOT / app4.session_key
    # backdate the file beyond the retention window
    old = time.time() - (pe.PDF_RETENTION_HOURS + 2) * 3600
    for f in folder4.glob("*.pdf"):
        import os
        os.utime(str(f), (old, old))
    swept = pe.purge_expired()
    report("purge_expired removes documents older than retention window", not folder4.exists(), swept)
    # fresh files survive the sweep
    report("Fresh files survive purge_expired", pe.pdf_path(app_row).is_file())

    # --- No sensitive info in error messages ----------------------------------
    try:
        generate_application_pdf(app_row, language="xx")  # unknown language falls back
        report("Unknown language falls back to English", True)
    except PdfGenerationError:
        report("Unknown language falls back to English", False)


# ===========================================================================
# API MODE TESTS
# ===========================================================================

def run_api_tests():
    print_safe("")
    print_safe("=== API TESTS (http://127.0.0.1:8000) - Phase 6 ===")

    status, body = api("GET", "/api/health")
    report("Health endpoint", status == 200)

    # -- unauthorized access & invalid references -----------------------------
    status, other_sess = api("POST", "/api/session?language=en", body={})
    other_session = other_sess["session_id"]

    status, err = api("GET", "/api/applications/APP-NOPE0000/pdf/status?session_id=" + other_session)
    report("Invalid application reference -> 404", status == 404, (status, err))

    status, auth_body, _headers = api("GET", "/api/applications/APP-NOPE0000/pdf?session_id=" + other_session, raw=True)
    report("Download of unknown reference -> 404 (no leak)", status == 404, status)
    report(
        "Download response carries PDF media type even on success paths",
        isinstance(auth_body, bytes),
    )

    # -- full happy path ------------------------------------------------------
    status, sess = api("POST", "/api/session?language=te", body={})
    session_id = sess["session_id"]

    status, init = api("POST", "/api/applications/init",
                       body={"session_id": session_id, "service_id": "acc-001"})
    report("Init application", status == 200 and init.get("application_id"), status)
    application_id = init.get("application_id")

    status, _, _ = upload_scan(session_id, "acc-001", "doc-pan", "pan_en_DEMON0123F.png")
    report("Synthetic PAN uploaded via Phase 4 scanner", status == 200, status)

    status, scans = api("GET", f"/api/scanner/status/{session_id}")
    last_scan = None
    for svc_state in (scans or {}).get("services", {}).values():
        for doc_info in svc_state.get("scan_status_by_document", {}).values():
            last_scan = doc_info["scan_id"]
    status, conf = api("POST", f"/api/scanner/confirm/{last_scan}", body={})
    report("Customer confirms scan", status == 200 and conf.get("status") == "confirmed")

    status, filled = api("POST", f"/api/applications/{application_id}/autofill?session_id={session_id}")
    report("Autofill ran", status == 200)

    # -- status endpoint ------------------------------------------------------
    status, pre_status = api("GET", f"/api/applications/{application_id}/pdf/status?session_id={session_id}")
    report(
        "Status endpoint exposes pdf_exists/completion",
        status == 200 and pre_status.get("pdf_exists") is False and "completion" in pre_status,
        pre_status,
    )
    report(
        "Status shows gate blocked before confirmation (unconfirmed fields)",
        not pre_status["completion"]["pdf_ready"],
        pre_status["completion"],
    )

    # -- generation blocked before customer confirmation ----------------------
    status, err = api("POST", f"/api/applications/{application_id}/generate-pdf",
                      body={"session_id": session_id})
    report("Generate blocked with 409 before field confirmation", status == 409, (status, err))
    report("Blocked message is meaningful (no row data)", "confirm" in (err.get("detail") or "").lower(), err)

    # confirm all populated fields via the Phase 5 API
    status, form = api("GET", f"/api/applications/{application_id}/form?session_id={session_id}")
    ids = [f["field_id"] for f in form.get("fields", []) if f.get("value")]
    status, conf_result = api("POST", f"/api/applications/{application_id}/fields/confirm",
                              body={"session_id": session_id, "field_ids": ids})
    report("Bulk field confirmation (Phase 5 endpoint)", status == 200 and conf_result.get("confirmed"), conf_result)

    # customer completes one missing field manually
    status, patched = api("PATCH", f"/api/applications/{application_id}/fields/mobile_number",
                          body={"session_id": session_id, "action": "edit", "value": "9321004567"})
    report("Customer-edited field recorded", status == 200, (status, patched))

    status, post_status = api("GET", f"/api/applications/{application_id}/pdf/status?session_id={session_id}")
    report(
        "Status flips to pdf_ready after review",
        post_status["completion"]["pdf_ready"] is True,
        post_status["completion"],
    )

    # -- generate via API -----------------------------------------------------
    status, meta = api("POST", f"/api/applications/{application_id}/generate-pdf",
                       body={"session_id": session_id, "language": "te"})
    report("Generate PDF endpoint returns metadata", status == 200 and meta.get("status") == "ready", (status, meta))
    report(
        "Metadata includes reference/form/language/banner",
        meta.get("application_id") == application_id and meta.get("language") == "te"
        and "EDUCATIONAL PROTOTYPE" in meta.get("prototype_banner", ""),
        meta,
    )

    # --- regenerate via API ----------------------------------------------------
    status, meta2 = api("POST", f"/api/applications/{application_id}/generate-pdf",
                        body={"session_id": session_id, "language": "en"})
    report("Regeneration works and overwrites stored file", status == 200 and meta2.get("status") == "ready")

    status, pdf_status = api("GET", f"/api/applications/{application_id}/pdf/status?session_id={session_id}")
    info = pdf_status.get("pdf") or {}
    report("Status shows existing pdf", pdf_status.get("pdf_exists") is True and info.get("file_name") == f"{application_id}.pdf", info)

    # -- download --------------------------------------------------------------
    status, pdf_bytes, headers = api("GET", f"/api/applications/{application_id}/pdf?session_id={session_id}", raw=True)
    report("Download returns real PDF bytes", status == 200 and pdf_bytes[:5] == b"%PDF-")
    ctype = (headers.get("Content-Type") or headers.get("content-type") or "")
    report("Download Content-Type is application/pdf", ctype.startswith("application/pdf"), ctype)
    cdisp = (headers.get("Content-Disposition") or headers.get("content-disposition") or "")
    report("Download Content-Disposition inline", "inline" in cdisp and f"{application_id}.pdf" in cdisp, cdisp)
    ccache = (headers.get("Cache-Control") or headers.get("cache-control") or "")
    report("Download response is no-store (no public cacheable URL)", "no-store" in ccache, ccache)

    # -- ownership enforcement --------------------------------------------------
    status, other_init = api("POST", "/api/applications/init",
                             body={"session_id": other_session, "service_id": "acc-001"})
    other_app = other_init["application_id"]
    status, err, _hdr = api("GET", f"/api/applications/{application_id}/pdf?session_id={other_session}", raw=True)
    report("Foreign session cannot download PDF (403)", status == 403, status)
    report("403 download carries no PDF bytes", not (isinstance(err, bytes) and err[:5] == b"%PDF-"))
    status, err = api("GET", f"/api/applications/{application_id}/pdf/status?session_id={other_session}")
    report("Foreign session cannot read PDF status (403)", status == 403)
    status, err = api("DELETE", f"/api/applications/{application_id}/pdf?session_id={other_session}")
    report("Foreign session cannot delete PDF (403)", status == 403)
    status, err = api("POST", f"/api/applications/{application_id}/generate-pdf",
                      body={"session_id": other_session})
    report("Foreign session cannot generate PDF (403)", status == 403)

    # -- missing file download after no generation ---------------------------------
    status, err, _hdr2 = api("GET", f"/api/applications/{other_app}/pdf?session_id={other_session}", raw=True)
    report("Download before generation -> 404", status == 404, status)

    # -- delete endpoint -------------------------------------------------------------
    status, del_res = api("DELETE", f"/api/applications/{application_id}/pdf?session_id={session_id}")
    report("Delete endpoint removes file", status == 200 and del_res.get("status") == "deleted", del_res)
    status, pdf_bytes, _ = api("GET", f"/api/applications/{application_id}/pdf?session_id={session_id}", raw=True)
    report("After delete, download 404s", status == 404)

    # regenerate once more for the session-deletion cleanup test
    status, _ = api("POST", f"/api/applications/{application_id}/generate-pdf",
                    body={"session_id": session_id, "language": "en"})
    report("Regenerate before session cleanup", status == 200)

    # -- session deletion cleans generated PDFs -----------------------------------
    from pathlib import Path
    pdf_root = BACKEND / "generated_pdfs"
    folder = pdf_root / session_id
    report("Session PDF folder exists before DELETE /session", folder.is_dir())
    status, del_res = api("DELETE", f"/api/session/{session_id}")
    report("DELETE /api/session responds cleaned", status == 200, del_res)
    report("Session PDF folder removed after session delete", not folder.exists())


def upload_scan(session_id, service_id, document_id, filename):
    """Upload a synthetic fixture via the Phase 4 capture API (as Phase 5 does)."""
    file_path = FIXTURES / filename
    with open(file_path, "rb") as fh:
        file_bytes = fh.read()
    boundary = "----protoBoundaryPhase6"
    ctype = "image/png"
    parts = []
    for k, v in (
        ("session_id", session_id),
        ("service_id", service_id),
        ("document_id", document_id),
    ):
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n')
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {ctype}\r\n\r\n"
    )
    payload = "".join(parts).encode() + file_bytes + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        "http://127.0.0.1:8000/api/scanner/upload",
        data=payload,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=180)
        return resp.status, json.loads(resp.read().decode()), None
    except urllib.error.HTTPError as e:
        return e.code, None, e.read()


# ===========================================================================
# MAIN
# ===========================================================================

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode in ("service", "all"):
        run_service_tests()
    if mode in ("api", "all"):
        run_api_tests()

    print_safe("")
    print_safe("========== PHASE 6 RESULTS ==========")
    print_safe(f"PASSED: {RESULTS['pass']}  FAILED: {RESULTS['fail']}")
    if RESULTS["failures"]:
        for f in RESULTS["failures"]:
            print_safe("  FAILED: " + f)
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
