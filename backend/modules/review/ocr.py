"""
Read a bill (PDF or image) and pull out the invoice fields.

Order of work:
  1. PDF with a text layer -> pdfplumber (exact text, best accuracy).
  2. Otherwise render the page and run Tesseract (after cleaning the
     image: grayscale, upscale, contrast).
  3. Work line by line, because bills are laid out in lines.

Seller and buyer are read separately. The XML builder picks the right
one for the voucher type.
"""

import io
import re

from models.invoice_models import empty_ocr_data


class OcrNotAvailable(Exception):
    pass


_OCR_READY = None
_OCR_PROBLEM = ""


# Check once whether Tesseract is usable, and remember the answer.
def _check_ocr_availability():
    global _OCR_READY, _OCR_PROBLEM
    if _OCR_READY is not None:
        return _OCR_READY, _OCR_PROBLEM
    try:
        import pytesseract
    except ImportError:
        _OCR_READY, _OCR_PROBLEM = False, "pytesseract is not installed (pip install pytesseract)"
        return _OCR_READY, _OCR_PROBLEM
    try:
        from config import Config
        path = getattr(Config, "TESSERACT_CMD", "") or ""
        if path:
            pytesseract.pytesseract.tesseract_cmd = path
    except Exception:
        pass
    try:
        pytesseract.get_tesseract_version()
    except Exception:
        _OCR_READY = False
        _OCR_PROBLEM = ("Tesseract binary not found. Install it from "
                        "https://github.com/UB-Mannheim/tesseract/wiki and set TESSERACT_CMD in .env.")
        return _OCR_READY, _OCR_PROBLEM
    _OCR_READY, _OCR_PROBLEM = True, ""
    return _OCR_READY, _OCR_PROBLEM


def ocr_status():
    ready, problem = _check_ocr_availability()
    return {"ready": ready, "message": problem if not ready else "OCR is ready."}


# ---------------------------------------------------------------
# 1. Getting text out of the file
# ---------------------------------------------------------------

def _read_pdf_text(data):
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            return "\n".join((p.extract_text() or "") for p in pdf.pages[:3])
    except Exception as exc:
        print("[OCR] pdfplumber unavailable/failed:", exc)
        return ""


# Make the picture easier for Tesseract: grayscale, bigger, sharper.
def _prepare_image(image):
    from PIL import ImageOps
    image = ImageOps.exif_transpose(image).convert("L")
    if image.width < 1600:
        scale = 1600 / image.width
        image = image.resize((int(image.width * scale), int(image.height * scale)))
    return ImageOps.autocontrast(image)


def _load_images(data, ext):
    from PIL import Image
    if ext != "pdf":
        return [Image.open(io.BytesIO(data))]
    try:
        from pdf2image import convert_from_bytes
    except ImportError:
        raise OcrNotAvailable("pdf2image not installed")
    try:
        from config import Config
        poppler = getattr(Config, "POPPLER_PATH", "") or ""
    except Exception:
        poppler = ""
    try:
        kwargs = {"dpi": 300, "first_page": 1, "last_page": 2}
        if poppler:
            kwargs["poppler_path"] = poppler
        pages = convert_from_bytes(data, **kwargs)
    except Exception as exc:
        raise OcrNotAvailable("PDF conversion failed: " + str(exc))
    if not pages:
        raise OcrNotAvailable("PDF has no pages.")
    return pages


# Try two Tesseract layouts and keep the one that found more digits,
# because digits (amounts, GSTIN, dates) are what we care about.
def _tesseract_text(image):
    import pytesseract
    image = _prepare_image(image)
    best = ""
    for psm in (6, 4):
        try:
            text = pytesseract.image_to_string(image, config=f"--psm {psm}")
        except Exception:
            continue
        if len(re.findall(r"\d", text)) > len(re.findall(r"\d", best)):
            best = text
    return best


def _read_text(data, extension):
    ext = (extension or "png").lower()
    if ext == "pdf":
        text = _read_pdf_text(data)
        if len(text.strip()) > 60:
            return text
        print("[OCR] PDF has no usable text layer, using Tesseract")
    return "\n".join(_tesseract_text(img) for img in _load_images(data, ext))


