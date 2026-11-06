"""
OCR Engine Service (Phase 4) - modular OCR abstraction.

Provider selection is centralised here. The application never calls a
provider directly - always through get_ocr_service().

Selected engine: Tesseract 5.x (UB-Mannheim build) through pytesseract.
  - Chosen for: Windows/Python 3.13 install compatibility, local/offline
    operation, and real word-level confidence scores (no synthetic scores).
  - PaddleOCR was considered but has no reliable wheel support for
    Python 3.13 on Windows; EasyOCR requires a multi-GB Torch install.

Language availability is probed from the language data files actually
present in TESSDATA - the code never assumes a language model exists.

If no OCR engine is available, get_ocr_service() returns None and the
API clearly reports ocr_available=false. NO fake OCR output is generated;
the application surfaces an explicit "OCR unavailable" state instead.
"""

import os
import shutil
import configparser
from pathlib import Path
from typing import Dict, Any, List, Optional

import cv2
import numpy as np

from app.core.config import get_settings


# ---------------------------------------------------------------------------
# Engine discovery / availability
# ---------------------------------------------------------------------------

_TESSERACT_CANDIDATES = [
    "tesseract",  # on PATH
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]

# Active tessdata: use the bundled project tessdata so hin/tel are guaranteed.
# The path may contain spaces (e.g. "C:\Users\Some Name"), which breaks pytesseract's
# command splitting - so resolve to the Windows 8.3 short path when possible.
import ctypes


def _short_path(path: Path) -> str:
    raw = str(path)
    try:
        buf = ctypes.create_unicode_buffer(520)
        ctypes.windll.kernel32.GetShortPathNameW(raw, buf, 520)
        if buf.value:
            return buf.value
    except Exception:
        pass
    return raw


# Backend-local language data shipped with this prototype (backend/tessdata)
BUNDLED_TESSDATA = Path(__file__).resolve().parents[2] / "tessdata"
TESSDATA_DIR = _short_path(BUNDLED_TESSDATA)


def _find_tesseract_binary(configured: Optional[str] = None) -> Optional[str]:
    if configured and Path(configured).exists():
        return configured
    for cand in _TESSERACT_CANDIDATES:
        path = shutil.which(cand) if not Path(cand).is_absolute() else Path(cand)
        if path:
            return str(path)
    return None


def _list_available_languages(tesseract_cmd: str) -> List[str]:
    """
    Probe which language models actually exist in the active tessdata dir.
    We scan for *.traineddata files directly - deterministic and avoids
    subprocess quirks. (A language matching system models may also exist.)
    """
    langs = set()
    for directory in (BUNDLED_TESSDATA,):
        try:
            if directory.exists():
                for f in directory.glob("*.traineddata"):
                    if f.is_file() and f.stat().st_size > 1024:
                        langs.add(f.stem)
        except Exception:
            continue
    return sorted(langs)


# Active tessdata was resolved above (short path); keep the human-readable
# reference for docs.
TESSDATA_SOURCE = str(BUNDLED_TESSDATA)

_settings = get_settings()
_TESSERACT_CMD = _find_tesseract_binary(getattr(_settings, "TESSERACT_CMD", None))

AVAILABLE = _TESSERACT_CMD is not None
AVAILABLE_LANGUAGES = _list_available_languages(_TESSERACT_CMD) if AVAILABLE else []

if AVAILABLE:
    import pytesseract

    pytesseract.pytesseract.tesseract_cmd = _TESSERACT_CMD


class UnsupportedLanguageError(Exception):
    """Raised when a requested language has no trained OCR model."""


# ---------------------------------------------------------------------------
# Tesseract provider
# ---------------------------------------------------------------------------

