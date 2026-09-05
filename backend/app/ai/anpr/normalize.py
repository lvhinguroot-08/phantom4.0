import re
from typing import Any, Dict, Optional, Tuple

# Strip all non-alphanumeric noise (spaces, hyphens, dots, underscores, special characters)
_STRIP_CHARS = re.compile(r"[^A-Za-z0-9]")

# Standard State format: State (2 letters) + RTO (1-2 digits) + Series (0-3 letters) + Number (1-4 digits)
_STD_INDIAN_PLATE = re.compile(r"^([A-Z]{2})([0-9]{1,2})([A-Z]{0,3})([0-9]{1,4})$")

# Bharat Series: Year (2 digits) + BH + Number (4 digits) + Letters (1-2 letters)
_BH_SERIES_PLATE = re.compile(r"^([0-9]{2})(BH)([0-9]{4})([A-Z]{1,2})$")

# Common Indian State/UT Codes
INDIAN_STATE_CODES = {
    "AN", "AP", "AR", "AS", "BR", "CH", "CG", "DD", "DL", "DN", "GA", "GJ", "HP",
    "HR", "JH", "JK", "KA", "KL", "LA", "LD", "MH", "ML", "MN", "MP", "MZ", "NL",
    "OD", "PB", "PY", "RJ", "SK", "TN", "TR", "TS", "UK", "UP", "WB"
}

# Gujarat specific State Codes
GUJARAT_RTO_CODES = {
    "01": "Ahmedabad", "02": "Mehsana", "03": "Rajkot", "04": "Bhavnagar",
    "05": "Surat", "06": "Vadodara", "07": "Nadiad/Kheda", "08": "Palanpur/Banaskantha",
    "09": "Himmatnagar/Sabar Kantha", "10": "Jamnagar", "11": "Junagadh",
    "12": "Bhuj/Kutch", "13": "Surendranagar", "14": "Amreli", "15": "Valsad",
    "16": "Bharuch", "17": "Godhra/Panchmahal", "18": "Gandhinagar", "19": "Bardoli",
    "20": "Dahod", "21": "Navsari", "22": "Rajpipla/Narmada", "23": "Anand",
    "24": "Patan", "25": "Porbandar", "26": "Vyara/Tapi", "27": "Ahmedabad East",
    "28": "Surat West", "29": "Vadodara Rural", "30": "Dang/Ahwa", "31": "Modasa/Aravalli",
    "32": "Veraval/Gir Somnath", "33": "Botad", "34": "Chhota Udepur", "35": "Lunawada/Mahisagar",
    "36": "Morbi", "37": "Khambhalia/Devbhumi Dwarka", "38": "Bavla/Ahmedabad Rural",
}

# Character disambiguation mapping tables for Indian ANPR OCR errors
CHAR_TO_DIGIT = {
    "O": "0", "D": "0", "Q": "0", "U": "0",
    "I": "1", "L": "1", "T": "1",
    "Z": "2",
    "J": "3",
    "A": "4",
    "S": "5",
    "G": "6", "C": "6",
    "B": "8",
}

DIGIT_TO_CHAR = {
    "0": "O",
    "1": "I",
    "2": "Z",
    "3": "J",
    "4": "A",
    "5": "S",
    "6": "G",
    "8": "B",
}


def disambiguate_plate(raw_plate: str) -> str:
    """
    Applies position-specific OCR disambiguation for Indian license plate syntax:
    - Positions 0-1: State Code (Letters, e.g. GJ, DL, MH, KA, etc.)
    - Positions 2-3: District / RTO Code (Digits, e.g. 05, 01, 27)
    - Middle: Series (0 to 3 Letters, e.g. AB, CD, A)
    - Suffix: Registration Number (1 to 4 Digits, e.g. 1234, 0001)
    """
    if not raw_plate:
        return ""
    
    # Strip non-alphanumerics
    cleaned = _STRIP_CHARS.sub("", raw_plate).upper()
    
    # Strip common IND prefix/suffix if present at edges
    if cleaned.startswith("IND") and len(cleaned) >= 9:
        cleaned = cleaned[3:]
    elif cleaned.endswith("IND") and len(cleaned) >= 9:
        cleaned = cleaned[:-3]

    n = len(cleaned)
    if n < 4:
        return cleaned

    # Check for Bharat (BH) series: 2 digits + BH + 4 digits + 1-2 letters
    if "BH" in cleaned[1:4] and n >= 8:
        chars = list(cleaned)
        # Year digits
        for i in range(0, 2):
            if chars[i] in CHAR_TO_DIGIT:
                chars[i] = CHAR_TO_DIGIT[chars[i]]
        # 'BH'
        chars[2] = "B"
        chars[3] = "H"
        # 4 digits
        for i in range(4, min(8, n)):
            if chars[i] in CHAR_TO_DIGIT:
                chars[i] = CHAR_TO_DIGIT[chars[i]]
        # 1-2 letters
        for i in range(8, n):
            if chars[i] in DIGIT_TO_CHAR:
                chars[i] = DIGIT_TO_CHAR[chars[i]]
        return "".join(chars)

    # Standard Indian Plate Syntax (6-11 characters, e.g., GJ05AB1234, GJ1A1234)
    if 6 <= n <= 11:
        chars = list(cleaned)
        # 0. Common state prefix OCR errors (e.g. 6J -> GJ, G1 -> GJ, C1 -> GJ)
        if chars[0] in ("6", "C") and chars[1] in ("J", "1", "I"):
            chars[0] = "G"
            chars[1] = "J"
        elif chars[0] == "G" and chars[1] in ("1", "I", "T"):
            chars[1] = "J"

        # 1. First 2 positions are State Letters (e.g. GJ)
        for i in range(min(2, n)):
            if chars[i] in DIGIT_TO_CHAR:
                chars[i] = DIGIT_TO_CHAR[chars[i]]
        
        # 2. Next 2 positions are RTO Digits (e.g. 05)
        for i in range(2, min(4, n)):
            if chars[i] in CHAR_TO_DIGIT:
                chars[i] = CHAR_TO_DIGIT[chars[i]]

        # 3. Determine suffix digit count (usually last 4, or last 1-4 digits)
        digit_count = 4 if n >= 8 else max(1, n - 4)
        for i in range(n - digit_count, n):
            if chars[i] in CHAR_TO_DIGIT:
                chars[i] = CHAR_TO_DIGIT[chars[i]]

        # 4. Middle positions (between RTO and final digits) are Series Letters
        for i in range(4, n - digit_count):
            if chars[i] in DIGIT_TO_CHAR:
                chars[i] = DIGIT_TO_CHAR[chars[i]]

        return "".join(chars)

    return cleaned


