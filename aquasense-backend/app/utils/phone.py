"""Phone number validation and normalization utility."""

import re


def normalize_indian_phone(phone: str) -> str:
    """Normalize valid Indian mobile numbers to international format (+91XXXXXXXXXX).

    Accepts standard input formats:
    - 9876543210 (10 digits starting with 6, 7, 8, or 9)
    - +919876543210
    - 91 9876543210 / 91-9876543210
    - 09876543210

    Raises ValueError if the number is clearly invalid or not an Indian mobile number.
    """
    if not phone or not phone.strip():
        raise ValueError("Phone number cannot be empty.")

    # Remove spaces, hyphens, and parentheses
    cleaned = re.sub(r"[\s\-\(\)]", "", phone.strip())

    # Check for invalid characters (only digits allowed after optional leading +)
    if cleaned.startswith("+"):
        if not cleaned[1:].isdigit():
            raise ValueError("Phone number contains invalid characters.")
        if not cleaned.startswith("+91"):
            raise ValueError("Only Indian phone numbers (+91) are supported.")
        digits = cleaned[3:]
        if len(digits) != 10 or digits[0] not in "123456789":
            raise ValueError("Invalid Indian mobile number format after +91.")
        return cleaned

    if not cleaned.isdigit():
        raise ValueError("Phone number contains invalid characters.")

    # Check 12 digits starting with country code 91
    if len(cleaned) == 12 and cleaned.startswith("91"):
        digits = cleaned[2:]
        if digits[0] in "123456789":
            return f"+91{digits}"
        raise ValueError("Invalid Indian mobile number format.")

    # Check 11 digits starting with trunk code 0
    if len(cleaned) == 11 and cleaned.startswith("0"):
        digits = cleaned[1:]
        if digits[0] in "123456789":
            return f"+91{digits}"
        raise ValueError("Invalid Indian mobile number format.")

    # Check standard 10 digits
    if len(cleaned) == 10:
        if cleaned[0] in "123456789":
            return f"+91{cleaned}"
        raise ValueError("Indian mobile numbers must start with a digit between 1 and 9.")

    raise ValueError("Invalid Indian phone number format. Must be a valid 10-digit mobile number.")


def mask_phone_number(phone: str | None) -> str:
    """Mask sensitive phone number for safe logging and API responses.

    Example:
        '+919876543210' -> '+91******3210'
        '9876543210' -> '******3210'
    """
    if not phone:
        return ""
    phone_str = str(phone).strip()
    if len(phone_str) <= 4:
        return "*" * len(phone_str)

    if phone_str.startswith("+91") and len(phone_str) > 7:
        prefix = "+91"
        suffix = phone_str[-4:]
        middle_len = len(phone_str) - len(prefix) - len(suffix)
        return f"{prefix}{'*' * max(middle_len, 3)}{suffix}"

    suffix = phone_str[-4:]
    prefix_len = len(phone_str) - 4
    return f"{'*' * prefix_len}{suffix}"
