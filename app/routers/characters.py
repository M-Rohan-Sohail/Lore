from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from app.db.base import get_db
from app.schemas.characters import QuizSubmission, CharacterResponse
from app.services.characters import process_quiz
from app.deps import get_current_user
from app.core.envelope import success

router = APIRouter(prefix="/v1/characters", tags=["characters"])

@router.post("/quiz", response_model=CharacterResponse)
async def submit_quiz(
    submission: QuizSubmission,
    user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    character = await process_quiz(db, user_id, submission)
    return success(character)
