import re
from typing import Optional

def normalize_phone_e164(phone: Optional[str]) -> Optional[str]:
    """
    Normalizes raw phone numbers to E.164 standard: +[country_code][subscriber_number].
    Strips whitespace, parentheses, dashes, slashes, and dots.
    Examples:
        "+1 (415) 555-2671" -> "+14155552671"
        "+91 98765-43210"   -> "+919876543210"
        "9876543210"        -> "+919876543210"
        "0014155552671"     -> "+14155552671"
    """
    if not phone:
        return None

    cleaned = str(phone).strip()
    if not cleaned:
        return None

    # Replace leading 00 with +
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]

    # Extract digits and check if leading +
    has_plus = cleaned.startswith("+")
    digits = re.sub(r"\D", "", cleaned)

    if not digits:
        return None

    if has_plus:
        return f"+{digits}"

    # If 10 digits without country code:
    # India mobile numbers start with 6, 7, 8, or 9
    if len(digits) == 10:
        if digits[0] in "6789":
            return f"+91{digits}"
        else:
            return f"+1{digits}"

    # If 11 digits starting with 1 (US with leading 1)
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"

    # If 12 digits starting with 91 (India with leading 91)
    if len(digits) == 12 and digits.startswith("91"):
        return f"+{digits}"

    # If 11 digits starting with 0 (e.g. 09876543210 trunk prefix for India)
    if len(digits) == 11 and digits.startswith("0") and digits[1] in "6789":
        return f"+91{digits[1:]}"

    # Default fallback: prepend +
    return f"+{digits}"

def are_phones_equal(phone1: Optional[str], phone2: Optional[str]) -> bool:
    """
    Determines if two phone representations refer to the same E.164 number.
    """
    n1 = normalize_phone_e164(phone1)
    n2 = normalize_phone_e164(phone2)
    if not n1 or not n2:
        return False
    return n1 == n2
