from fastapi import APIRouter, Depends
from sqlalchemy import delete, select, update
from app.db import get_db
from app.errors import APIError
from app.models import Interest, Profile, ProfileInterest, now_ts
from app.schemas import InterestOut, ProfileInput, ProfileOut
from app.security import current_principal
from app.services.profiles import profile_payload

router = APIRouter(tags=["프로필·관심사"])

@router.get("/interests", summary="관심 분야와 활동 유형 사전", response_model=list[InterestOut])
def interests(db=Depends(get_db)):
    return list(db.scalars(select(Interest).order_by(Interest.type, Interest.id)))

@router.get("/profile", summary="본인의 학적·관심사 조회", response_model=ProfileOut)
def profile(principal=Depends(current_principal), db=Depends(get_db)):
    return profile_payload(db, principal.user.id)

@router.put("/profile", response_model=ProfileOut, summary="프로필과 관심사를 함께 저장")
def save_profile(body: ProfileInput, principal=Depends(current_principal), db=Depends(get_db)):
    valid_ids = set(db.scalars(select(Interest.id).where(Interest.id.in_(body.interest_ids))))
    if valid_ids != set(body.interest_ids):
        raise APIError(422, "UNKNOWN_INTEREST", "관심사 선택지에 없는 값입니다.")
    stmt = update(Profile).where(Profile.user_id == principal.user.id)
    if body.expected_version is not None:
        stmt = stmt.where(Profile.version == body.expected_version)
    result = db.execute(stmt.values(department=body.department, grade=body.grade,
        academic_status=body.academic_status, version=Profile.version + 1, updated_at=now_ts()))
    if result.rowcount != 1:
        raise APIError(409, "PROFILE_CONFLICT", "정보가 이미 변경되었습니다. 새로 조회해주세요.")
    db.execute(delete(ProfileInterest).where(ProfileInterest.user_id == principal.user.id))
    db.add_all(ProfileInterest(user_id=principal.user.id, interest_id=ident) for ident in body.interest_ids)
    db.commit()
    return profile_payload(db, principal.user.id)
