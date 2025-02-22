

import re
def is_valid_phone_number(phone: str) -> bool:
    """
    Validate Indian phone number format.
    Valid formats:
    - 7012345678 (10 digits)
    - +917012345678
    - +91-7012345678
    - 917012345678
    """
    pattern = r'^(?:(?:\+91|91)?[6789]\d{9})$'
    
    # Remove all non-digit characters except '+' and format number
    cleaned_phone = ''.join(c for c in phone if c.isdigit() or c == '+')
    
    # Additional validation for numbers with country code and hyphen
    if phone.startswith('+91-'):
        cleaned_phone = '+91' + phone.split('-')[1]
    
    return bool(re.match(pattern, cleaned_phone))