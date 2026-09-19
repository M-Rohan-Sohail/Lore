import asyncio
import datetime
import zoneinfo
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import select

from app.db.models.accounts import Profile
from app.services.notifications import dispatch_notification

async def process_streak_reminders(session_maker: async_sessionmaker):
    """
    Finds users who are at risk of losing their streak and sends a reminder.
    Runs periodically.
    """
    async with session_maker() as db:
        # We process in batches of 1000 for scalability
        # In a real system, we'd paginate or use an index on streak_current > 0
        stmt = select(Profile).where(Profile.streak_current > 0)
        res = await db.execute(stmt)
        profiles = res.scalars().all()
        
        for profile in profiles:
            try:
                zi = zoneinfo.ZoneInfo(profile.tz)
            except Exception:
                zi = datetime.timezone.utc
                
            local_time = datetime.datetime.now(zi)
            local_date = local_time.date()
            
            # Check if it's evening in their timezone (between 6 PM and 10 PM)
            if 18 <= local_time.hour < 22:
                # Have they completed a quest today?
                if profile.last_streak_date != local_date:
                    # They haven't! Send reminder.
                    # dispatch_notification will handle caps and preferences
                    await dispatch_notification(
                        session=db,
                        user_id=profile.id,
                        event="streak_reminder",
                        title="Your streak is at risk!",
                        body=f"Complete a quest before midnight to keep your {profile.streak_current}-day streak alive 🔥",
                    )
