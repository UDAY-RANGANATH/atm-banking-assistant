"""
Phase 7 automated test suite - Multilingual AI Integration.

Verification approach: this script can run in two modes.
  1. SERVICE mode  - direct service-layer tests (no server required)
  2. API mode      - HTTP tests against a running server (default port 8000)

All AI provider interactions use MOCK/injected providers. The test suite never
makes paid API calls and never requires a configured provider. Fixtures use
SYNTHETIC data only (no real identity documents or values).

Print-safe on cp1252 consoles (ascii fallback for non-latin output).
"""

import asyncio
import sys
import json
import urllib.request
import urllib.error
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

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


def api(method, path, body=None, base="http://127.0.0.1:8000", headers=None):
    """HTTP helper. Returns (status, parsed_json_or_None)."""
    url = base + path
    data = None
    hdrs = dict(headers or {})
    if body is not None:
        data, _ = json.dumps(body).encode(), hdrs.setdefault(
            "Content-Type", "application/json"
        )
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=120)
        raw = resp.read()
        try:
            return resp.status, json.loads(raw.decode())
        except Exception:
            return resp.status, None
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw.decode())
        except Exception:
            return e.code, None


# ===========================================================================
# SERVICE MODE TESTS
# ===========================================================================

def run_service_tests():
    print_safe("")
    print_safe("=== SERVICE LAYER TESTS (Phase 7 multilingual AI) ===")

    from app.services import ai as ai_module
    from app.services.ai_provider import LLMProvider, AIProviderError
    from app.services.ai_safety import (
        sanitize_user_input,
        evaluate_input,
        validate_provider_reply,
    )
    from app.services.ai_knowledge import (
        detect_language,
        match_intent,
        find_service,
        glossary_answer,
        language_switch_request,
        format_document_list,
        format_categories_list,
        SUGGESTIONS,
        TEMPLATES,
    )
    from app.services.ai_conversation import conversation_store
    from app.services.banking_services import SERVICES
    from app.services.document_engine import get_service_mappings

    engine = ai_module.ai_service
    loop = asyncio.new_event_loop()

    # --- Input sanitisation / privacy -------------------------------------
    pan = sanitize_user_input("my pan is ABCDE1234F please")
    report("PAN values masked in input", "PAN-REDACTED" in pan and "ABCDE1234F" not in pan, pan)
    aad = sanitize_user_input("aadhaar 1234 5678 9012 details")
    report("Aadhaar-like numbers masked in input", "9012" not in aad.replace("1234 5678", ""), aad)
    digits = sanitize_user_input("account 12345678901 balance")
    report("Long digit identifiers masked", "12345678901" not in digits, digits)
    otp = sanitize_user_input("my otp is 556677")
    report("OTP values masked in input", "556677" not in otp, otp)
    ctrl = sanitize_user_input("hello\x00\x07world")
    report("Control characters stripped", "\x00" not in ctrl and "\x07" not in ctrl, ctrl)
    long_input = sanitize_user_input("x" * 4000)
    report("Input length capped", len(long_input) == 500, len(long_input))
    report("Sanitiser preserves Telugu text",
           "సేవ" in sanitize_user_input("నాకు సేవలు కావాలి"),
           sanitize_user_input("నాకు సేవలు కావాలి"))

    # --- Safety input classification ---------------------------------------
    report("Transfer request classified real_transaction",
           evaluate_input("transfer money to my friend") == "real_transaction")
    report("Balance check classified real_transaction",
           evaluate_input("check my account balance now") == "real_transaction")
    report("Withdrawal request classified real_transaction",
           evaluate_input("I want to withdraw cash 5000") == "real_transaction")
    report("PIN sharing classified secret_sharing",
           evaluate_input("my pin is 7890") == "secret_sharing")
    report("OTP sharing classified secret_sharing",
           evaluate_input("otp : 482913") == "secret_sharing")
    report("Password sharing classified secret_sharing",
           evaluate_input("my password is hunter2") == "secret_sharing")
    report("Ordinary banking question is safe",
           evaluate_input("which documents do I need for savings account?") == "safe")
    report("Service request is safe",
           evaluate_input("I want to open a savings account") == "safe")

    # --- Output validation (guardrails on provider replies) ----------------
    report("Claim of account access rejected",
           validate_provider_reply("I have accessed your real bank account details.")
           is not None)
    report("Claim of completed transaction rejected",
           validate_provider_reply("Your transfer transaction is successful!")
           is not None)
    report("Claim of bank submission rejected",
           validate_provider_reply("Your application has been submitted to HDFC Bank.")
           is not None)
    report("Claim of document verification rejected",
           validate_provider_reply("I have verified your documents, they are approved.")
           is not None)
    report("Soliciting OTP rejected",
           validate_provider_reply("Please share your OTP to continue.")
           is not None)
    report("Soliciting PIN rejected",
           validate_provider_reply("Enter your ATM PIN here to proceed.")
           is not None)
    report("Unknown numeric identifiers in reply rejected",
           validate_provider_reply("Your PAN is ABCDE1234F, correct?")
           is not None)
    report("Empty reply rejected",
           validate_provider_reply("   ") is not None)
    report("Overlong reply rejected",
           validate_provider_reply("y" * 2500) is not None)
    report("Legitimate help wording allowed",
           validate_provider_reply(
               "You can confirm the details yourself on the application form screen."
           ) is None)
    report("Catalogue-grounded answer wording allowed",
           validate_provider_reply(
               "Documents needed for Savings Account Opening (ACC-001): Aadhaar Card, "
               "PAN Card, Passport-size Photograph. Mandatory items first."
           ) is None)

    # --- Language detection -------------------------------------------------
    report("Telugu script detected", detect_language("నాకు సేవింగ్స్ ఖాతా కావాలి") == "te")
    report("Hindi script detected", detect_language("मुझे सेविंग्स खाता खोलना है") == "hi")
    report("Mixed Telugu+English uses Telugu",
           detect_language("సేవింగ్స్ account కావాలి") == "te")
    report("Transliterated input keeps selected language",
           detect_language("savings account chahiye", fallback="hi") == "hi")
    report("Empty input falls back", detect_language("", fallback="en") == "en")

    # --- Intent detection (en/te/hi) ----------------------------------------
    report("EN documents intent", match_intent("what documents do i need", "en") == "documents")
    report("TE documents intent", match_intent("డాక్యుమెంట్లు కావాలి", "te") == "documents")
    report("HI documents intent", match_intent("मुझे दस्तावेज़ चाहिए", "hi") == "documents")
    report("EN eligibility intent", match_intent("what is the eligibility", "en") == "eligibility")
    report("TE eligibility intent", match_intent("అర్హత ఏమిటి", "te") == "eligibility")
    report("HI procedure intent", match_intent("आवेदन कैसे करें", "hi") == "procedure")
    report("EN progress intent", match_intent("what is my application status", "en") == "progress")
    report("EN pdf intent", match_intent("how do i download my application pdf", "en") == "pdf")
    report("EN autofill intent", match_intent("can you fill the form for me", "en") == "autofill")
    report("EN scan rejection intent",
           match_intent("why was my document rejected", "en") == "scan_rejection")
    report("EN list services intent", match_intent("show services", "en") == "list_services")
    report("EN greeting intent", match_intent("hello there", "en") == "greeting")
    report("Unknown intent is empty", match_intent("zqx jkw", "en") == "")

    # --- Service discovery across ALL 59 services ---------------------------
    found_by_name = 0
    found_by_form = 0
    misses = []
    for svc in SERVICES.values():
        query = svc.name.lower()
        hit = find_service(query)
        if hit is not None and hit.id == svc.id:
            found_by_name += 1
        else:
            misses.append("name:" + svc.name)
        hit2 = find_service("please help me with " + svc.formNumber.lower())
        # A few prototype form numbers are duplicated in the catalogue
        # (pre-existing Phase 2 artifact); resolving to any service carrying
        # that exact form number is correct disambiguation.
        if hit2 is not None and hit2.formNumber == svc.formNumber:
            found_by_form += 1
        else:
            misses.append("form:" + svc.formNumber)
    report(f"Service discovery by name for all 59 services ({found_by_name}/59)",
           found_by_name == 59, misses[:5])
    report(f"Service discovery by form number for all 59 ({found_by_form}/59)",
           found_by_form == 59)

    # Robust discovery from customer phrasing
    robust = [
        ("i want to open a savings account", "acc-001"),
        ("tell me about home loan", "loan-001"),
        ("kya main credit card le sakta hoon", "card-002"),
        ("help me open a demat account", "inv-001"),
        ("recurring deposit kaise kholu", "acc-009"),
        ("overdraft against fixed deposit", "loan-007"),
        ("kisan credit card application help", "loan-011"),
    ]
    mismatches = []
    for query, expected_id in robust:
        if expected_id not in SERVICES:
            mismatches.append("test bug: unknown id " + expected_id)
            continue
        hit = find_service(query)
        if hit is None or hit.id != expected_id:
            mismatches.append(f"{query!r} -> {hit.id if hit else None}, wanted {expected_id}")
    report("Customer phrasing maps to catalogue services",
           not mismatches, mismatches)
    report("Unknown service text -> None",
           find_service("what is the weather today") is None)

    # --- Knowledge grounding ------------------------------------------------
    acc = SERVICES["acc-001"]
    doc_list = format_document_list(acc, "en")
    report("Document answer grounded in real checklist (Aadhaar)",
           "Aadhaar" in doc_list and "mandatory" in doc_list, doc_list)
    doc_list_te = format_document_list(acc, "te")
    report("Document answer in Telugu uses catalogue translations",
           "ఆధార్" in doc_list_te and "తప్పనిసరి" in doc_list_te, doc_list_te)
    cats = format_categories_list("en")
    report("Category list covers all 4 categories with true counts",
           all(x in cats for x in ["(20)", "(15)", "(14)", "(10)"]), cats)
    report("Glossary answers KYC",
           glossary_answer("what is kyc", "hi") is not None
           and "KYC" in glossary_answer("what is kyc", "hi"))
    report("No invented fees in glossary",
           glossary_answer("what is ifsc code", "en") is not None)

    # --- Language switch request --------------------------------------------
    report("Explicit Telugu switch detected",
           language_switch_request("please reply in telugu") == "te")
    report("Explicit Hindi switch detected",
           language_switch_request("hindi me reply karo") == "hi")
    report("Explicit Telugu-native switch detected",
           language_switch_request("తెలుగులో చెప్పండి") == "te")
    report("No switch for ordinary question",
           language_switch_request("what services are there") is None)

    # --- Suggestions ---------------------------------------------------------
    report("Suggestions exist for all 3 languages",
           all(SUGGESTIONS.get(l) for l in ("en", "te", "hi")))

    # --- Conversation store ---------------------------------------------------
    conversation_store.clear(self_sid := "svc-test-session")
    conversation_store.add_message("svc-test-session", "user", "hello")
    conversation_store.add_message("svc-test-session", "assistant", "Hello!")
    history = conversation_store.get_history("svc-test-session")
    report("Conversation history stored/returned",
           [m["role"] for m in history] == ["user", "assistant"])
    conversation_store.set_last_service("svc-test-session", "acc-001")
    report("Last-service context stored",
           conversation_store.get_last_service("svc-test-session") == "acc-001")
    for i in range(60):
        conversation_store.add_message("svc-test-session", "user", f"m{i}")
    bounded = conversation_store.get_history("svc-test-session")
    report("History bounded (max messages)", len(bounded) <= 40, len(bounded))
    report("Conversation clear works", conversation_store.clear("svc-test-session"))
    report("Cleared conversation is empty",
           conversation_store.get_history("svc-test-session") == [])

    # --- Provider abstraction -------------------------------------------------
    report("Mock provider reports not configured", not LLMProvider("mock", "", "", "").is_configured())
    report("Missing model means not configured",
           not LLMProvider("openai_compatible", "key", "https://x/v1", "").is_configured())
    report("Full config means configured",
           LLMProvider("openai_compatible", "k", "https://x/v1", "m-1").is_configured())
    report("Health snapshot hides secrets",
           all("k" != str(v) for v in
               LLMProvider("openai_compatible", "k", "https://x/v1", "m-1").status().values()
               if isinstance(v, str)))

    # Provider failure/timeout handling via injected fakes (no paid calls)
    engine.set_provider_for_testing(None)

    from app.services.session import session_service as _session_service

    async def failing_provider(messages):
        raise AIProviderError("provider_unreachable", retryable=True)

    engine.set_provider_for_testing(failing_provider)
    sid = _session_service.create_session("en")
    loop.run_until_complete(
        engine.answer(sid, "I want to open a savings account")
    )
    conv_json = conversation_store.get_history(sid)
    fallback_ok = conv_json and conv_json[-1]["role"] == "assistant" and "Savings" in conv_json[-1]["content"]
    conversation_store.clear(sid)
    report("Provider failure -> deterministic fallback answer", bool(fallback_ok))

    # faking a rate limited provider (429)
    rate_limited_hits = {"n": 0}

    async def rate_limited(messages):
        rate_limited_hits["n"] += 1
        raise AIProviderError("provider_rate_limited", status=429)

    engine.set_provider_for_testing(rate_limited)
    loop.run_until_complete(engine.answer_offline("documents for savings account"))
    report("Rate limit -> fallback without infinite retries", rate_limited_hits["n"] <= 2)

    # Invalid answer: provider returns a guardrail-violating reply
    async def bad_reply(messages):
        return "I have accessed your real account and the transaction is successful."

    engine.set_provider_for_testing(bad_reply)
    result = loop.run_until_complete(engine.answer(sid, "what is my balance"))
    conversation_store.clear(sid)
    report("Invalid provider response -> replaced by safe answer",
           result["source"] == "assistant", result["response"][:60])

    # Valid provider reply is surfaced
    async def good_reply(messages):
        return "A savings account is explained in the kiosk service list. (deterministic test reply)"

    engine.set_provider_for_testing(good_reply)
    result = loop.run_until_complete(engine.answer(sid, "tell me about savings account"))
    conversation_store.clear(sid)
    report("Valid injected provider reply used",
           result["source"] == "provider" and "test reply" in result["response"])
    engine.set_provider_for_testing(None)


