import uuid
import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update
from app.db.models.accounts import Profile
from app.schemas.accounts import OnboardingRequest
from app.core.analytics import track_event

async def complete_onboarding(db: AsyncSession, user_id: uuid.UUID, data: OnboardingRequest) -> bool:
    try:
        birth_date = datetime.datetime.strptime(data.birth_ym, "%Y-%m").date()
    except ValueError:
        birth_date = datetime.date(2000, 1, 1)
        
    today = datetime.datetime.now(datetime.timezone.utc).date()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    
    age_gate_blocked = age < 13
    now = datetime.datetime.now(datetime.timezone.utc)
    
    stmt = update(Profile).where(Profile.id == user_id).values(
        birth_ym=data.birth_ym,
        tz=data.tz,
        consent_shown_at=now if data.consent else None,
        age_gate_blocked_at=now if age_gate_blocked else None
    )
    
    await db.execute(stmt)
    await db.commit()
    
    await track_event(user_id, "onboarding_completed", {
        "age_gate_blocked": age_gate_blocked,
        "tz": data.tz
    })
    
    return age_gate_blocked
