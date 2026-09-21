import hashlib
import hmac
from app.db import dialect_insert
from app.errors import APIError
from app.models import RateBucket, now_ts

def check_limit(factory, secret: str, identity: str, limit: int, period: int = 900) -> None:
    now = now_ts()
    key = hmac.new(secret.encode(), identity.encode(), hashlib.sha256).hexdigest()
    window = now // period
    with factory() as db:
        ins = dialect_insert(db, RateBucket).values(
            key=key, window=window, count=1, expires_at=(window + 2) * period)
        stmt = ins.on_conflict_do_update(index_elements=["key", "window"],
            set_={"count": RateBucket.count + 1}).returning(RateBucket.count)
        count = db.execute(stmt).scalar_one()
        db.commit()
    if count > limit:
        raise APIError(429, "RATE_LIMITED", "요청이 많습니다. 잠시 후 다시 시도해주세요.",
            headers={"Retry-After": str((window + 1) * period - now)})

def auth_limit(request, email: str, action: str):
    settings = request.app.state.settings
    client = request.client.host if request.client else "unknown"
    # Separate buckets: distributed guessing and multi-address attacks are both bounded.
    for identity, limit in [
        (f"auth:{action}:email:{email}", settings.auth_limit_per_15_minutes),
        (f"auth:{action}:ip:{client}", settings.auth_limit_per_15_minutes * 3),
    ]:
        check_limit(request.app.state.sessions, settings.secret_key, identity, limit)
