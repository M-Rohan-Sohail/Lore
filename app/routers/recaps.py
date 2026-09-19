from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import datetime
from app.db.base import get_db
from app.db.models.recaps import Recap, RecapJob
from app.schemas.recaps import RecapResponse
from app.deps import get_current_user
from app.core.envelope import success

router = APIRouter(prefix="/v1/recaps", tags=["recaps"])

@router.get("", response_model=list[RecapResponse])
async def list_recaps(
    user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Recap).where(Recap.owner_id == user_id, Recap.scope == "user").order_by(Recap.week_start.desc())
    result = await db.execute(stmt)
    recaps = result.scalars().all()
    
    return success([{
        "id": r.id,
        "scope": r.scope,
        "owner_id": r.owner_id,
        "week_start": r.week_start,
        "payload": r.payload,
        "provider": r.provider,
        "degraded_level": r.degraded_level,
        "episode_number": r.episode_number,
        "regen_count": r.regen_count
    } for r in recaps])

@router.post("/trigger_job")
async def trigger_recap_job(
    week_start: datetime.date,
    user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # This endpoint is just for testing/demoing the async job
    now = datetime.datetime.now(datetime.timezone.utc)
    job = RecapJob(
        scope="user",
        owner_id=user_id,
        week_start=week_start,
        run_after=now
    )
    db.add(job)
    await db.commit()
    return success({"job_id": job.id})
