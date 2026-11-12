"""
Field extraction and validation for Indian business/identity documents.

Only masked or non-sensitive values are returned. Full Aadhaar numbers
are never returned or stored (UIDAI rules allow showing the last four
digits only).
"""

import re

# ---------------------------------------------------------------------
# Aadhaar: Verhoeff checksum
# ---------------------------------------------------------------------

_VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6], [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8], [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2], [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4], [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]
_VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2], [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0], [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5], [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]


def verhoeff_valid(number):
    check = 0
    for i, digit in enumerate(reversed(number)):
        check = _VERHOEFF_D[check][_VERHOEFF_P[i % 8][int(digit)]]
    return check == 0


def aadhaar_valid(number):
    return (
        bool(re.fullmatch(r"[2-9]\d{11}", number))
        and verhoeff_valid(number)
    )


def mask_aadhaar(number):
    return "XXXX XXXX " + number[-4:]


# ---------------------------------------------------------------------
# GSTIN: 15 characters with a base-36 check character
# ---------------------------------------------------------------------

_GST_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
GSTIN_PATTERN = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b")


def gstin_check_char(first14):
    total = 0
    for i, char in enumerate(first14):
        value = _GST_CHARS.index(char) * (2 if i % 2 else 1)
        total += value // 36 + value % 36
    return _GST_CHARS[(36 - total % 36) % 36]


def gstin_valid(gstin):
    return (
        bool(GSTIN_PATTERN.fullmatch(gstin))
        and gstin_check_char(gstin[:14]) == gstin[14]
    )


# ---------------------------------------------------------------------
# PAN, Udyam, IFSC
# ---------------------------------------------------------------------

PAN_PATTERN = re.compile(r"\b[A-Z]{3}[ABCFGHLJPT][A-Z]\d{4}[A-Z]\b")
PAN_HOLDER_TYPES = {
    "P": "Individual", "C": "Company", "H": "Hindu Undivided Family",
    "F": "Firm / LLP", "A": "Association of Persons", "T": "Trust",
    "B": "Body of Individuals", "L": "Local Authority",
    "J": "Artificial Juridical Person", "G": "Government",
}
UDYAM_PATTERN = re.compile(r"\bUDYAM-[A-Z]{2}-\d{2}-\d{7}\b")
IFSC_PATTERN = re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b")
AADHAAR_PATTERN = re.compile(r"(?<!\d)([2-9]\d{3})\s?(\d{4})\s?(\d{4})(?!\d)")
DATE_PATTERN = re.compile(r"\b(\d{2})[/-](\d{2})[/-](\d{4})\b")

DOC_TYPE_KEYWORDS = {
    "pan": ["income tax department", "permanent account number"],
    "aadhaar": ["aadhaar", "unique identification", "uidai",
                "government of india"],
    "gst": ["goods and services tax", "gstin", "registration certificate"],
    "udyam": ["udyam registration", "udyam-", "ministry of micro"],
    "bank_statement": ["statement of account", "account statement",
                       "opening balance", "closing balance"],
}

DOC_TYPES = {
    "pan": "PAN card",
    "aadhaar": "Aadhaar card",
    "gst": "GST registration certificate",
    "udyam": "Udyam registration certificate",
    "bank_statement": "Bank statement",
    "other": "Other document",
}


def squash(text):
    """Lower-case and drop whitespace: OCR often merges or splits words."""
    return re.sub(r"\s+", "", text.lower())


def detect_type(text):
    lower = text.lower()
    squashed = squash(text)
    scores = {
        doc_type: sum(squash(word) in squashed for word in words)
        for doc_type, words in DOC_TYPE_KEYWORDS.items()
    }
    # Strong identifiers win over keywords.
    upper = text.upper()
    if UDYAM_PATTERN.search(upper):
        scores["udyam"] += 3
    if GSTIN_PATTERN.search(upper.replace(" ", "")):
        scores["gst"] += 2
    if PAN_PATTERN.search(upper) and "incometax" in squashed:
        scores["pan"] += 2
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "other"


def extract_fields(text, doc_type):
    """Return (fields, checks) for the OCR text of a document."""
    upper = text.upper()
    compact = re.sub(r"\s+", "", upper)
    fields = {}
    checks = []

    pans = sorted(set(PAN_PATTERN.findall(upper)))
    if pans:
        pan = pans[0]
        fields["pan"] = pan[:2] + "XXX" + pan[5:]
        fields["pan_holder_type"] = PAN_HOLDER_TYPES.get(pan[3], "Unknown")
        checks.append({
            "check": "PAN format",
            "passed": True,
            "detail": f"Valid PAN structure ({fields['pan_holder_type']}).",
        })
    elif doc_type == "pan":
        checks.append({"check": "PAN format", "passed": False,
                       "detail": "No valid PAN number found."})

    aadhaar_numbers = ["".join(m) for m in AADHAAR_PATTERN.findall(text)]
    valid_aadhaar = [n for n in aadhaar_numbers if aadhaar_valid(n)]
    if valid_aadhaar:
        fields["aadhaar_masked"] = mask_aadhaar(valid_aadhaar[0])
        checks.append({
            "check": "Aadhaar checksum (Verhoeff)",
            "passed": True,
            "detail": "The number passes the Aadhaar checksum. "
                      "Only the last four digits are kept.",
        })
    elif doc_type == "aadhaar":
        checks.append({
            "check": "Aadhaar checksum (Verhoeff)",
            "passed": False,
            "detail": "No 12-digit number with a valid Aadhaar checksum "
                      "was found. The image may be unclear.",
        })

    gstins = sorted(set(GSTIN_PATTERN.findall(compact)))
    if gstins:
        gstin = gstins[0]
        valid = gstin_valid(gstin)
        fields["gstin"] = gstin
        fields["gst_state_code"] = gstin[:2]
        checks.append({
            "check": "GSTIN checksum",
            "passed": valid,
            "detail": "Check character is correct." if valid
            else "Check character does not match; possible OCR error "
                 "or invalid GSTIN.",
        })
    elif doc_type == "gst":
        checks.append({"check": "GSTIN checksum", "passed": False,
                       "detail": "No GSTIN found."})

    udyam = UDYAM_PATTERN.search(upper.replace(" ", ""))
    if udyam:
        fields["udyam_number"] = udyam.group(0)
        checks.append({"check": "Udyam number format", "passed": True,
                       "detail": "Matches UDYAM-XX-00-0000000."})
    elif doc_type == "udyam":
        checks.append({"check": "Udyam number format", "passed": False,
                       "detail": "No Udyam registration number found."})

    ifsc = IFSC_PATTERN.search(compact)
    if ifsc:
        fields["ifsc"] = ifsc.group(0)
        fields["bank_code"] = ifsc.group(0)[:4]

    dates = DATE_PATTERN.findall(text)
    if dates:
        fields["dates_found"] = ["/".join(d) for d in dates[:3]]

    return fields, checks


def name_matches(text, *names):
    """True when every non-empty name part appears in the text."""
    parts = [squash(p) for p in names if p and len(p.strip()) > 1]
    if not parts:
        return None
    squashed = squash(text)
    return all(part in squashed for part in parts)
