import pytest
import uuid
import datetime
from unittest.mock import patch, AsyncMock
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.db.base import Base
from app.db.models.accounts import Profile
from app.db.models.quests import Quest, QuestLog
from app.db.models.recaps import Recap, RecapJob
from app.services.recaps import generate_user_recap
from app.jobs.recap_tick import process_recap_job
from app.schemas.ai import AIResponse

@pytest.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest.fixture
async def db_session_maker(db_engine):
    return async_sessionmaker(db_engine, expire_on_commit=False)

@pytest.fixture
async def db_session(db_session_maker):
    async with db_session_maker() as session:
        yield session

@pytest.mark.asyncio
async def test_quiet_week(db_session: AsyncSession):
    user_id = uuid.uuid4()
    profile = Profile(id=user_id, tz="UTC")
    db_session.add(profile)
    await db_session.commit()
    
    week_start = datetime.date(2026, 9, 1)
    
    # Generate recap with 0 quests
    recap = await generate_user_recap(db_session, user_id, week_start)
    
    assert recap.episode_number is None
    assert recap.provider == "template"
    assert recap.payload["title"] == "A Quiet Week"

@pytest.mark.asyncio
@patch("app.services.recaps.narrate")
async def test_regenerate_pins_stats(mock_narrate, db_session: AsyncSession):
    user_id = uuid.uuid4()
    profile = Profile(id=user_id, tz="UTC")
    db_session.add(profile)
    
    quest_id = uuid.uuid4()
    quest = Quest(id=quest_id, user_id=user_id, type="main", title="Test", category="vit", difficulty="easy", source="template", status="active")
    db_session.add(quest)
    
    # Log 1 quest
    log = QuestLog(user_id=user_id, quest_id=quest_id, completed_at=datetime.datetime.now(datetime.timezone.utc), tz_at_log="UTC", local_date=datetime.date(2026, 9, 2), xp_awarded=10, counted_for_xp=True, client_key="123")
    db_session.add(log)
    await db_session.commit()
    
    week_start = datetime.date(2026, 9, 1)
    
    # First Generation
    mock_narrate.return_value = AIResponse(content='{"title": "First Version", "body_text": "Text 1"}', provider="test", model="test", tokens_in=10, tokens_out=10)
    recap1 = await generate_user_recap(db_session, user_id, week_start)
    
    assert recap1.episode_number == 1
    assert recap1.payload["title"] == "First Version"
    assert recap1.payload["stat_deltas"]["vit"] == 1
    
    # Second Generation (Force Regen)
    mock_narrate.return_value = AIResponse(content='{"title": "Second Version", "body_text": "Text 2"}', provider="test", model="test", tokens_in=10, tokens_out=10)
    recap2 = await generate_user_recap(db_session, user_id, week_start, force_regen=True)
    
    assert recap2.id == recap1.id
    assert recap2.episode_number == 1
    assert recap2.payload["title"] == "Second Version"
    assert recap2.payload["stat_deltas"]["vit"] == 1 # Stats pinned!

@pytest.mark.asyncio
@patch("app.jobs.recap_tick.generate_user_recap")
async def test_recap_job_poison_pill(mock_gen, db_session_maker):
    # Tests the exact poison-pill failure and MissingGreenlet crash fix
    async with db_session_maker() as db:
        user_id = uuid.uuid4()
        profile = Profile(id=user_id, tz="UTC")
        db.add(profile)
        
        job = RecapJob(scope="user", owner_id=user_id, week_start=datetime.date(2026, 9, 1), run_after=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1), attempts=2)
        db.add(job)
        await db.commit()
        
        job_id = job.id
    
    # Mock to throw exception
    mock_gen.side_effect = Exception("Simulated DB failure during generation")
    
    # Run the processor
    await process_recap_job(db_session_maker)
    
    # Check job state
    async with db_session_maker() as db:
        job = await db.get(RecapJob, job_id)
        assert job.status == "failed"
        assert job.attempts == 3
        assert "Simulated DB failure" in job.last_error