def normalize_plate_text(raw: Optional[str]) -> str:
    """Uppercase, strip spaces/hyphens/punctuation, and apply syntax disambiguation."""
    if raw is None:
        return ""
    raw_str = str(raw).strip()
    return disambiguate_plate(raw_str)


def score_plate_format(plate: Optional[str]) -> float:
    """
    Score the syntactic validity of a candidate license plate string [0.0 - 1.0].
    Used as the Format Validity component in ANPR confidence fusion.
    """
    if not plate:
        return 0.0

    cleaned = _STRIP_CHARS.sub("", plate).upper()
    if len(cleaned) < 4:
        return 0.0

    # 1. Perfect BH series match
    if _BH_SERIES_PLATE.fullmatch(cleaned):
        return 1.0

    # 2. Check standard state format
    m = _STD_INDIAN_PLATE.fullmatch(cleaned)
    if m:
        state, rto, series, number = m.groups()
        # Full 4-digit number and recognized state code -> 1.0
        if state in INDIAN_STATE_CODES and len(number) == 4 and len(rto) == 2:
            return 1.0
        elif state in INDIAN_STATE_CODES:
            return 0.90
        else:
            return 0.80

    # 3. Partial plausibility checks
    if 6 <= len(cleaned) <= 11:
        prefix = cleaned[:2]
        if prefix in INDIAN_STATE_CODES:
            # Starts with recognized state, has at least some digits
            has_digits = any(c.isdigit() for c in cleaned[2:])
            if has_digits:
                return 0.65
        elif prefix.isalpha():
            return 0.40

    return 0.15 if len(cleaned) >= 6 else 0.0


def looks_like_indian_plate(normalized: Optional[str]) -> bool:
    """Check if normalized string matches Indian vehicle registration pattern (State or BH series)."""
    if not normalized:
        return False
    norm = normalized.strip().upper()
    return bool(_STD_INDIAN_PLATE.fullmatch(norm) or _BH_SERIES_PLATE.fullmatch(norm))


def is_gujarat_plate(normalized: Optional[str]) -> bool:
    """Check if plate belongs to Gujarat state registration (GJ prefix)."""
    if not normalized:
        return False
    return normalized.strip().upper().startswith("GJ")


def extract_plate_structure(normalized: Optional[str]) -> Dict[str, Any]:
    """Extract state code, district RTO code, series, and registration number."""
    norm = (normalized or "").strip().upper()
    
    # Check Standard State Format (e.g. GJ05AB1234)
    m = _STD_INDIAN_PLATE.fullmatch(norm)
    if m:
        state, rto, series, number = m.groups()
        rto_padded = rto.zfill(2)
        rto_name = GUJARAT_RTO_CODES.get(rto_padded) if state == "GJ" else None
        return {
            "format": "STANDARD",
            "state_code": state,
            "rto_code": rto_padded,
            "series": series or "",
            "number": number,
            "rto_jurisdiction": rto_name or f"RTO {rto_padded}",
            "is_gujarat": state == "GJ",
        }
        
    # Check BH Series (e.g. 22BH1234AA)
    m_bh = _BH_SERIES_PLATE.fullmatch(norm)
    if m_bh:
        year, bh, number, letters = m_bh.groups()
        return {
            "format": "BHARAT_SERIES",
            "state_code": "BH",
            "rto_code": year,
            "series": letters,
            "number": number,
            "rto_jurisdiction": "All-India Defense / Multi-State Commercial",
            "is_gujarat": False,
        }
        
    return {
        "format": "UNKNOWN",
        "state_code": norm[:2] if len(norm) >= 2 and norm[:2].isalpha() else None,
        "rto_code": None,
        "series": None,
        "number": None,
        "rto_jurisdiction": None,
        "is_gujarat": norm.startswith("GJ"),
    }
