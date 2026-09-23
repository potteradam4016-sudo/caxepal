from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from app.db import get_db
from app.errors import APIError
from app.models import AuthSession, AuthToken, Profile, User, now_ts
from app.schemas import Credentials, EmailInput, LoginInput, LoginOut, MessageOut, PasswordInput, ResetInput, TokenInput, UserOut
from app.security import DUMMY_HASH, check_password, current_principal, digest_token, hash_password, new_token
from app.services.mail import deliver_or_record
from app.services.profiles import user_payload
from app.services.rate_limit import auth_limit

router = APIRouter(prefix="/auth", tags=["인증"])
GENERIC = {"message": "요청을 접수했습니다. 해당 계정으로 처리 가능한 경우 안내 메일을 보냅니다."}

def issue_action_token(db, user, purpose):
    token = new_token()
    db.add(AuthToken(token_hash=digest_token(token), user_id=user.id, purpose=purpose,
                     expires_at=now_ts() + (86400 if purpose == "verify" else 1800)))
    return token

@router.post("/register", response_model=MessageOut, status_code=202, summary="이메일로 가입")
def register(body: Credentials, request: Request, db=Depends(get_db)):
    auth_limit(request, body.email, "register")
    # Always hash, including duplicate emails, to avoid a trivial timing difference.
    hashed = hash_password(body.password)
    if db.scalar(select(User.id).where(User.email == body.email)):
        return GENERIC
    user = User(email=body.email, password_hash=hashed)
    db.add(user)
    try:
        db.flush()
        db.add(Profile(user_id=user.id))
        token = issue_action_token(db, user, "verify")
        db.commit()
    except IntegrityError:
        db.rollback()
        return GENERIC
    deliver_or_record(request, user.id, user.email, token, "verify")
    return GENERIC

@router.post("/resend-verification", summary="이메일 확인 메일 재발송", response_model=MessageOut, status_code=202)
def resend(body: EmailInput, request: Request, db=Depends(get_db)):
    auth_limit(request, body.email, "resend")
    user = db.scalar(select(User).where(User.email == body.email))
    if user and not user.email_verified:
        token = issue_action_token(db, user, "verify")
        db.commit()
        deliver_or_record(request, user.id, user.email, token, "verify")
    return GENERIC

def consume_action(db, token, purpose):
    # DELETE ... RETURNING is atomic. The token cannot succeed twice concurrently.
    user_id = db.execute(delete(AuthToken).where(AuthToken.token_hash == digest_token(token),
        AuthToken.purpose == purpose, AuthToken.expires_at > now_ts()).returning(AuthToken.user_id)).scalar_one_or_none()
    if user_id is None:
        raise APIError(400, "INVALID_TOKEN", "확인 링크가 만료되었거나 올바르지 않습니다.")
    return user_id

@router.post("/verify-email", summary="이메일 소유 확인", response_model=MessageOut)
def verify(body: TokenInput, db=Depends(get_db)):
    user_id = consume_action(db, body.token, "verify")
    db.execute(update(User).where(User.id == user_id).values(email_verified=True))
    db.execute(delete(AuthToken).where(AuthToken.user_id == user_id, AuthToken.purpose == "verify"))
    db.commit()
    return {"message": "이메일 확인이 완료되었습니다. 로그인해주세요."}

@router.post("/login", summary="로그인과 세션 토큰 발급", response_model=LoginOut)
def login(body: LoginInput, request: Request, db=Depends(get_db)):
    auth_limit(request, body.email, "login")
    # Serialize login with password-reset updates on PostgreSQL so an old password
    # cannot create a session after a concurrent reset has revoked sessions.
    user = db.scalar(select(User).where(User.email == body.email).with_for_update())
    valid = check_password(body.password, user.password_hash if user else DUMMY_HASH)
    if not user or not valid:
        raise APIError(401, "INVALID_CREDENTIALS", "이메일 또는 비밀번호가 올바르지 않습니다.")
    if not user.email_verified:
        raise APIError(403, "EMAIL_NOT_VERIFIED", "먼저 이메일 소유를 확인해주세요.")
    token, expires = new_token(), now_ts() + request.app.state.settings.session_hours * 3600
    db.add(AuthSession(token_hash=digest_token(token), user_id=user.id, expires_at=expires))
    db.commit()
    return {"access_token": token, "token_type": "bearer", "expires_at": expires, "user": user_payload(db, user)}

@router.get("/me", summary="현재 로그인한 계정 조회", response_model=UserOut)
def me(principal=Depends(current_principal), db=Depends(get_db)):
    return user_payload(db, principal.user)

@router.post("/logout", summary="현재 세션 로그아웃", status_code=204)
def logout(principal=Depends(current_principal), db=Depends(get_db)):
    db.execute(delete(AuthSession).where(AuthSession.token_hash == principal.token_hash))
    db.commit()
    return Response(status_code=204)

@router.post("/logout-all", summary="본인의 모든 세션 로그아웃", status_code=204)
def logout_all(principal=Depends(current_principal), db=Depends(get_db)):
    db.execute(delete(AuthSession).where(AuthSession.user_id == principal.user.id))
    db.commit()
    return Response(status_code=204)

@router.post("/forgot-password", summary="비밀번호 재설정 메일 요청", response_model=MessageOut, status_code=202)
def forgot(body: EmailInput, request: Request, db=Depends(get_db)):
    auth_limit(request, body.email, "forgot")
    user = db.scalar(select(User).where(User.email == body.email))
    if user and user.email_verified:
        token = issue_action_token(db, user, "reset")
        db.commit()
        deliver_or_record(request, user.id, user.email, token, "reset")
    return GENERIC

@router.post("/reset-password", summary="비밀번호 재설정", response_model=MessageOut)
def reset(body: ResetInput, db=Depends(get_db)):
    hashed = hash_password(body.password)
    user_id = consume_action(db, body.token, "reset")
    db.execute(update(User).where(User.id == user_id).values(password_hash=hashed))
    db.execute(delete(AuthSession).where(AuthSession.user_id == user_id))
    db.execute(delete(AuthToken).where(AuthToken.user_id == user_id))
    db.commit()
    return {"message": "비밀번호를 변경했습니다. 다시 로그인해주세요."}

@router.delete("/account", summary="본인 계정 탈퇴", status_code=204)
def remove_account(body: PasswordInput, request: Request, principal=Depends(current_principal), db=Depends(get_db)):
    if not check_password(body.password, principal.user.password_hash):
        raise APIError(401, "INVALID_CREDENTIALS", "비밀번호가 올바르지 않습니다.")
    db.delete(principal.user)
    db.commit()
    return Response(status_code=204)
