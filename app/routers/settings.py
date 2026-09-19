import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel

from app.db.session import get_db
from app.deps import get_current_user
from app.core.envelope import success
from app.services.privacy import export_user_data, delete_user_account
from app.db.models.accounts import Profile

router = APIRouter(prefix="/v1/settings", tags=["settings"])

class UpdateSettingsRequest(BaseModel):
    ai_personalization: bool | None = None
    tz: str | None = None

class DeleteAccountRequest(BaseModel):
    reason: str | None = None

@router.get("")
async def get_settings(
    current_user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    profile = await db.get(Profile, current_user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
        
    return success({
        "ai_personalization": profile.ai_personalization,
        "tz": profile.tz,
        "email": profile.email
    })

@router.patch("")
async def update_settings(
    payload: UpdateSettingsRequest,
    current_user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        return success({"status": "no changes"})
        
    stmt = update(Profile).where(Profile.id == current_user_id).values(**update_data)
    await db.execute(stmt)
    await db.commit()
    return success({"status": "updated"})

@router.get("/export")
async def export_data(
    current_user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    data = await export_user_data(db, current_user_id)
    return success(data)

@router.post("/delete")
async def delete_account(
    payload: DeleteAccountRequest,
    current_user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await delete_user_account(db, current_user_id, payload.reason)
    return success({"status": "deleted"})
