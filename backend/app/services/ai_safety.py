"""
Safety and Privacy Validation (Phase 7).

Two layers:

1. INPUT sanitisation — control characters stripped, length capped, and
   sensitive identifiers (PAN, Aadhaar-like numbers, long digit strings) are
   masked before anything leaves for the deterministic engine or the LLM
   provider. Raw OCR data and document images never enter this pipeline.

2. OUTPUT validation — any AI-provider reply is checked before it reaches
   the customer. Replies that claim real account access, real transactions,
   official document verification, a real submission to HDFC Bank, or that
   solicit PIN/OTP/CVV/password are rejected and the deterministic engine
   answer is used instead.

Sensitive values are never logged; error strings contain only category codes.
"""

import re
import unicodedata
from typing import List, Optional, Set

# ---------------------------------------------------------------------------
# Input sanitisation (privacy §10)
# ---------------------------------------------------------------------------

CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

_PAN_RE = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b", re.IGNORECASE)
_AADHAAR_RE = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")
_LONG_DIGITS_RE = re.compile(r"\b\d{9,}\b")
_OTP_VALUE_RE = re.compile(
    r"\b(?:otp|pin|cvv|password|passcode|one\s?time\s?password)\b[\s:=-]*(?:is\s*)?\w+",
    re.IGNORECASE,
)


def sanitize_user_input(raw: str, max_length: int = 500) -> str:
    """Strip control characters, collapse whitespace, cap length, and mask
    sensitive identifier values. The masked text is safe for the provider."""
    if not raw:
        return ""
    text = CONTROL_CHARS_RE.sub(" ", raw)
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[ \t]+", " ", text).strip()
    if len(text) > max_length:
        text = text[:max_length]
    text = _OTP_VALUE_RE.sub("[SECRET-REDACTED]", text)
    text = _PAN_RE.sub("[PAN-REDACTED]", text)
    text = _AADHAAR_RE.sub("[ID-REDACTED]", text)
    text = _LONG_DIGITS_RE.sub("[NUMBER-REDACTED]", text)
    return text


# ---------------------------------------------------------------------------
# Input safety: real-transaction requests and secret sharing
# ---------------------------------------------------------------------------

# Requests that a real banking action be performed with this assistant.
_REAL_TRANSACTION_RE = re.compile(
    r"\b(?:"
    r"transfer\s+(?:money|funds|cash|rs|rupees|inr|amount|\d+)|send\s+(?:money|funds|cash|rs|rupees|inr|\d+)|"
    r"withdraw\s+(?:money|cash|rs|amount|\d+)|cash\s+withdrawal|"
    r"deposit\s+(?:money|cash|rs|my|\d+)|credit\s+my\s+account|"
    r"pay\s+(?:my\s+)?(?:bills?|credit\s+card\s+bill|\d+)|"
    r"check\s+my\s+(?:account\s+)?balance|my\s+account\s+balance|"
    r"recharge\s+my|deduct\s+money|debit\s+\d+|"
    r"open\s+(?:a\s+)?real\s+account|give\s+me\s+cash"
    r")\b",
    re.IGNORECASE,
)

# Attempting to type secrets into the chat.
_SECRET_SHARING_RE = re.compile(
    r"(?:my\s+)?\b(?:otp|pin|cvv|password|passcode)\b"
    r"\s*(?:is|:|=)\s*\S+",
    re.IGNORECASE,
)

_SECRET_KEYWORDS_RE = re.compile(
    r"\b(?:otp|cvv|password|passcode|pin)\b",
    re.IGNORECASE,
)


def evaluate_input(prompt: str) -> str:
    """Classify raw user input as safe / secret_sharing / real_transaction."""
    if _REAL_TRANSACTION_RE.search(prompt):
        return "real_transaction"
    if _SECRET_KEYWORDS_RE.search(prompt) and (
        _SECRET_SHARING_RE.search(prompt)
        or re.search(r"my\s+(?:otp|pin|cvv|password)|atm\s+pin", prompt, re.IGNORECASE)
    ):
        return "secret_sharing"
    return "safe"


# ---------------------------------------------------------------------------
# Output validation (guardrails on provider replies)
# ---------------------------------------------------------------------------