# ---------------------------------------------------------------
# 2. GSTIN helpers
# ---------------------------------------------------------------

GSTIN_FORMAT = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][0-9A-Z]Z[0-9A-Z]$")
_DIGIT_POS = {0, 1, 7, 8, 9, 10}
_LETTER_POS = {2, 3, 4, 5, 6, 11}
_TO_DIGIT = {"O": "0", "D": "0", "I": "1", "L": "1", "S": "5", "B": "8", "Z": "2"}
_TO_LETTER = {"0": "O", "1": "I", "5": "S", "8": "B", "2": "Z"}


# Fix the usual OCR mix-ups (O/0, I/1, S/5, B/8) by position.
def _fix_gstin(token):
    token = token.upper()
    if len(token) != 15:
        return ""
    out = []
    for i, ch in enumerate(token):
        if i in _DIGIT_POS:
            ch = _TO_DIGIT.get(ch, ch)
        elif i in _LETTER_POS:
            ch = _TO_LETTER.get(ch, ch)
        elif i == 13 and ch == "2":
            ch = "Z"
        out.append(ch)
    fixed = "".join(out)
    return fixed if GSTIN_FORMAT.match(fixed) else ""


def _gstins_in(line):
    found = []
    for token in re.findall(r"(?<![0-9A-Za-z])[0-9A-Za-z]{15}(?![0-9A-Za-z])", line):
        fixed = _fix_gstin(token)
        if fixed:
            found.append(fixed)
    return found


# ---------------------------------------------------------------
# 3. Names
# ---------------------------------------------------------------

ADDRESS_WORDS = ("road", "street", "shop ", "nagar", "floor", "plot", "near ", "opp",
                 "colony", "phase", "sector", "maharashtra", "india", "phone", "mob",
                 "tel", "email", "@", "www.", "gstin", "gst no", "pin ", "state")
HEADER_WORDS = ("tax invoice", "invoice", "sample business", "original", "duplicate",
                "bill of supply", "document no", "date", "bill to", "party", "sr.",
                "description", "subtotal", "grand total", "declaration", "authorised")


def _is_address(line):
    low = line.lower()
    return bool(re.search(r"\b\d{6}\b", line)) or any(w in low for w in ADDRESS_WORDS)


def _is_header(line):
    low = line.lower()
    return any(low.startswith(w) or w in low for w in HEADER_WORDS) or line.isupper() and len(line) > 15


# Remove things that are not part of a business name.
def _tidy_name(text):
    text = re.sub(r"\(.*?\)", " ", text)            # "(Fictional Test Data)"
    text = re.split(r"\||GSTIN|GST\s*No|Phone|Mob", text, flags=re.I)[0]
    text = re.sub(r"\s+", " ", text)
    return text.strip(" :|,;.-")[:80]


# Seller = the business printed at the top, just above its own GSTIN.
def _find_seller(lines):
    gst_index = next((i for i, l in enumerate(lines) if _gstins_in(l)), None)
    if gst_index is not None:
        for j in range(gst_index, max(-1, gst_index - 5), -1):
            line = lines[j]
            if _is_address(line) or _is_header(line) or re.match(r"^[\d,\.\s]+$", line):
                continue
            name = _tidy_name(line)
            if len(name) >= 3:
                return name
    for line in lines[:10]:
        if _is_address(line) or _is_header(line):
            continue
        name = _tidy_name(line)
        if len(name) >= 3:
            return name
    return ""


BUYER_LABEL = re.compile(
    r"^(?:bill(?:ed)?\s*to|buyer|customer|consignee|sold\s*to|ship\s*to)"
    r"(?:\s*/\s*party)?(?:\s*name)?\s*[:\-]\s*(.*)$", re.I)


def _find_buyer(lines):
    for i, line in enumerate(lines):
        m = BUYER_LABEL.match(line)
        if m:
            value = m.group(1).strip()
            if not value and i + 1 < len(lines):
                value = lines[i + 1]
            name = _tidy_name(value)
            if len(name) >= 2:
                return name
    return ""


