from fastapi import HTTPException, status
from config import DEMO_MODE

def check_demo_mode():
    """
    Dependency to check if demo mode is enabled.
    Raises HTTPException if demo mode is active and a write operation is attempted.
    """
    if DEMO_MODE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Write Access Restricted",
                "message": "Thank you for your interest! This application is currently in demo mode and does not support data submissions or changes.",
                "demo_mode": True
            }
        )
    return True