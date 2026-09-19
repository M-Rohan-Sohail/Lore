import pytest
import uuid
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.db.base import Base
from app.db.models.accounts import Profile
from app.db.models.quests import Quest, QuestLog, StreakEvent
from app.services.quests import complete_quest
from app.core.errors import AppException
from unittest.mock import patch

@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session
        
    await engine.dispose()

@pytest.mark.asyncio
@patch("app.services.quests.track_event")
async def test_complete_quest_idempotent(mock_track, db_session: AsyncSession):
    user_id = uuid.uuid4()
    profile = Profile(id=user_id, tz="UTC")
    db_session.add(profile)
    
    quest_id = uuid.uuid4()
    quest = Quest(id=quest_id, user_id=user_id, type="main", title="Test", category="vit", difficulty="easy", source="template", status="active")
    db_session.add(quest)
    await db_session.commit()
    
    # First time
    client_key = "1234-abcd"
    res1 = await complete_quest(db_session, user_id, quest_id, client_key, "UTC", "did it")
    
    assert res1["xp_awarded"] == 10
    assert res1["new_streak"] == 1
    
    # Replay
    with pytest.raises(AppException) as exc:
        await complete_quest(db_session, user_id, quest_id, client_key, "UTC", "did it again")
        
    assert exc.value.code == "E_REPLAY"

@pytest.mark.asyncio
@patch("app.services.quests.track_event")
async def test_complete_quest_xp_cap(mock_track, db_session: AsyncSession):
    user_id = uuid.uuid4()
    profile = Profile(id=user_id, tz="UTC")
    db_session.add(profile)
    await db_session.commit()
    
    quest_id = uuid.uuid4()
    
    # Log 6 quests
    for i in range(6):
        res = await complete_quest(db_session, user_id, quest_id, str(uuid.uuid4()), "UTC", "text")
        assert res["xp_awarded"] == 10
        
    # 7th quest
    res7 = await complete_quest(db_session, user_id, quest_id, str(uuid.uuid4()), "UTC", "text")
    assert res7["xp_awarded"] == 0