def _find_buyer_gstin(lines, seller_gstin):
    label = re.compile(r"party|buyer|customer|bill\s*to|consignee", re.I)
    for line in lines:
        if label.search(line):
            for g in _gstins_in(line):
                if g != seller_gstin:
                    return g
    for line in lines:                       # second distinct GSTIN in the bill
        for g in _gstins_in(line):
            if g != seller_gstin:
                return g
    return ""


# ---------------------------------------------------------------
# 4. Invoice number and date
# ---------------------------------------------------------------

INVOICE_NO_PATTERNS = [
    re.compile(r"Document\s*No\.?\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-\/]{2,30})", re.I),
    re.compile(r"Invoice\s*(?:No|Number|#)\.?\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-\/]{2,30})", re.I),
    re.compile(r"Bill\s*(?:No|Number|#)\.?\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-\/]{2,30})", re.I),
    re.compile(r"\b(INV[\-\/][A-Z0-9][A-Z0-9\-\/]{2,25})\b", re.I),
]

DATE_PATTERNS = [
    re.compile(r"\b(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})\b"),
    re.compile(r"\b(\d{4}[\/\-\.]\d{2}[\/\-\.]\d{2})\b"),
    re.compile(r"\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})\b", re.I),
]


def _first_match(patterns, text):
    for p in patterns:
        m = p.search(text)
        if m and m.group(1).strip():
            return m.group(1).strip()
    return ""


# Prefer a date on a line that says "Date" (but not "Due Date").
def _find_date(lines, text):
    for line in lines:
        low = line.lower()
        if "date" in low and "due" not in low:
            found = _first_match(DATE_PATTERNS, line)
            if found:
                return found
    return _first_match(DATE_PATTERNS, text)


# ---------------------------------------------------------------
# 5. Amounts
# ---------------------------------------------------------------

# Last money value on a line. Tax rates like "(9%)" are removed first
# so we never mistake the rate for the amount.
def _money_on_line(line):
    cleaned = re.sub(r"\(?\s*@?\s*\d+(?:\.\d+)?\s*%\s*\)?", " ", line)
    numbers = re.findall(r"\d[\d,]*\.\d{1,2}|\d[\d,]*", cleaned)
    decimals = [n for n in numbers if "." in n]
    pick = decimals[-1] if decimals else (numbers[-1] if numbers else None)
    if pick is None:
        return None
    try:
        return float(pick.replace(",", ""))
    except ValueError:
        return None


def _find_amount(lines, label, exclude=None, last=False):
    hits = []
    for i, line in enumerate(lines):
        if not re.search(label, line, re.I):
            continue
        if exclude and re.search(exclude, line, re.I):
            continue
        value = _money_on_line(line)
        if value is None and i + 1 < len(lines):      # value on the next line
            value = _money_on_line(lines[i + 1])
        if value is not None:
            hits.append(value)
    if not hits:
        return 0.0
    return hits[-1] if last else hits[0]


def detect_bill_type(lines):
    head = " ".join(lines[:12]).lower()
    if "credit note" in head or "sales return" in head:
        return "sales_return"
    if "debit note" in head or "purchase return" in head:
        return "purchase_return"
    if "sales" in head:
        return "sales"
    if "purchase" in head:
        return "purchase"
    return "purchase"


# Tesseract often reads the rupee sign as a 7 (or another digit), so
# "₹4,350.00" turns into 74,350.00. We cannot spot that from the digits
# alone, but we CAN check the arithmetic: taxable + taxes must equal
# total. If they do not, try the same numbers with the first digit
# removed and keep the combination that balances.
def _strip_first_digit(value):
    text = f"{value:.2f}"
    whole, dec = text.split(".")
    if len(whole) < 2:
        return None
    return float(whole[1:] + "." + dec)


