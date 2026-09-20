import pytest
from unittest.mock import patch
import datetime
import zoneinfo
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.models.accounts import Profile, PushSubscription, NotificationPref
from app.db.models.platform import NotificationLog
from app.services.notifications import dispatch_notification, _is_quiet_hours
from app.jobs.push_send import process_streak_reminders

@pytest.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest.fixture
async def db_session(db_engine):
    async_session = async_sessionmaker(db_engine, expire_on_commit=False)
    async with async_session() as session:
        yield session

@pytest.fixture
async def user_profile(db_session):
    profile = Profile(
        id=uuid.uuid4(),
        display_name="Tester",
        tz="UTC",
        streak_current=5,
        last_streak_date=datetime.date(2020, 1, 1) # old date
    )
    db_session.add(profile)
    
    sub = PushSubscription(
        user_id=profile.id,
        platform="android",
        device_token="mock-token"
    )
    db_session.add(sub)
    await db_session.commit()
    return profile

@patch("app.services.notifications._is_quiet_hours", return_value=False)
@patch("app.services.notifications.send_fcm_push", return_value=True)
@pytest.mark.asyncio
async def test_dispatch_honors_caps_and_logs(mock_fcm, mock_quiet, db_session: AsyncSession, user_profile: Profile):
    # Send one party_join
    await dispatch_notification(
        session=db_session,
        user_id=user_profile.id,
        event="party_join",
        title="Hi",
        body="Join"
    )
    res = await db_session.execute(select(NotificationLog).where(NotificationLog.event == "party_join"))
    assert len(res.scalars().all()) == 1
    
    # Party join cap is 5. Let's send 4 more.
    for _ in range(4):
        await dispatch_notification(db_session, user_profile.id, "party_join", "Hi", "Join")
        
    res2 = await db_session.execute(select(NotificationLog).where(NotificationLog.event == "party_join"))
    assert len(res2.scalars().all()) == 5
    
    # 6th should be capped and NOT logged
    await dispatch_notification(db_session, user_profile.id, "party_join", "Hi", "Join")
    res3 = await db_session.execute(select(NotificationLog).where(NotificationLog.event == "party_join"))
    assert len(res3.scalars().all()) == 5

@pytest.mark.asyncio
async def test_dispatch_honors_prefs(db_session: AsyncSession, user_profile: Profile):
    # Disable party_events
    pref = NotificationPref(user_id=user_profile.id, party_events=False)
    db_session.add(pref)
    await db_session.commit()
    
    await dispatch_notification(db_session, user_profile.id, "party_join", "Hi", "Join")
    
    # Should not be logged (was not sent via any channels)
    res = await db_session.execute(select(NotificationLog).where(NotificationLog.event == "party_join"))
    assert len(res.scalars().all()) == 0

@pytest.mark.asyncio
async def test_is_quiet_hours(monkeypatch):
    import zoneinfo
    
    # Mock datetime to force local time inside quiet hours (e.g. 23:00)
    class MockDatetime(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.datetime(2023, 1, 1, 23, 0, 0, tzinfo=tz)
            
    monkeypatch.setattr(datetime, "datetime", MockDatetime)
    
    assert _is_quiet_hours("UTC") == True
    
    # Mock datetime to force local time outside quiet hours (e.g. 12:00)
    class MockDatetimeDay(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=tz)
            
    monkeypatch.setattr(datetime, "datetime", MockDatetimeDay)
    
    assert _is_quiet_hours("UTC") == False

@pytest.mark.asyncio
async def test_streak_reminders_job(db_session: AsyncSession, user_profile: Profile, monkeypatch):
    # Mock time so it's 19:00 (evening)
    class MockDatetime(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.datetime(2023, 1, 1, 19, 0, 0, tzinfo=tz)
            
    monkeypatch.setattr(datetime, "datetime", MockDatetime)
    
    # Run the job
    from sqlalchemy.ext.asyncio import async_sessionmaker
    sm = async_sessionmaker(db_session.bind, expire_on_commit=False)
    
    await process_streak_reminders(sm)
    
    # Verify reminder was sent
    res = await db_session.execute(select(NotificationLog).where(NotificationLog.event == "streak_reminder"))
    assert len(res.scalars().all()) == 1
