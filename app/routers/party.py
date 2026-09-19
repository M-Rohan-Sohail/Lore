from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from app.db.session import get_db
from app.services.party import create_party, join_party, leave_party
from app.schemas.party import PartyCreate, PartyResponse
from app.deps import get_current_user
from app.core.envelope import success

router = APIRouter(prefix="/v1/party", tags=["party"])

@router.post("", response_model=PartyResponse)
async def create(
    payload: PartyCreate,
    user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    party = await create_party(db, user_id, payload.name)
    return success(party)

@router.post("/join/{invite_code}", response_model=PartyResponse)
async def join(
    invite_code: str,
    user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    party = await join_party(db, user_id, invite_code)
    return success(party)

@router.post("/leave")
async def leave(
    user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await leave_party(db, user_id)
    return success({"message": "Left party"})