def _reconcile_amounts(subtotal, taxes, total):
    def balanced(s, t):
        return s > 0 and t > 0 and abs(s + taxes - t) <= 1.0

    if balanced(subtotal, total):
        return subtotal, total, False

    sub_options = [subtotal, _strip_first_digit(subtotal) if subtotal else None]
    tot_options = [total, _strip_first_digit(total) if total else None]
    for s in sub_options:
        for t in tot_options:
            if s is not None and t is not None and balanced(s, t):
                return s, t, True

    # Last resort: trust the total and the tax amounts.
    if total > taxes:
        return round(total - taxes, 2), total, True
    return subtotal, total, False
# ---------------------------------------------------------------
# 6. Main entry point
# ---------------------------------------------------------------

def extract_fields(image_bytes, extension):
    ready, problem = _check_ocr_availability()
    if not ready:
        raise OcrNotAvailable(problem)

    try:
        text = _read_text(image_bytes, extension)
    except OcrNotAvailable:
        raise
    except Exception as exc:
        raise OcrNotAvailable("OCR failed: " + str(exc))

    if len(text.strip()) < 20:
        raise OcrNotAvailable("Could not read any text from this file.")

    lines = [re.sub(r"\s{2,}", " ", l).strip() for l in text.splitlines() if l.strip()]
    ocr = empty_ocr_data()
    ocr["raw_text"] = text[:5000]
    warnings = []

    ocr["invoice_number"] = _first_match(INVOICE_NO_PATTERNS, text)
    ocr["invoice_date"] = _find_date(lines, text)

    # parties
    seller_gstin = next((g for l in lines for g in _gstins_in(l)), "")
    ocr["seller_name"] = _find_seller(lines)
    ocr["seller_gstin"] = seller_gstin
    ocr["buyer_name"] = _find_buyer(lines)
    ocr["buyer_gstin"] = _find_buyer_gstin(lines, seller_gstin)
    ocr["vendor_name"] = ocr["seller_name"]
    ocr["gstin"] = seller_gstin

    # amounts: read every value first
    cgst = _find_amount(lines, r"\bC\.?\s?G\.?\s?S\.?\s?T\b")
    sgst = _find_amount(lines, r"\bS\.?\s?G\.?\s?S\.?\s?T\b")
    igst = _find_amount(lines, r"\bI\.?\s?G\.?\s?S\.?\s?T\b")
    subtotal = _find_amount(lines, r"sub\s*-?\s*total|taxable\s*(?:value|amount)")
    total = _find_amount(lines, r"grand\s*total|total\s*amount|invoice\s*total|net\s*payable|amount\s*payable")
    if total == 0.0:
        total = _find_amount(lines, r"\btotal\b", exclude=r"sub\s*-?\s*total|tax|gst", last=True)

    # taxes MUST be defined before anything below uses it
    taxes = cgst + sgst + igst

    if total == 0.0 and subtotal:
        total = subtotal + taxes
    taxable = subtotal if subtotal else max(total - taxes, 0.0)

    if total:
        taxable, total, corrected = _reconcile_amounts(taxable, taxes, total)
        if corrected:
            warnings.append("Amounts were auto-corrected so they add up. Please verify them.")
        if abs(taxable + taxes - total) > 1.0:
            warnings.append("Amounts do not add up (taxable + tax is not equal to total). Please check them.")

    if not ocr["invoice_number"]:
        warnings.append("Invoice number not found.")
    if not ocr["invoice_date"]:
        warnings.append("Invoice date not found.")
    if not ocr["seller_gstin"]:
        warnings.append("Seller GSTIN not found.")

    ocr["cgst"] = round(cgst, 2)
    ocr["sgst"] = round(sgst, 2)
    ocr["igst"] = round(igst, 2)
    ocr["taxable_amount"] = round(taxable, 2)
    ocr["total_amount"] = round(total, 2)
    ocr["detected_type"] = detect_bill_type(lines)
    ocr["warnings"] = warnings

    print("[OCR] ===== extracted =====")
    for k in ("invoice_number", "invoice_date", "seller_name", "seller_gstin",
              "buyer_name", "buyer_gstin", "taxable_amount", "cgst", "sgst",
              "igst", "total_amount", "detected_type"):
        print(f"[OCR] {k:15} = {ocr[k]}")
    for w in warnings:
        print("[OCR] WARNING:", w)

    return ocr