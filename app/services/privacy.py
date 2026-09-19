import uuid
import json
import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert

from app.db.models.accounts import Profile, NotificationPref, PushSubscription, DeletedAccount, AuthSession, Entitlement
from app.db.models.characters import Character
from app.db.models.party import PartyMember
from app.db.models.recaps import Recap
from app.db.models.platform import AiUsage, NotificationLog

async def export_user_data(session: AsyncSession, user_id: uuid.UUID) -> dict:
    """
    Returns a comprehensive dictionary of all personal data for GDPR compliance.
    """
    data = {}
    
    # Profile
    profile = await session.get(Profile, user_id)
    if profile:
        data["profile"] = {
            "id": str(profile.id),
            "display_name": profile.display_name,
            "birth_ym": profile.birth_ym,
            "tz": profile.tz,
            "level": profile.level,
            "xp_total": profile.xp_total,
            "streak_current": profile.streak_current,
            "ai_personalization": profile.ai_personalization,
            "email": profile.email,
            "created_at": profile.created_at.isoformat() if profile.created_at else None
        }
        
    # Characters
    res_chars = await session.execute(select(Character).where(Character.user_id == user_id))
    data["characters"] = [
        {
            "id": str(c.id),
            "class_name": c.class_name,
            "tagline": c.tagline,
            "origin_blurb": c.origin_blurb
        }
        for c in res_chars.scalars().all()
    ]
    
    # Recaps
    res_recaps = await session.execute(select(Recap).where(Recap.owner_id == user_id))
    data["recaps"] = [
        {
            "id": str(r.id),
            "week_start": r.week_start.isoformat(),
            "summary_text": r.summary_text
        }
        for r in res_recaps.scalars().all()
    ]
    
    # Push subscriptions
    res_push = await session.execute(select(PushSubscription).where(PushSubscription.user_id == user_id))
    data["push_subscriptions"] = [
        {"platform": p.platform, "created_at": p.created_at.isoformat()}
        for p in res_push.scalars().all()
    ]
    
    return data

async def delete_user_account(session: AsyncSession, user_id: uuid.UUID, reason: str = None) -> None:
    """
    Deletes all personal data and writes a tombstone record.
    Foreign key ON DELETE CASCADE will handle characters, recaps, push subscriptions, etc.
    But we also want to explicitly delete the profile and log the tombstone.
    """
    
    # 1. Create tombstone
    stmt_tomb = insert(DeletedAccount).values(
        user_id=user_id,
        reason=reason,
        deleted_at=datetime.datetime.now(datetime.timezone.utc)
    ).on_conflict_do_nothing()
    await session.execute(stmt_tomb)
    
    # 2. Delete Profile (this will cascade to almost everything else)
    await session.execute(delete(Profile).where(Profile.id == user_id))
    
    # 3. Revoke active sessions just in case
    await session.execute(
        delete(AuthSession).where(AuthSession.user_id == user_id)
    )
    
    await session.commit()
