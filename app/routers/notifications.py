from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import datetime

from app.db.session import get_db
from app.deps import get_current_user
from app.db.models.accounts import Profile, PushSubscription, NotificationPref
from app.core.envelope import success

router = APIRouter(prefix="/v1/notifications", tags=["notifications"])

class RegisterDeviceRequest(BaseModel):
    platform: str
    device_token: str

class UpdatePrefsRequest(BaseModel):
    recap_push: bool | None = None
    recap_email: bool | None = None
    streak_reminder: bool | None = None
    party_events: bool | None = None

@router.post("/register")
async def register_device(
    payload: RegisterDeviceRequest,
    current_user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(PushSubscription).where(PushSubscription.device_token == payload.device_token))
    sub = res.scalar_one_or_none()
    
    if sub:
        if sub.user_id != current_user_id:
            sub.user_id = current_user_id
            sub.failed_count = 0
            await db.commit()
    else:
        sub = PushSubscription(
            user_id=current_user_id,
            platform=payload.platform,
            device_token=payload.device_token
        )
        db.add(sub)
        await db.commit()
        
    return success({"registered": True})

@router.patch("/prefs")
async def update_prefs(
    payload: UpdatePrefsRequest,
    current_user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(NotificationPref).where(NotificationPref.user_id == current_user_id))
    pref = res.scalar_one_or_none()
    
    if not pref:
        pref = NotificationPref(user_id=current_user_id)
        db.add(pref)
        
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(pref, k, v)
        
    await db.commit()
    return success({"updated": True})
