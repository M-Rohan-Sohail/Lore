import uuid
import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from app.db.models.quests import Quest, QuestLog, StreakEvent
from app.db.models.accounts import Profile
from app.services.progression import calculate_streak_update, XP_PER_QUEST, MAX_QUESTS_XP_PER_DAY
from app.core.errors import AppException
from app.core.analytics import track_event
from app.services.growth import maybe_grant_founding_player

async def complete_quest(
    db: AsyncSession,
    user_id: uuid.UUID,
    quest_id: uuid.UUID,
    client_key: str,
    tz_str: str,
    note_text: str | None = None
) -> dict:
    # Check Idempotency
    existing = await db.execute(select(QuestLog).where(QuestLog.user_id == user_id, QuestLog.client_key == client_key))
    if existing.scalar_one_or_none():
        raise AppException(code="E_REPLAY", message="Quest already logged", retryable=False)
        
    import zoneinfo
    try:
        tz = zoneinfo.ZoneInfo(tz_str)
    except Exception:
        tz = zoneinfo.ZoneInfo("UTC")
        
    now = datetime.datetime.now(datetime.timezone.utc)
    local_date = now.astimezone(tz).date()
    
    # Check anti-gaming cap (how many counted_for_xp logs today?)
    stmt = select(func.count(QuestLog.id)).where(
        QuestLog.user_id == user_id,
        QuestLog.local_date == local_date,
        QuestLog.counted_for_xp == True
    )
    today_counted = await db.scalar(stmt)
    
    xp_awarded = XP_PER_QUEST if today_counted < MAX_QUESTS_XP_PER_DAY else 0
    counted_for_xp = xp_awarded > 0
    
    # Process streak
    profile = await db.get(Profile, user_id)
    if not profile:
        raise ValueError("Profile not found")
        
    new_streak, new_freeze, event_type = calculate_streak_update(
        local_date, profile.last_streak_date, profile.last_freeze_used_date, profile.streak_current
    )
    
    # Update profile
    profile.streak_current = new_streak
    profile.last_streak_date = local_date if event_type != "none" else profile.last_streak_date
    profile.last_freeze_used_date = new_freeze
    profile.xp_total += xp_awarded
    
    from app.services.progression import level_for_xp
    new_level = level_for_xp(profile.xp_total)
    profile.level = new_level
    
    log = QuestLog(
        user_id=user_id,
        quest_id=quest_id,
        completed_at=now,
        tz_at_log=tz_str,
        local_date=local_date,
        note_text=note_text,
        xp_awarded=xp_awarded,
        counted_for_xp=counted_for_xp,
        client_key=client_key
    )
    db.add(log)
    
    if event_type != "none":
        se = StreakEvent(
            user_id=user_id,
            local_date=local_date,
            kind=event_type,
            meta={"xp_delta": xp_awarded}
        )
        db.add(se)
        
    await maybe_grant_founding_player(db, user_id)
        
    await db.commit()
    
    await track_event(user_id, "quest_completed", {
        "xp_awarded": xp_awarded,
        "new_streak": new_streak,
        "event_type": event_type
    })
    
    return {
        "xp_awarded": xp_awarded,
        "new_streak": new_streak,
        "event_type": event_type,
        "level": new_level
    }
