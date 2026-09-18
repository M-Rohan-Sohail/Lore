from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
import uuid
from datetime import datetime, timezone
from app.db.session import get_db
from app.db.models.accounts import AuthSession
from app.core.envelope import success
from app.schemas.auth import LogoutResponse
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