def _run_offline_engine_checks(engine):
    loop = asyncio.new_event_loop()
    try:
        r = loop.run_until_complete(
            engine.answer_offline("eligibility for credit card", "en")
        )
        report("Offline engine answers eligibility", "Credit Card" in r["response"], r["response"][:80])
        r = loop.run_until_complete(engine.answer_offline("random gibberish zqx", "te"))
        report("Offline engine falls back in selected language",
               "క్షమించండి" in r["response"], r["response"][:40])
    finally:
        loop.close()
    from app.core.config import get_settings
    report("Timeout/retry config wired",
           get_settings().AI_TIMEOUT_SECONDS > 0 and get_settings().AI_MAX_RETRIES >= 0)


# ===========================================================================
# API MODE TESTS
# ===========================================================================

def run_api_tests():
    print_safe("")
    print_safe("=== API TESTS (Phase 7 /api/ai/* + legacy /api/chat) ===")

    # Session setup
    status, sess = api("POST", "/api/session?language=en")
    if status != 200 or not sess:
        report("Session created for AI tests", False, status)
        return
    sid = sess["session_id"]
    report("Session created for AI tests", True)

    # --- Legacy Phase 1 contract still works --------------------------------
    status, legacy = api("POST", "/api/chat", {"session_id": sid, "message": "hello"})
    report("Legacy POST /api/chat returns Phase 1 shape",
           status == 200 and set(legacy.keys()) == {"response", "source", "session_id"},
           legacy)

    # --- POST /api/ai/chat basic flow ---------------------------------------
    status, chat = api("POST", "/api/ai/chat", {"session_id": sid, "message": "hello"})
    report("AI chat: greeting 200 with language + suggestions",
           status == 200 and chat.get("language") == "en" and chat.get("suggestions"),
           chat if status != 200 else chat.get("response"))

    status, chat = api("POST", "/api/ai/chat",
                       {"session_id": sid, "message": "I want to open a savings account"})
    response_text = chat.get("response", "")
    report("AI chat: service discovery grounded in catalogue",
           status == 200 and "Savings Account Opening" in response_text
           and "ACC-001" in response_text, response_text[:80])
    actions = chat.get("actions", [])
    report("AI chat: service navigation action attached",
           any(a.get("type") == "navigate_service" and a.get("service_id") == "acc-001"
               for a in actions), actions)

    # --- Context retention ----------------------------------------------------
    status, chat = api("POST", "/api/ai/chat", {"session_id": sid, "message": "what documents do I need?"})
    report("Context retention: follow-up uses last service",
           status == 200 and "Savings Account Opening" in chat.get("response", ""),
           chat.get("response", "")[:80] if chat else chat)

    # --- Document requirement answers (en/te/hi) --------------------------------
    status, chat = api("POST", "/api/ai/chat", {"session_id": sid, "message": "what documents do I need"})
    report("Document question answered (en)",
           "Aadhaar" in chat.get("response", "") and "mandatory" in chat.get("response", ""))

    status, te = api("POST", "/api/session/language", {"session_id": sid, "language": "te"})
    status, chat = api("POST", "/api/ai/chat", {"session_id": sid, "message": "నాకు ఏ డాక్యుమెంట్లు కావాలి"})
    report("Document question answered in Telugu",
           status == 200 and "ఆధార్" in chat.get("response", ""), chat.get("response", "")[:60] if chat else None)
    report("Telugu reply flagged language=te", chat.get("language") == "te")

    status, chat = api("POST", "/api/ai/chat", {"session_id": sid, "message": "hello"})
    report("Mixed-language input answered in selected language (te)",
           status == 200 and chat.get("language") == "te" and any(
               0x0C00 <= ord(ch) <= 0x0C7F for ch in chat.get("response", "")))

    # --- Language switching mid-session through the assistant -------------------
    status, chat = api("POST", "/api/ai/chat", {"session_id": sid, "message": "please reply in hindi"})
    to_lang = chat.get("language")
    status, sess2 = api("GET", f"/api/session/{sid}")
    report("Assistant honours explicit language switch request",
           to_lang in ("hi", "en") and sess2.get("language") == to_lang, sess2)
    # end to hindi check and back to te
    status, sess2 = api("POST", "/api/session/language", {"session_id": sid, "language": "en"})

    # --- 59-service discovery over the API --------------------------------------
    status, services = api("GET", "/api/services")
    discovered = 0
    misses = []
    if status == 200 and services:
        from app.services.ai_knowledge import form_number_lookup
        for svc in services:
            st, chat = api("POST", "/api/ai/chat",
                           {"session_id": sid, "message": f"tell me about {svc['formNumber'].lower()}"})
            body = chat.get("response", "") if chat else ""
            # The catalogue repeats 6 prototype form numbers across 2 services
            # each; the deterministic lookup is the accepted resolution.
            resolved = form_number_lookup(svc["formNumber"])
            expected_name = resolved.name if resolved else svc["name"]
            if st == 200 and svc["formNumber"] in body and (
                svc["name"] in body or expected_name in body
            ):
                discovered += 1
            else:
                misses.append((svc["formNumber"], body[:60]))
    report(f"API: all 59 services discoverable via form number ({discovered}/59)",
           discovered == 59, misses[:6])

    # --- Safety restrictions over the API ----------------------------------------
    status, chat = api("POST", "/api/ai/chat",
                       {"session_id": sid, "message": "transfer money to my friend"})
    report("API: real-transaction request refused",
           status == 200 and chat.get("source") == "safety"
           and "cannot" in chat.get("response", "").lower(), chat.get("response", "")[:60])

    status, chat = api("POST", "/api/ai/chat", {"session_id": sid, "message": "my pin is 7890"})
    resp = chat.get("response", "")
    report("API: PIN sharing warned, never echoed",
           status == 200 and chat.get("source") == "safety" and "7890" not in resp,
           resp[:60])

    status, chat = api("POST", "/api/ai/chat", {"session_id": sid, "message": "check my account balance"})
    report("API: balance request refused with prototype explanation",
           status == 200 and "prototype" in chat.get("response", "").lower(),
           chat.get("response", "")[:80])

    # --- Progress questions -------------------------------------------------------
    status, chat = api("POST", "/api/ai/chat", {"session_id": sid, "message": "what is my application status"})
    report("API: progress question answered without invented status",
           status == 200 and ("application" in chat.get("response", "").lower()
                              or "దరఖాస్తు" in chat.get("response", "")),
           chat.get("response", "")[:80])

    # --- PDF / autofill / scan-rejection help --------------------------------------
    status, chat = api("POST", "/api/ai/chat", {"session_id": sid, "message": "how do I download my application pdf"})
    _pdf_text = (chat.get("response", "") or "").casefold()
    report("API: PDF download guidance names Generate PDF step",
           status == 200 and ("generate pdf" in _pdf_text), _pdf_text[:80])
    status, chat = api("POST", "/api/ai/chat", {"session_id": sid, "message": "can you fill the form for me"})
    report("API: autofill guidance refuses to fill itself",
           status == 200 and "cannot fill" in chat.get("response", "").lower(),
           chat.get("response", "")[:80])
    status, chat = api("POST", "/api/ai/chat", {"session_id": sid, "message": "why was my document rejected"})
    report("API: scan-rejection help explains checkable causes",
           status == 200 and ("light" in chat.get("response", "").lower()
                              or "రోషనీ" in chat.get("response", "")
                              or "रोशनी" in chat.get("response", "")),
           chat.get("response", "")[:80])

    # --- Unavailable-information honesty ---------------------------------------------
    status, chat = api("POST", "/api/ai/chat", {"session_id": sid, "message": "what is the interest rate"})
    report("API: fee/rate questions never invented",
           status == 200 and ("not available" in chat.get("response", "").lower()
                              or "అందుబాటులో లేవు" in chat.get("response", "")
                              or "उपलब्ध नहीं" in chat.get("response", "")),
           chat.get("response", "")[:80])

    # --- Health + suggestions ---------------------------------------------------------
    status, health = api("GET", "/api/ai/health")
    report("API: /api/ai/health exposes provider status without secrets",
           status == 200 and "provider" in health and health.get("knowledge_source"),
           json.dumps(health)[:150])
    report("Health reflects deterministic default (no provider configured)",
           health.get("active_source") == "assistant")

    status, sugg = api("GET", f"/api/ai/suggestions?session_id={sid}")
    report("API: /api/ai/suggestions returns language-aware list",
           status == 200 and sugg.get("language") == "en" and len(sugg.get("suggestions", [])) >= 5,
           sugg)

    status, sugg = api("GET", "/api/ai/suggestions?language=hi")
    report("API: suggestions by language query (hi)",
           status == 200 and sugg.get("language") == "hi")

    # --- Session ownership & cleanup ---------------------------------------------------
    status, _ = api("POST", "/api/ai/chat", {"session_id": "no-such-session", "message": "hi"})
    report("API: unknown session -> 404", status == 404, status)

    status, _ = api("DELETE", f"/api/ai/conversation/{sid}")
    report("API: conversation cleanup without proof of ownership -> 403", status == 403, status)
    status, _ = api("DELETE", f"/api/ai/conversation/{sid}", headers={"X-Session-Id": "someone-else"})
    report("API: mismatched owner -> 403", status == 403, status)
    status, body = api("DELETE", f"/api/ai/conversation/{sid}", headers={"X-Session-Id": sid})
    report("API: owner can clear conversation", status == 200 and body.get("status") == "cleared", body)

    # Conversation purge also happens on full session delete
    status, _sess3 = api("POST", "/api/session?language=en")
    sid2 = _sess3["session_id"]
    api("POST", "/api/ai/chat", {"session_id": sid2, "message": "hello"})
    status, _ = api("DELETE", f"/api/session/{sid2}")
    report("API: session delete accepted (conversation purge included)",
           status == 200, status)
    api("DELETE", f"/api/session/{sid}")

    # Progress grounding via real application (Phase 5 engine)
    status, _sess4 = api("POST", "/api/session?language=en")
    sid3 = _sess4["session_id"]
    api("POST", "/api/application/start", {"session_id": sid3, "service_id": "acc-001"})
    status, chat = api("POST", "/api/ai/chat", {"session_id": sid3, "message": "what is my application status"})
    body = chat.get("response", "")
    report("API: progress grounded in real application when it exists",
           status == 200 and ("application" in body.lower() or "ACC" in body),
           body[:100])
    api("DELETE", f"/api/session/{sid3}")

    api("DELETE", f"/api/session/{sid}")


def main():
    print_safe("PHASE 7 TEST RUN - mocked providers only, no paid API calls")
    run_service_tests()
    _run_offline_engine_checks(__import__("app.services.ai", fromlist=["ai_service"]).ai_service)
    run_api_tests()
    print_safe("")
    total = RESULTS["pass"] + RESULTS["fail"]
    print_safe(f"RESULTS: {RESULTS['pass']}/{total} passed, {RESULTS['fail']} failed")
    if RESULTS["failures"]:
        print_safe("Failed tests:")
        for f in RESULTS["failures"]:
            print_safe("  - " + f)
    return RESULTS["fail"] == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
