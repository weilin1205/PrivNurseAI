from passlib.context import CryptContext
from secrets import token_hex
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import HTTPException, Depends, Request
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from sqlalchemy.orm import Session
from models import User
from database import get_db
from config import SECRET_KEY, ALGORITHM, SEPARATOR, AUTO_LOGIN_ENABLED, AUTO_LOGIN_USERNAME

# Password encryption setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme configuration
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="api/login",
    auto_error=False  # Don't auto-error to handle auto-login
)

def get_password_hash(password: str) -> str:
    """Hash password with salt"""
    salt = token_hex(16)
    salted_password = password + salt
    hashed_password = pwd_context.hash(salted_password)
    # Combine hash and salt
    return f"{hashed_password}{SEPARATOR}{salt}"

def verify_password(plain_password: str, stored_password: str) -> bool:
    """Verify password against stored hash and salt"""
    try:
        # Separate hash and salt from stored password
        hashed_password, salt = stored_password.split(SEPARATOR)
        salted_password = plain_password + salt
        return pwd_context.verify(salted_password, hashed_password)
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: timedelta = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_or_create_admin_user(db: Session):
    """Get or create admin user for auto-login"""
    admin_user = db.query(User).filter(User.username == AUTO_LOGIN_USERNAME).first()
    if admin_user:
        return admin_user
    
    # Create admin user if it doesn't exist
    admin_user = User(
        username=AUTO_LOGIN_USERNAME,
        password_hash="dummy_hash_for_auto_login",
        role="admin",
        created_at=datetime.utcnow()
    )
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    return admin_user

async def get_current_user(
    request: Request = None,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """Get current authenticated user"""
    # If auto-login is enabled, always return admin user
    if AUTO_LOGIN_ENABLED:
        return get_or_create_admin_user(db)
    
    # Normal authentication flow
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
        
    return user