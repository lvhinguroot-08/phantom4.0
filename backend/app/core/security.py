from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union
import bcrypt
import jwt

from app.core.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its bcrypt hash."""
    try:
        if not plain_password or not hashed_password:
            return False
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Hash a password securely using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def create_access_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate a signed JWT access token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode: Dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }

    if extra_claims:
        to_encode.update(extra_claims)

    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Generate a signed JWT refresh token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

    to_encode: Dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
    }

    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT token payload."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")


# =========================================================================
# File Upload Hardening: Magic Bytes & Anti-Malware Validation
# =========================================================================

DANGEROUS_EXTENSIONS = {
    ".exe", ".sh", ".php", ".py", ".bat", ".js", ".vbs", ".cmd",
    ".dll", ".scr", ".jsp", ".asp", ".aspx", ".cgi", ".pl", ".bin",
}

VALID_MAGIC_SIGNATURES = [
    b"ftyp",                      # MP4 / ISO Media
    b"RIFF",                      # AVI / WAV
    b"\x1a\x45\xdf\xa3",          # WebM / Matroska MKV
    b"\xff\xd8\xff",              # JPEG
    b"\x89PNG\r\n\x1a\n",          # PNG
    b"GIF8",                      # GIF
    b"\x00\x00\x00",              # MP4 Box Header prefix
]


def validate_media_file_magic_bytes(header_bytes: bytes, filename: str) -> bool:
    """
    Validates binary header magic bytes of uploaded media files.
    Blocks files disguised as video or image containing executable scripts.
    """
    if not filename or not header_bytes:
        return False

    # Check extension
    dot_idx = filename.rfind(".")
    if dot_idx != -1:
        ext = filename[dot_idx:].lower()
        if ext in DANGEROUS_EXTENSIONS:
            return False

    # Check magic header bytes
    prefix_32 = header_bytes[:32]

    # MP4 inspection: usually contains 'ftyp' within first 16 bytes
    if b"ftyp" in prefix_32:
        return True

    # RIFF AVI inspection: starts with 'RIFF' and has 'AVI ' at byte 8
    if prefix_32.startswith(b"RIFF") and b"AVI" in prefix_32:
        return True

    # MKV / WebM
    if prefix_32.startswith(b"\x1a\x45\xdf\xa3"):
        return True

    # JPEG / PNG images
    if prefix_32.startswith(b"\xff\xd8\xff") or prefix_32.startswith(b"\x89PNG\r\n\x1a\n"):
        return True

    # Safe fallback for generic MP4 streams (e.g. 00 00 00 ... ftyp)
    for sig in VALID_MAGIC_SIGNATURES:
        if sig in prefix_32:
            return True

    return False


# =========================================================================
# Zero-Trust CCTV Stream Token Signing (HMAC-SHA256)
# =========================================================================

def create_stream_access_token(camera_id: str, officer_id: str = "sentinel_operator", valid_seconds: int = 300) -> str:
    """
    Generates a cryptographically signed HMAC token for authorized CCTV streaming.
    Prevents unauthorized scraping or replay of sensitive police feeds.
    """
    payload = {
        "cam": camera_id.lower().strip(),
        "sub": officer_id,
        "exp": datetime.now(timezone.utc) + timedelta(seconds=valid_seconds),
        "type": "stream_auth",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def verify_stream_access_token(token: str, camera_id: str) -> bool:
    """Validates if the provided stream token is authentic, unexpired, and matches camera ID."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        if payload.get("type") != "stream_auth":
            return False
        return payload.get("cam") == camera_id.lower().strip()
    except Exception:
        return False
