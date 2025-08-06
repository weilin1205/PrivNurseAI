"""
Validators for data validation
"""
from typing import Optional

# Valid patient category values
VALID_PATIENT_CATEGORIES = ['NHI General', 'NHI Injury', 'Self-Pay']

def validate_patient_category(category: str) -> str:
    """
    Validate and normalize patient category
    
    This handles common mistakes like:
    - 'NHI Insurance' -> 'NHI General'
    - Case sensitivity issues
    """
    if not category:
        raise ValueError("Patient category is required")
    
    # Direct match
    if category in VALID_PATIENT_CATEGORIES:
        return category
    
    # Common mistake mappings
    category_lower = category.lower()
    if 'insurance' in category_lower and 'nhi' in category_lower:
        return 'NHI General'
    
    # Case-insensitive match
    for valid_cat in VALID_PATIENT_CATEGORIES:
        if category.lower() == valid_cat.lower():
            return valid_cat
    
    # If no match found, raise error with helpful message
    raise ValueError(
        f"'{category}' is not a valid patient category. "
        f"Valid options are: {', '.join(VALID_PATIENT_CATEGORIES)}"
    )