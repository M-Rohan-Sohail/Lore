import pytest
import uuid
import datetime
from unittest.mock import patch
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.db.base import Base
from app.db.models.accounts import Profile
from app.db.models.party import Party, PartyMember
from app.db.models.quests import Quest, QuestLog
from app.services.party import create_party, join_party
from app.services.recaps import generate_party_recap
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

@pytest.mark.asyncio
@patch("app.services.recaps.narrate")
async def test_party_recap_leak(mock_narrate, db_session_maker):
    async with db_session_maker() as db:
        u1 = uuid.uuid4()
        u2 = uuid.uuid4()
        db.add(Profile(id=u1, tz="UTC"))
        db.add(Profile(id=u2, tz="UTC"))
        await db.commit()
        
        party = await create_party(db, u1, "Leak Test Party")
        await join_party(db, u2, party.invite_code)
        
        quest_id = uuid.uuid4()
        db.add(Quest(id=quest_id, user_id=u1, type="main", title="Test Quest", category="vit", difficulty="easy", source="template", status="active"))
        db.add(QuestLog(user_id=u1, quest_id=quest_id, completed_at=datetime.datetime.now(datetime.timezone.utc), tz_at_log="UTC", local_date=datetime.date(2026, 9, 2), xp_awarded=10, counted_for_xp=True, client_key="c1", note_text="SUPER_SECRET_NOTE"))
        await db.commit()
        
        week_start = datetime.date(2026, 9, 1)
        mock_narrate.return_value = AIResponse(content='{"title": "Party Version", "body_text": "Text 1"}', provider="test", model="test", tokens_in=10, tokens_out=10)
        
        recap = await generate_party_recap(db, party.id, week_start)
        
        # Verify prompt did not leak SUPER_SECRET_NOTE
        call_args = mock_narrate.call_args[0][0] # req
        assert "SUPER_SECRET_NOTE" not in call_args.user_prompt
        assert recap.provider == "gateway"
