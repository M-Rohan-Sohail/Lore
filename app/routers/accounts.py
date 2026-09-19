from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
import uuid
from datetime import datetime, timezone
from app.db.session import get_db
from app.db.models.accounts import AuthSession
from app.core.envelope import success
from app.schemas.auth import LogoutResponse
from app.schemas.accounts import OnboardingRequest, OnboardingResponse
from app.services.accounts import complete_onboarding
from app.deps import get_current_user, get_current_session_id

router = APIRouter(prefix="/v1/accounts", tags=["accounts"])

@router.post("/logout")
async def logout(
    session_id: str = Depends(get_current_session_id),
    user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = insert(AuthSession).values(
        id=uuid.UUID(session_id),
        user_id=user_id,
        revoked_at=datetime.now(timezone.utc)
    ).on_conflict_do_nothing(index_elements=['id'])
    
    await db.execute(stmt)
    await db.commit()
    
    return success({"status": "ok"})

@router.post("/onboard", response_model=OnboardingResponse)
async def onboard(
    request: OnboardingRequest,
    user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    blocked = await complete_onboarding(db, user_id, request)
    return success(OnboardingResponse(status="ok", age_gate_blocked=blocked))
