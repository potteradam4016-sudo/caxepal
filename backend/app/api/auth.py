from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from app.db import get_db
from app.errors import APIError
from app.models import AuthSession, Profile, User, now_ts
from app.schemas import ChangePasswordInput, Credentials, LoginInput, LoginOut, MessageOut, PasswordInput, UserOut
from app.security import DUMMY_HASH, check_password, current_principal, digest_token, hash_password, new_token
from app.services.profiles import user_payload
from app.services.rate_limit import auth_limit

router = APIRouter(prefix="/auth", tags=["인증"])

@router.post("/register", response_model=MessageOut, status_code=201, summary="아이디와 비밀번호로 가입")
def register(body: Credentials, request: Request, db=Depends(get_db)):
    auth_limit(request, body.username, "register")
    hashed = hash_password(body.password)
    if db.scalar(select(User.id).where(User.username == body.username)):
        raise APIError(409, "USERNAME_TAKEN", "이미 사용 중인 아이디입니다.")
    user = User(username=body.username, password_hash=hashed)
    db.add(user)
    try:
        db.flush()
        db.add(Profile(user_id=user.id))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise APIError(409, "USERNAME_TAKEN", "이미 사용 중인 아이디입니다.")
    return {"message": "가입이 완료되었습니다. 로그인해주세요."}

@router.post("/login", summary="로그인과 세션 토큰 발급", response_model=LoginOut)
def login(body: LoginInput, request: Request, db=Depends(get_db)):
    auth_limit(request, body.username, "login")
    user = db.scalar(select(User).where(User.username == body.username).with_for_update())
    valid = check_password(body.password, user.password_hash if user else DUMMY_HASH)
    if not user or not valid:
        raise APIError(401, "INVALID_CREDENTIALS", "아이디 또는 비밀번호가 올바르지 않습니다.")
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

@router.post("/change-password", summary="현재 비밀번호로 비밀번호 변경", response_model=MessageOut)
def change_password(body: ChangePasswordInput, principal=Depends(current_principal), db=Depends(get_db)):
    user = db.scalar(select(User).where(User.id == principal.user.id).with_for_update())
    if not check_password(body.current_password, user.password_hash):
        raise APIError(401, "INVALID_CREDENTIALS", "현재 비밀번호가 올바르지 않습니다.")
    user.password_hash = hash_password(body.new_password)
    db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
    db.commit()
    return {"message": "비밀번호를 변경했습니다. 다시 로그인해주세요."}

@router.delete("/account", summary="본인 계정 탈퇴", status_code=204)
def remove_account(body: PasswordInput, request: Request, principal=Depends(current_principal), db=Depends(get_db)):
    if not check_password(body.password, principal.user.password_hash):
        raise APIError(401, "INVALID_CREDENTIALS", "비밀번호가 올바르지 않습니다.")
    db.delete(principal.user)
    db.commit()
    return Response(status_code=204)
