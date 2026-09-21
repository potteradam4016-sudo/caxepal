import hashlib
import hmac
import secrets
from dataclasses import dataclass
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import delete, select
from app.db import get_db
from app.errors import APIError
from app.models import AuthSession, User, now_ts

# Argon2id defaults: no custom cryptographic primitives.
hasher = PasswordHasher()
DUMMY_HASH = hasher.hash(secrets.token_urlsafe(24))
bearer = HTTPBearer(auto_error=False, scheme_name="BearerAuth")

def hash_password(password: str) -> str:
    return hasher.hash(password)

def check_password(password: str, stored_hash: str) -> bool:
    try:
        return hasher.verify(stored_hash, password)
    except (VerificationError, InvalidHashError):
        return False

def new_token() -> str:
    return secrets.token_urlsafe(32)

def digest_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

@dataclass
class Principal:
    user: User
    token_hash: str

def optional_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db=Depends(get_db),
) -> Principal | None:
    if credentials is None:
        if request.headers.get("Authorization"):
            raise APIError(401, "INVALID_SESSION", "Bearer 인증 형식을 확인해주세요.")
        return None
    if credentials.scheme.lower() != "bearer" or len(credentials.credentials) > 256:
        raise APIError(401, "INVALID_SESSION", "로그인이 필요합니다.", headers={"WWW-Authenticate": "Bearer"})
    hashed = digest_token(credentials.credentials)
    row = db.execute(select(AuthSession, User).join(User, User.id == AuthSession.user_id).where(
        AuthSession.token_hash == hashed, AuthSession.expires_at > now_ts(),
        User.email_verified.is_(True)
    )).first()
    if row is None:
        raise APIError(401, "INVALID_SESSION", "로그인이 필요하거나 세션이 만료되었습니다.",
                       headers={"WWW-Authenticate": "Bearer"})
    return Principal(row[1], hashed)

def current_principal(principal=Depends(optional_principal)) -> Principal:
    if principal is None:
        raise APIError(401, "AUTH_REQUIRED", "로그인이 필요합니다.", headers={"WWW-Authenticate": "Bearer"})
    return principal

def admin_principal(principal=Depends(current_principal)) -> Principal:
    if not principal.user.is_admin:
        raise APIError(403, "ADMIN_REQUIRED", "관리자 권한이 필요합니다.")
    return principal
