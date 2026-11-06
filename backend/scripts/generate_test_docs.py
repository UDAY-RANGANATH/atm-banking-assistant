"""
Synthetic test document generator (Phase 4)

Renders clearly-marked SYNTHETIC test documents ("SYNTHETIC TEST DOCUMENT, NOT A REAL
DOCUMENT" watermark) used by automated tests and the demonstration mode.

These are not real identity documents and must never be submitted as such.
Fonts: uses Windows Nirmala UI when needed for Devanagari/Telugu glyphs,
falls back to the default PIL font.
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures"
OUT_DIR.mkdir(parents=True, exist_ok=True)

_A4 = (1654, 2339)  # A4 at 200dpi-ish; renders fast

try:
    F_LATIN = ImageFont.truetype("arial.ttf", 42)
    F_LATIN_S = ImageFont.truetype("arial.ttf", 30)
    F_LATIN_XS = ImageFont.truetype("arial.ttf", 24)
except OSError:
    F_LATIN = F_LATIN_S = F_LATIN_XS = None

_INDIC_FONT_PATHS = [
    r"C:\Windows\Fonts\Nirmala.ttf",
    r"C:\Windows\Fonts\nirmala.ttf",
]

def indic_font(size: int):
    for p in _INDIC_FONT_PATHS:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _font(size: int):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _canvas(title: str) -> tuple:
    img = Image.new("RGB", _A4, "white")
    d = ImageDraw.Draw(img)
    d.rectangle([60, 60, _A4[0] - 60, _A4[1] - 60], outline="black", width=6)
    d.text((_A4[0] // 2, 110), title, fill="black", font=_font(48), anchor="mm")
    # watermark the synthetic notice
    d.text((_A4[0] // 2, 175), "SYNTHETIC TEST DOCUMENT - NOT A REAL DOCUMENT - PROTOTYPE ONLY",
           fill="dimgray", font=_font(22), anchor="mm")
    return img, d


def generate_pan(fake_number: str = "DEMON0123F", lang: str = "en") -> Path:
    img, d = _canvas("INCOME TAX DEPARTMENT" if lang == "en" else "आयकर विभाग")
    y = 320
    d.text((240, y), "GOVT. OF INDIA", fill="black", font=_font(34)); y += 90
    d.text((240, y), "Permanent Account Number Card", fill="black", font=_font(38)); y += 110
    d.text((240, y), "Name" if lang == "en" else "नाम", fill="black", font=_font(26)); y += 44
    d.text((240, y), "Demo Srinivas", fill="black", font=_font(40)); y += 80
    d.text((240, y), "Date of Birth" if lang == "en" else "जन्म तिथि", fill="black", font=_font(26)); y += 44
    d.text((240, y), "15/01/2005", fill="black", font=_font(40)); y += 90
    d.text((240, y), "PAN Number", fill="black", font=_font(26)); y += 50
    d.text((240, y), fake_number, fill="black", font=_font(48))
    out = OUT_DIR / f"pan_en_{fake_number}.png"
    img.save(out)
    return out


def generate_aadhaar(fake_number: str = "2345 1234 5678", lang: str = "en") -> Path:
    img, d = _canvas("UNIQUE IDENTIFICATION AUTHORITY OF INDIA" if lang == "en" else "भारत सरकार")
    y = 340
    d.text((240, y), "Aadhaar Card" if lang == "en" else "आधार कार्ड", fill="black", font=_font(44)); y += 120
    d.text((240, y), "Name" if lang == "en" else "नाम", fill="black", font=_font(26)); y += 48
    d.text((240, y), "Demo Ramesh Kumar", fill="black", font=_font(40)); y += 84
    d.text((240, y), "Date of Birth" if lang == "en" else "जन्म तिथि", fill="black", font=_font(26)); y += 48
    d.text((240, y), "10/04/1990", fill="black", font=_font(40)); y += 90
    d.text((240, y), "Address" if lang == "en" else "पता", fill="black", font=_font(26)); y += 48
    d.text((240, y), "12-3-45 Demo Street, Hyderabad", fill="black", font=_font(34)); y += 110
    d.text((240, y), fake_number, fill="black", font=_font(52))
    out = OUT_DIR / f"aadhaar_{lang}_{fake_number.replace(' ', '_')}.png"
    img.save(out)
    return out


def generate_marksheet(lang: str = "en", student: str = "Demo Anjali", year: str = "2022") -> Path:
    title = {
        "en": "SECONDARY SCHOOL CERTIFICATE",
        "hi": "माध्यमिक विद्यालय प्रमाणपत्र",
        "te": "మాధ్యమిక పాఠశాల ప్రమాణపత్రం",
    }[lang]
    img, d = _canvas(title)
    fb = indic_font(40)
    y = 330
    d.text((240, y), "Board of Secondary Education", fill="black", font=_font(34)); y += 90
    d.text((240, y), "Name : " + student, fill="black", font=fb); y += 90
    d.text((240, y), "Class : 10th Standard", fill="black", font=fb); y += 84
    d.text((240, y), "Year of Passing : " + year, fill="black", font=fb); y += 84
    d.text((240, y), "Marks Obtained : 476 / 500", fill="black", font=fb)
    out = OUT_DIR / f"marksheet_{lang}_{student.replace(' ', '_')}_{year}.png"
    img.save(out)
    return out


def generate_salary_slip() -> Path:
    img, d = _canvas("SALARY SLIP")
    y = 330
    d.text((240, y), "Acme Technologies Pvt Ltd", fill="black", font=_font(38)); y += 90
    d.text((240, y), "Employee Name : Demo Girish", fill="black", font=_font(34)); y += 70
    d.text((240, y), "Pay Period : March 2026", fill="black", font=_font(34)); y += 70
    d.text((240, y), "Basic Salary : Rs 45000", fill="black", font=_font(34)); y += 70
    d.text((240, y), "Gross Salary : Rs 58200", fill="black", font=_font(34)); y += 70
    d.text((240, y), "Net Salary : Rs 51000", fill="black", font=_font(34))
    out = OUT_DIR / "salary_slip.png"
    img.save(out)
    return out


def generate_gst() -> Path:
    img, d = _canvas("GST REGISTRATION CERTIFICATE")
    y = 330
    d.text((240, y), "Goods and Services Tax", fill="black", font=_font(34)); y += 90
    d.text((240, y), "Business Name : Demo Traders LLP", fill="black", font=_font(34)); y += 80
    d.text((240, y), "GSTIN : 36DEMO1234K1Z5", fill="black", font=_font(40)); y += 90
    d.text((240, y), "Registration Date : 12/06/2023", fill="black", font=_font(34))
    out = OUT_DIR / "gst_registration.png"
    img.save(out)
    return out


def generate_bank_statement() -> Path:
    img, d = _canvas("STATEMENT OF ACCOUNT")
    y = 330
    d.text((240, y), "Bank : Demo Bank Ltd", fill="black", font=_font(34)); y += 80
    d.text((240, y), "Account Holder : Demo Suresh", fill="black", font=_font(34)); y += 80
    d.text((240, y), "Account Number : 000112233445", fill="black", font=_font(34)); y += 80
    d.text((240, y), "IFSC : DEMO0001234", fill="black", font=_font(34)); y += 80
    d.text((240, y), "Statement Period : 01/01/2026 - 31/03/2026", fill="black", font=_font(34)); y += 80
    for i in range(3):
        d.text((240, y), f"Transaction {i+1} : Rs 2,{i}50.00", fill="black", font=_font(30)); y += 60
    out = OUT_DIR / "bank_statement.png"
    img.save(out)
    return out


ALL = {
    "pan_en": generate_pan,
    "aadhaar_en": generate_aadhaar,
    "aadhaar_hi": lambda: generate_aadhaar(lang="hi"),
    "aadhaar_te": lambda: generate_aadhaar(lang="te"),
    "marksheet_en": generate_marksheet,
    "marksheet_te": lambda: generate_marksheet(lang="te"),
    "salary_slip": generate_salary_slip,
    "gst_registration": generate_gst,
    "bank_statement": generate_bank_statement,
}


if __name__ == "__main__":
    for name, fn in ALL.items():
        path = fn()
        print(f"Generated {name}: {path}")

