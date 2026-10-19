"""
Security and Cryptography Engine.

Uses the native 'bcrypt' library directly (eliminating passlib version bugs)
and provides offline JWT token creation/verification.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import bcrypt
import hashlib
import jwt
from core.config import settings


def hash_password(plain_password: str) -> str:
    """Computes a salted, one-way bcrypt hash of a plain text password."""
    # Bcrypt operates on bytes and has a 72-byte limit
    pwd_bytes = plain_password.encode('utf-8')[:72]
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, stored_hash_or_plain: str) -> bool:
    """
    Verifies a password against the stored database value.
    - If stored value is bcrypt: verifies using bcrypt.checkpw().
    - If stored value is legacy plain text or SHA256: checks fallback cleanly.
    """
    if not stored_hash_or_plain or not plain_password:
        return False

    # 1. Attempt standard bcrypt verification
    try:
        pwd_bytes = plain_password.encode('utf-8')[:72]
        hash_bytes = stored_hash_or_plain.strip().encode('utf-8')
        if bcrypt.checkpw(pwd_bytes, hash_bytes):
            return True
    except Exception:
        pass

    # 2. Fallback: Check plain text match
    if plain_password == stored_hash_or_plain:
        return True

    # 3. Fallback: Check legacy SHA-256
    sha256_hash = hashlib.sha256(plain_password.encode('utf-8')).hexdigest()
    if sha256_hash.lower() == stored_hash_or_plain.strip().lower():
        return True

    return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Cryptographically signs an offline JWT access token for user sessions."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodes and verifies the cryptographic signature of an incoming JWT token."""
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None