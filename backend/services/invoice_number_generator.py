from datetime import datetime
from typing import Optional

from sqlmodel import Session, select, func

from models import Invoice


def generate_next_invoice_number(session: Session, profile_id: int = None) -> str:
    """
    Generate the next invoice number globally (not per profile).
    Format: "YY | NNN" where YY is current year and NNN is sequential number.
    
    IMPORTANT: German tax law (§ 14 UStG) requires invoice numbers to be 
    unique and sequential across the entire business, not per profile/location.
    
    Args:
        session: Database session
        profile_id: Not used anymore, kept for backward compatibility
        
    Returns:
        Next invoice number in format "YY | NNN"
    """
    current_year = datetime.now().year
    year_suffix = str(current_year)[-2:]  # Get last 2 digits of year
    
    # Find the highest number for this year GLOBALLY (all profiles)
    year_prefix = f"{year_suffix} |"
    
    # Query for ALL invoices with numbers starting with current year pattern
    # Remove profile_id filter to make it global
    stmt = select(Invoice.number).where(
        Invoice.number.startswith(year_prefix)
    )
    
    existing_numbers = session.exec(stmt).all()
    
    if not existing_numbers:
        # First invoice of the year globally
        next_number = 1
    else:
        # Extract numeric parts and find maximum across ALL profiles
        numeric_parts = []
        for number in existing_numbers:
            try:
                # Split "25 | 123" -> ["25", "123"]
                parts = number.split(" | ")
                if len(parts) == 2:
                    numeric_parts.append(int(parts[1]))
            except (ValueError, IndexError):
                # Skip malformed numbers
                continue
        
        if numeric_parts:
            next_number = max(numeric_parts) + 1
        else:
            next_number = 1
    
    # Format with leading zeros (minimum 3 digits)
    return f"{year_suffix} | {next_number:03d}"


def get_preview_invoice_number(session: Session, profile_id: int = None) -> str:
    """
    Get a preview of what the next invoice number would be without creating an invoice.
    Numbers are generated globally, not per profile (German tax law compliance).
    
    Args:
        session: Database session
        profile_id: Not used anymore, kept for backward compatibility
        
    Returns:
        Preview invoice number in format "YY | NNN"
    """
    return generate_next_invoice_number(session)


def validate_invoice_number_format(number: str) -> bool:
    """
    Validate if an invoice number follows the correct format.
    
    Args:
        number: Invoice number to validate
        
    Returns:
        True if format is valid, False otherwise
    """
    import re
    return bool(re.match(r"^\d{2} \| \d{3,}$", number))