def _decode_confidences(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert pytesseract image_to_data output into word records."""
    words: List[Dict[str, Any]] = []
    n = len(data.get("text", []))
    for i in range(n):
        text = (data["text"][i] or "").strip()
        if not text:
            continue
        try:
            conf = float(data["conf"][i])
        except (ValueError, TypeError):
            conf = 0.0
        words.append(
            {
                "text": text,
                "conf": conf,
                "line": int(data.get("line_num", [0] * n)[i]),
                "block": int(data.get("block_num", [0] * n)[i]),
                "par": int(data.get("par_num", [0] * n)[i]),
            }
        )
    return words


def _words_to_lines(words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Group word records into (text, avg_conf) lines."""
    lines: Dict[tuple, List[Dict[str, Any]]] = {}
    for w in words:
        key = (w["block"], w["par"], w["line"])
        lines.setdefault(key, []).append(w)
    out: List[Dict[str, Any]] = []
    for key in sorted(lines.keys()):
        ws = lines[key]
        text = " ".join(w["text"] for w in ws)
        avg_conf = sum(w["conf"] for w in ws) / len(ws)
        out.append({"text": text, "confidence": round(avg_conf, 1)})
    return out


def run_ocr(image_bgr: np.ndarray, languages: List[str]) -> Dict[str, Any]:
    """
    Run actual OCR over the image with the Tesseract provider.

    Returns:
      {
        "engine": "tesseract",
        "languages_requested": [...],
        "languages_used": [...],
        "text": str,            # full plain text
        "confidence": float,    # mean word confidence (real, from engine)
        "lines": [{text, confidence}],
      }
    Raises UnsupportedLanguageError if no requested language model exists.
    Raises RuntimeError if the engine fails for any reason.
    """
    if not AVAILABLE or not _TESSERACT_CMD:
        raise RuntimeError(
            "OCR engine unavailable: Tesseract is not installed on this machine. "
            "The application cannot perform text extraction without a local OCR engine."
        )

    if not AVAILABLE_LANGUAGES:
        raise RuntimeError(
            "OCR engine unavailable: no language data files found in the tessdata directory."
        )

    used = [lang for lang in languages if lang in AVAILABLE_LANGUAGES]
    if not used:
        raise UnsupportedLanguageError(
            "No trained OCR model available for the requested language(s): "
            + ", ".join(languages)
            + ". Available languages: " + ", ".join(AVAILABLE_LANGUAGES)
        )

    import pytesseract

    lang_str = "+".join(used)
    config = f"--tessdata-dir {TESSDATA_DIR} --oem 1 --psm 4"
    try:
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        data = pytesseract.image_to_data(
            gray, lang=lang_str, config=config, output_type=pytesseract.Output.DICT
        )
        words = _decode_confidences(data)
        lines = _words_to_lines(words)
        text = "\n".join(line["text"] for line in lines)
        conf = (
            round(sum(w["conf"] for w in words) / len(words), 1) if words else 0.0
        )
        return {
            "engine": "tesseract",
            "languages_requested": languages,
            "languages_used": used,
            "text": text,
            "confidence": conf,
            "lines": lines,
        }
    except UnsupportedLanguageError:
        raise
    except Exception as exc:  # engine-level failure
        raise RuntimeError(f"OCR processing failed: {exc}") from exc


def get_ocr_service():
    """
    Return the OCR service object, or None when no engine is available.

    The returned object exposes run_ocr(image, languages) and metadata
    (name, available languages). Callers MUST handle the None case by
    reporting a clear 'OCR unavailable' state - never fabricate output.
    """
    if not AVAILABLE:
        return None

    ocr = _OcrService()
    return ocr


class _OcrService:
    name = "tesseract"

    @property
    def available_languages(self) -> List[str]:
        return list(AVAILABLE_LANGUAGES)

    def run(self, image_bgr: np.ndarray, languages: List[str]) -> Dict[str, Any]:
        return run_ocr(image_bgr, languages)

    def get(self) -> Dict[str, Any]:
        """Convenience wrapper matching run()."""
        raise NotImplementedError
