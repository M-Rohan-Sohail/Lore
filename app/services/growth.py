import uuid
import datetime
import hashlib
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text, update
from app.db.models.accounts import Profile
import asyncio

_sqlite_lock = asyncio.Lock()

async def maybe_grant_founding_player(db: AsyncSession, user_id: uuid.UUID, cap: int = 1000) -> None:
    """
    Grants the founding_player badge if the user hasn't been checked yet,
    and if there are fewer than `cap` players who already have it.
    Uses pg_advisory_xact_lock to prevent concurrent race conditions over the cap.
    """
    # Quick un-locked read first to avoid locking if already checked
    stmt_quick = select(Profile.founding_player_checked_at).where(Profile.id == user_id)
    result = await db.execute(stmt_quick)
    checked_at = result.scalar()
    
    if checked_at is not None:
        return
        
    # Lock for check-and-grant to prevent >cap concurrent activations
    # We use a deterministic advisory lock key for this specific feature
    lock_key = int(hashlib.md5(b"founding_player_grant").hexdigest()[:15], 16)
    
    # Needs to be a raw query because SQLAlchemy doesn't natively expose advisory locks
    # We use pg_advisory_xact_lock so it releases automatically at commit/rollback
    # Only run on postgres, sqlite tests will use a python asyncio lock
    now = datetime.datetime.now(datetime.timezone.utc)
    
    if db.bind and db.bind.dialect.name == "postgresql":
        await db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key})
        await _do_grant(db, user_id, cap, now)
    else:
        async with _sqlite_lock:
            await _do_grant(db, user_id, cap, now)
            
async def _do_grant(db: AsyncSession, user_id: uuid.UUID, cap: int, now: datetime.datetime) -> None:
    stmt = select(Profile).where(Profile.id == user_id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()
    
    if not profile or profile.founding_player_checked_at is not None:
        return
        
    # Count current founding players
    stmt_count = select(func.count()).where(Profile.founding_player == True)
    count_result = await db.execute(stmt_count)
    current_count = count_result.scalar() or 0
    
    if current_count < cap:
        profile.founding_player = True
        
    profile.founding_player_checked_at = now
    db.add(profile)
    # The transaction will be committed by the caller (complete_quest)

async def maybe_show_invite_nudge(db: AsyncSession, user_id: uuid.UUID) -> bool:
    """
    Returns True if the user should see an invite nudge, and updates the timestamp.
    Returns False otherwise.
    Frequency is capped at once per 30 days.
    """
    stmt = select(Profile).where(Profile.id == user_id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()
    
    if not profile:
        return False
        
    now = datetime.datetime.now(datetime.timezone.utc)
    
    if profile.last_invite_nudge_at is None:
        should_show = True
    else:
        # Avoid days_since_nudge math with tzinfo if one is naive, but both should be aware
        delta = now - profile.last_invite_nudge_at
        should_show = delta.days >= 30
        
    if should_show:
        profile.last_invite_nudge_at = now
        db.add(profile)
        await db.commit()
        return True
        
    return False
