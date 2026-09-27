import pytest
import datetime
import uuid
from unittest.mock import patch, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.db.models.quests import Quest, QuestLog
from app.db.models.recaps import Recap
from app.db.models.accounts import Profile
from app.services.recaps import generate_user_recap
import jwt
from app.config import settings

def create_access_token(user_id: uuid.UUID) -> str:
    return jwt.encode(
        {"sub": str(user_id), "session_id": str(uuid.uuid4()), "aud": "authenticated"},
        "dummy_secret_for_tests_must_not_be_empty",
        algorithm="HS256"
    )

@pytest.fixture
def test_user_id():
    return uuid.uuid4()

@pytest.fixture
async def setup_test_user(db_session: AsyncSession, test_user_id):
    p = Profile(id=test_user_id, display_name="Outage Tester", tz="UTC")
    db_session.add(p)
    await db_session.commit()
    return test_user_id

@pytest.fixture
def auth_headers(test_user_id):
    return {"Authorization": f"Bearer dummy_token"}

@pytest.mark.asyncio
@patch("app.ai.providers.groq.generate", new_callable=AsyncMock)
@patch("app.ai.providers.gemini.generate", new_callable=AsyncMock)
@patch("app.ai.providers.openrouter.generate", new_callable=AsyncMock)
async def test_ai_outage_quest_completion(
    mock_openrouter, mock_gemini, mock_groq,
    db_session: AsyncSession, setup_test_user, auth_headers: dict
):
    test_user_id = setup_test_user
    
    # Mock all AI providers to raise Exception
    mock_openrouter.side_effect = Exception("OpenRouter is down")
    mock_gemini.side_effect = Exception("Gemini is down")
    mock_groq.side_effect = Exception("Groq is down")
    
    # 1. Create a quest
    quest_id = uuid.uuid4()
    q = Quest(id=quest_id, user_id=test_user_id, title="Survive Outage", type="main", category="physical", difficulty="medium", source="template", status="active")
    db_session.add(q)
    await db_session.commit()
    
    # 2. Complete the quest
    client = TestClient(app)
    res = client.post(
        f"/v1/quests/{quest_id}/complete",
        json={"tz": "UTC", "note_text": "Did my best"},
        headers={**auth_headers, "Idempotency-Key": "outage_test_key"}
    )
    
    assert res.status_code == 200
    data = res.json()["data"]
    
    # Assert XP is awarded despite AI failing (if AI was even involved, it wouldn't block)
    assert data["xp_awarded"] > 0
    assert "new_streak" in data
    
    stmt = select(QuestLog).where(QuestLog.user_id == test_user_id)
    logs = (await db_session.execute(stmt)).scalars().all()
    assert len(logs) == 1

@pytest.mark.asyncio
@patch("app.ai.providers.groq.generate", new_callable=AsyncMock)
@patch("app.ai.providers.gemini.generate", new_callable=AsyncMock)
@patch("app.ai.providers.openrouter.generate", new_callable=AsyncMock)
@patch("app.services.recaps.calculate_deltas")
async def test_ai_outage_recap_generation(
    mock_calc_deltas, mock_openrouter, mock_gemini, mock_groq,
    db_session: AsyncSession, setup_test_user
):
    test_user_id = setup_test_user
    mock_calc_deltas.return_value = {"physical": 1}
    
    # Mock all AI providers to raise Exception
    mock_openrouter.side_effect = Exception("OpenRouter is down")
    mock_gemini.side_effect = Exception("Gemini is down")
    mock_groq.side_effect = Exception("Groq is down")
    
    week_start = datetime.datetime.now(datetime.timezone.utc).date()
    
    # Try generating a recap directly using the service function
    recap = await generate_user_recap(db_session, test_user_id, week_start, force_regen=True)
    
    assert recap is not None
    assert recap.degraded_level == "template"
    assert recap.provider == "template"
    assert recap.payload["title"] == "Episode 1: Steady Progress"

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.db.base import Base
from app.db.session import get_db

@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"

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

@pytest.fixture(autouse=True)
def override_get_db(db_session_maker, test_user_id):
    async def _get_db():
        async with db_session_maker() as session:
            yield session
    
    async def _get_current_user():
        return test_user_id

    from app.deps import get_current_user
    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_current_user] = _get_current_user
    yield
    app.dependency_overrides.clear()
