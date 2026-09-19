import pytest
import uuid
import datetime
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.db.base import Base
from app.db.models.accounts import Profile
from app.services.growth import maybe_grant_founding_player, maybe_show_invite_nudge

@pytest.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest.fixture
async def session_factory(db_engine):
    return async_sessionmaker(db_engine, expire_on_commit=False)

@pytest.fixture
async def db_session(session_factory):
    async with session_factory() as session:
        yield session

@pytest.mark.asyncio
async def test_founding_player_race(session_factory):
    # Create 6 users
    user_ids = [uuid.uuid4() for _ in range(6)]
    
    async with session_factory() as setup_session:
        for uid in user_ids:
            profile = Profile(id=uid, display_name=f"User {uid}", tz="UTC")
            setup_session.add(profile)
        await setup_session.commit()
        
    async def worker(uid):
        async with session_factory() as session:
            await maybe_grant_founding_player(session, uid, cap=3)
            await session.commit()
            
    # Run 6 workers concurrently
    await asyncio.gather(*(worker(uid) for uid in user_ids))
    
    async with session_factory() as check_session:
        # Check that exactly 3 got the badge
        stmt = select(Profile).where(Profile.founding_player == True)
        result = await check_session.execute(stmt)
        founding_profiles = result.scalars().all()
        assert len(founding_profiles) == 3

@pytest.mark.asyncio
async def test_invite_nudge_frequency(db_session: AsyncSession):
    uid = uuid.uuid4()
    profile = Profile(id=uid, display_name="Test", tz="UTC")
    db_session.add(profile)
    await db_session.commit()
    
    # First time, should show nudge
    show_1 = await maybe_show_invite_nudge(db_session, uid)
    assert show_1 is True
    
    # Immediate second call, should not show
    show_2 = await maybe_show_invite_nudge(db_session, uid)
    assert show_2 is False
    
    # Move last_invite_nudge_at back 31 days
    profile = await db_session.get(Profile, uid)
    profile.last_invite_nudge_at = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=31)
    db_session.add(profile)
    await db_session.commit()
    
    # Should show again
    show_3 = await maybe_show_invite_nudge(db_session, uid)
    assert show_3 is True

def test_growth_pressure_mechanics():
    # Scan growth.py and card_templates.py for banned words
    import os
    banned_tokens = ["countdown", "urgency", "scarcity", "loot box", "flash sale"]
    
    files_to_check = [
        "app/services/growth.py",
        "app/services/card_templates.py"
    ]
    
    for fpath in files_to_check:
        with open(fpath, "r") as f:
            content = f.read().lower()
            for token in banned_tokens:
                assert token not in content, f"Found banned token '{token}' in {fpath}"
