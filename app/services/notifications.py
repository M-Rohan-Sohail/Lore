import datetime
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func

from app.db.models.accounts import PushSubscription, NotificationPref, Profile
from app.db.models.platform import NotificationLog
from app.notifications.providers.fcm import send_fcm_push
from app.notifications.providers.apns import send_apns_push
from app.notifications.providers.email import send_email

# Matrix defining default behaviors per event
NOTIFICATION_MATRIX = {
    "weekly_recap": {
        "channels": ["push", "email"],
        "pref_key": "recap_push", # For push
        "email_pref_key": "recap_email",
        "cap": 1, # Max 1 per 6 days roughly (we do it simply by checking last 5 days)
        "quiet_hours_respect": True
    },
    "streak_reminder": {
        "channels": ["push"],
        "pref_key": "streak_reminder",
        "cap": 1, # Max 1 per day
        "quiet_hours_respect": True
    },
    "party_join": {
        "channels": ["push"],
        "pref_key": "party_events",
        "cap": 5, # Max 5 per day
        "quiet_hours_respect": True
    }
}

async def _check_cap(session: AsyncSession, user_id: uuid.UUID, event: str, cap: int) -> bool:
    """Returns True if user is UNDER the cap for the given event."""
    # Check since beginning of day UTC, except for weekly_recap which is last 5 days
    now = datetime.datetime.now(datetime.timezone.utc)
    if event == "weekly_recap":
        since = now - datetime.timedelta(days=5)
    else:
        since = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
    res = await session.execute(
        select(func.count(NotificationLog.id))
        .where(NotificationLog.user_id == user_id, NotificationLog.event == event, NotificationLog.created_at >= since)
    )
    count = res.scalar() or 0
    return count < cap

def _is_quiet_hours(tz: str) -> bool:
    """
    Returns True if local time in `tz` is between 22:00 and 08:00.
    Falls back to UTC if tz parsing fails.
    """
    import zoneinfo
    try:
        zi = zoneinfo.ZoneInfo(tz)
    except Exception:
        zi = datetime.timezone.utc
    
    local_time = datetime.datetime.now(zi)
    return local_time.hour >= 22 or local_time.hour < 8

async def log_notification(session: AsyncSession, user_id: uuid.UUID, event: str):
    session.add(NotificationLog(user_id=user_id, event=event))
    await session.commit()

async def prune_subscription(session: AsyncSession, sub_id: uuid.UUID):
    await session.execute(delete(PushSubscription).where(PushSubscription.id == sub_id))
    await session.commit()

async def increment_subscription_failure(session: AsyncSession, sub: PushSubscription):
    sub.failed_count += 1
    if sub.failed_count >= 5:
        await prune_subscription(session, sub.id)
    else:
        await session.commit()

async def dispatch_notification(
    session: AsyncSession,
    user_id: uuid.UUID,
    event: str,
    title: str,
    body: str,
    data: dict = None,
    html: str = None
) -> None:
    """
    Dispatches a notification using the matrix rules.
    """
    matrix = NOTIFICATION_MATRIX.get(event)
    if not matrix:
        return # Unknown event
        
    # Get user profile and preferences
    user = await session.get(Profile, user_id)
    if not user:
        return
        
    # Check quiet hours
    if matrix["quiet_hours_respect"] and _is_quiet_hours(user.tz):
        return
        
    # Check cap
    if not await _check_cap(session, user_id, event, matrix["cap"]):
        return

    # Check preferences
    res_pref = await session.execute(select(NotificationPref).where(NotificationPref.user_id == user_id))
    pref = res_pref.scalar_one_or_none()
    
    # Defaults are True if pref row doesn't exist
    push_enabled = True
    email_enabled = True
    if pref:
        push_enabled = getattr(pref, matrix["pref_key"], True) if matrix.get("pref_key") else True
        email_enabled = getattr(pref, matrix.get("email_pref_key", ""), True) if matrix.get("email_pref_key") else True

    sent_any = False

    # Send Push
    if "push" in matrix["channels"] and push_enabled:
        res_subs = await session.execute(select(PushSubscription).where(PushSubscription.user_id == user_id))
        subs = res_subs.scalars().all()
        for sub in subs:
            success = False
            try:
                if sub.platform == "android":
                    success = await send_fcm_push(sub.device_token, title, body, data)
                elif sub.platform == "ios":
                    success = await send_apns_push(sub.device_token, title, body, data)
                    
                if not success:
                    # Permanently dead token (unregistered)
                    await prune_subscription(session, sub.id)
                else:
                    sub.failed_count = 0
                    sub.last_success_at = datetime.datetime.now(datetime.timezone.utc)
                    await session.commit()
                    sent_any = True
            except Exception:
                await increment_subscription_failure(session, sub)

    # Send Email
    if "email" in matrix["channels"] and email_enabled and html and user.email:
        try:
            success = await send_email(user.email, title, html)
            if success:
                sent_any = True
        except Exception:
            pass # We don't prune email aggressively

    if sent_any:
        await log_notification(session, user_id, event)
