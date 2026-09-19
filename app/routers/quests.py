from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from app.db.base import get_db
from app.services.quests import complete_quest
from app.deps import get_current_user
from app.core.envelope import success

router = APIRouter(prefix="/v1/quests", tags=["quests"])

class CompleteQuestRequest(BaseModel):
    note_text: str | None = None
    tz: str = "UTC"

@router.post("/{quest_id}/complete")
async def complete(
    quest_id: uuid.UUID,
    request: CompleteQuestRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await complete_quest(
        db, user_id, quest_id, idempotency_key, request.tz, request.note_text
    )
    return success(result)
