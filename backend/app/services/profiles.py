from sqlalchemy import select
from app.models import Profile, ProfileInterest, Interest

def profile_payload(db, user_id: str) -> dict:
    profile = db.get(Profile, user_id)
    choices = list(db.scalars(select(Interest).join(ProfileInterest,
        ProfileInterest.interest_id == Interest.id).where(
        ProfileInterest.user_id == user_id).order_by(Interest.type, Interest.id)))
    complete = bool(profile and profile.department and profile.grade and profile.academic_status
                    and {"field", "activity"} <= {i.type for i in choices})
    return {"user_id": user_id, "department": profile.department if profile else None,
            "grade": profile.grade if profile else None,
            "academic_status": profile.academic_status if profile else None,
            "interests": [{"id": i.id, "name": i.name, "type": i.type} for i in choices],
            "onboarding_complete": complete, "version": profile.version if profile else 0,
            "updated_at": profile.updated_at if profile else 0}

def user_payload(db, user):
    return {"id": user.id, "username": user.username,
            "is_admin": user.is_admin,
            "onboarding_complete": profile_payload(db, user.id)["onboarding_complete"]}
