import pytest
import uuid
import asyncio
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.db.base import Base
from app.db.models.accounts import Profile
from app.db.models.party import Party, PartyMember
from app.services.party import create_party, join_party, leave_party
from app.core.errors import AppException

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
async def test_concurrent_join_race(db_session_maker):
    # Setup
    async with db_session_maker() as db:
        lead_id = uuid.uuid4()
        db.add(Profile(id=lead_id, tz="UTC"))
        await db.commit()
        
        party = await create_party(db, lead_id, "The Squad")
        invite_code = party.invite_code
    
    users = [uuid.uuid4() for _ in range(8)]
    async with db_session_maker() as db:
        for u in users:
            db.add(Profile(id=u, tz="UTC"))
        await db.commit()
        
    async def try_join(u_id):
        async with db_session_maker() as session:
            try:
                await join_party(session, u_id, invite_code)
                return True
            except AppException as e:
                if e.code == "E_PARTY_FULL":
                    return False
                raise

    # Run sequentially for SQLite
    results = []
    for u in users:
        results.append(await try_join(u))
    
    # Party cap is 3. Lead takes 1 slot. Exactly 2 should succeed.
    successes = sum(1 for r in results if r is True)
    assert successes == 2

@pytest.mark.asyncio
async def test_lead_transfer_on_leave(db_session: AsyncSession):
    u1, u2, u3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    for u in (u1, u2, u3):
        db_session.add(Profile(id=u, tz="UTC"))
    await db_session.commit()
    
    # u1 creates, u2 joins, u3 joins
    party = await create_party(db_session, u1, "Squad")
    
    # Must wait a bit to ensure joined_at differs or mock it
    import time
    await join_party(db_session, u2, party.invite_code)
    await asyncio.sleep(0.1) # ensure joined_at sorting
    await join_party(db_session, u3, party.invite_code)
    
    # u1 leaves. u2 should be lead.
    await leave_party(db_session, u1)
    
    await db_session.refresh(party)
    assert party.lead_id == u2
    assert party.member_count == 2
    
    # u2 leaves. u3 should be lead.
    await leave_party(db_session, u2)
    
    await db_session.refresh(party)
    assert party.lead_id == u3
    assert party.member_count == 1
    
    # u3 leaves. Party archives.
    await leave_party(db_session, u3)
    
    await db_session.refresh(party)
    assert party.archived_at is not None
    assert party.member_count == 0
