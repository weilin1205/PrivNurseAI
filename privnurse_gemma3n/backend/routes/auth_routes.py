from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
import re

from database import get_db
from models import User
from schemas import UserCreate, PasswordReset
from auth import get_password_hash, verify_password, create_access_token, get_current_user
from config import ACCESS_TOKEN_EXPIRE_MINUTES, AUTO_LOGIN_ENABLED, AUTO_LOGIN_USERNAME, DEMO_MODE
from demo_dependencies import check_demo_mode

router = APIRouter()

@router.get("/api/auth-config")
async def get_auth_config():
    """Get authentication configuration"""
    return {
        "auto_login_enabled": AUTO_LOGIN_ENABLED,
        "auto_login_username": AUTO_LOGIN_USERNAME if AUTO_LOGIN_ENABLED else None,
        "demo_mode": DEMO_MODE
    }

@router.post("/api/users")
async def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_demo_mode)
):
    """Create new user (admin only)"""
    # Check permissions
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only administrators can create users"
        )
    
    # Validate username format
    if not re.match("^[a-zA-Z0-9_-]{3,20}$", user.username):
        raise HTTPException(
            status_code=400,
            detail="Username must be 3-20 characters long and contain only letters, numbers, underscores, and hyphens"
        )
    
    # Check if username already exists
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(
            status_code=400,
            detail="Username already registered"
        )
    
    # Create new user with hashed password and salt
    hashed_password = get_password_hash(user.password)
    new_user = User(
        username=user.username,
        password_hash=hashed_password,
        role=user.role
    )
    
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return {"message": "User created successfully", "user_id": new_user.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """User login"""
    # If auto-login is enabled, return token for admin user
    if AUTO_LOGIN_ENABLED:
        admin_user = db.query(User).filter(User.username == AUTO_LOGIN_USERNAME).first()
        if not admin_user:
            # Create admin user if it doesn't exist
            from datetime import datetime
            admin_user = User(
                username=AUTO_LOGIN_USERNAME,
                password_hash="dummy_hash",  # Password won't be checked
                role="admin",
                created_at=datetime.utcnow()
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
        
        # Generate token for admin user
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": admin_user.username}, expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": admin_user.id,
            "username": admin_user.username,
            "role": admin_user.role
        }
    
    # Normal authentication flow
    # Query for user
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password"
        )
    
    # Verify password
    if not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password"
        )
    
    # Generate JWT token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "username": user.username,
        "role": user.role
    }

@router.post("/api/users/{user_id}/reset-password")
async def reset_password(
    password_reset: PasswordReset,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_demo_mode)
):
    """Reset password (admin only)"""
    # Check permissions
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only administrators can reset passwords"
        )
    
    # Find user
    user = db.query(User).filter(User.id == password_reset.user_id).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    # Reset password
    hashed_password = get_password_hash(password_reset.new_password)
    user.password_hash = hashed_password
    
    try:
        db.commit()
        return {"message": "Password reset successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/users")
async def get_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 10
):
    """Get all users list (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only administrators can view user list"
        )
    
    users = db.query(User).offset(skip).limit(limit).all()
    total = db.query(User).count()
    
    return {
        "items": [
            {
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "created_at": user.created_at,
                "updated_at": user.updated_at
            }
            for user in users
        ],
        "total": total
    }