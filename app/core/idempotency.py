import uuid
from fastapi import Header, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.db.models.quests import QuestLog
from app.db.models.recaps import RecapJob
from app.core.errors import AppException

async def get_client_key(client_key: str | None = Header(None)) -> str:
    if not client_key:
        raise AppException(code="E_VALIDATION", message="Missing client_key header", retryable=False)
    return client_key

async def check_idempotency(user_id: uuid.UUID, client_key: str, session: AsyncSession) -> bool:
    """Returns True if the action has already been processed."""
    log = await session.scalar(select(QuestLog).where(QuestLog.user_id == user_id, QuestLog.client_key == client_key))
    if log:
        return True
    return False