# Claims a prototype assistant must never make.
_FORBIDDEN_CLAIMS: List[re.Pattern] = [
    re.compile(r"\bi\s+(?:have\s+)?(?:accessed|read|pulled|checked|verified)\s+your\s+(?:real\s+)?(?:bank\s+)?account", re.IGNORECASE),
    re.compile(r"\b(?:transaction|transfer|payment)\s+(?:is\s+)?(?:successful|completed|done|processed)", re.IGNORECASE),
    re.compile(r"\b(?:submitted|sent|forwarded)\s+(?:your\s+)?(?:application|documents|request)\s+to\s+\S*\s*(?:bank|hdfc)", re.IGNORECASE),
    re.compile(r"\b(?:application|documents?|request)\s+has\s+been\s+(?:officially\s+)?(?:verified|approved|submitted)", re.IGNORECASE),
    re.compile(r"\byour\s+documents\s+(?:are\s+)?(?:verified|approved|accepted)\b(?!\s*\?)", re.IGNORECASE),
    re.compile(r"\bi\s+(?:have\s+)?(?:verified|approved|confirmed)\s+your\s+documents", re.IGNORECASE),
    re.compile(r"\b(?:approved|sanctioned|disbursed)\s+(?:your\s+)?(?:loan|account|card)", re.IGNORECASE),
]

# Replies that solicit secrets.
_SECRET_SOLICIT_RE = re.compile(
    r"\b(?:enter|provide|share|send|tell\s+me|what\s+is\s+your)\b[^.!?]{0,40}\b(?:otp|pin|cvv|password|passcode|cvv\s+number|atm\s+pin)\b",
    re.IGNORECASE,
)

MAX_REPLY_LENGTH = 2000


def validate_provider_reply(reply: str) -> Optional[str]:
    """Return a rejection category when a provider reply violates the
    guardrails, or None when the reply may be shown to the customer.
    Never inspects for silence-only rules: legitimate prototype help wording
    ("you can confirm details yourself") is allowed.
    """
    if not reply or not reply.strip():
        return "empty"
    if len(reply) > MAX_REPLY_LENGTH:
        return "too_long"
    for pattern in _FORBIDDEN_CLAIMS:
        if pattern.search(reply):
            return "forbidden_claim"
    if _SECRET_SOLICIT_RE.search(reply):
        return "secret_solicitation"
    if sanitize_user_input(reply) != reply.strip():
        # Reply contains PAN / Aadhaar-like / long-digit strings the customer
        # never typed: do not echo unknown numeric identifiers.
        return "unsanitised_identifier"
    return None


# ---------------------------------------------------------------------------
# Safety refusal answers (per language) — used by the deterministic engine
# ---------------------------------------------------------------------------

REFUSAL_FOR_TRANSACTION = {
    "en": "This is an educational banking prototype, not a real ATM. I cannot transfer money, withdraw or deposit cash, or check a real account balance — no real transaction happens here. To continue an application, please use the service and application screens; I can answer questions about them.",
    "te": "ఇది విద్యాపరమైన బ్యాంకింగ్ ప్రోటోటైప్, నిజమైన ATM కాదు. డబ్బు బదిలీ, నగదు తీసుకోవడం/జమ చేయడం, నిజమైన ఖాతా బ్యాలెన్స్ వంటి నిజమైన లావాదేవీలు ఇక్కడ జరగవు. దరఖాస్తు కొనసాగించడానికి సేవ/దరఖాస్తు స్క్రీన్‌లు వాడండి; వాటి గురించి అడగవచ్చు.",
    "hi": "यह शैक्षिक बैंकिंग प्रोटोटाइप है, वास्तविक ATM नहीं। यहाँ पैसे ट्रांसफ़र, नकद निकासी/जमा, वास्तविक खाता बैलेंस जांच — कोई वास्तविक लेन-देन नहीं होता। आवेदन जारी रखने के लिए सेवा/आवेदन स्क्रीन का उपयोग करें; प्रश्न पूछ सकते हैं।",
}

REFUSAL_FOR_SECRET = {
    "en": "Please do NOT type your PIN, CVV, OTP or password here — this assistant never asks for or needs them. Real banks never ask for these in a chat either. Type your banking question instead, for example \"which documents do I need?\".",
    "te": "దయచేసి మీ PIN, CVV, OTP లేదా పాస్‌వర్డ్‌ను ఇక్కడ టైప్ చేయకండి — ఈ సహాయకుడు వాటిని ఎప్పుడూ అడగడు, అవసరం లేదు. నిజమైన బ్యాంకులు కూడా చాట్‌లో ఇవి అడగవు. బ్యాంకింగ్ ప్రశ్న టైప్ చేయండి, ఉదా: \"నాకు ఏ డాక్యుమెంట్లు కావాలి?\".",
    "hi": "कृपया अपना PIN, CVV, OTP या पासवर्ड यहाँ टाइप न करें — यह सहायक इन्हें कभी नहीं मांगता और इनकी आवश्यकता नहीं होती। असली बैंक भी चैट में ये नहीं पूछते। कृपया बैंकिंग प्रश्न टाइप करें, जैसे \"मुझे कौन से दस्तावेज़ चाहिए?\"।",
}
