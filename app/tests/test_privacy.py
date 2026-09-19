import pytest
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

from app.db.base import Base
from app.db.models.accounts import Profile, AuthSession, DeletedAccount
from app.db.models.characters import Character
from app.services.privacy import export_user_data, delete_user_account

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
async def test_user(db_session: AsyncSession):
    u_id = uuid.uuid4()
    profile = Profile(
        id=u_id,
        display_name="Privacy Tester",
        email="test@example.com"
    )
    db_session.add(profile)
    
    char = Character(
        id=uuid.uuid4(),
        user_id=u_id,
        class_name="Mage",
        tagline="Test Char",
        origin_blurb="test blurb",
        generated_by="test"
    )
    db_session.add(char)
    
    auth = AuthSession(
        id="test_session_id",
        user_id=u_id
    )
    db_session.add(auth)
    
    await db_session.commit()
    return u_id

@pytest.mark.asyncio
async def test_export_user_data(db_session: AsyncSession, test_user: uuid.UUID):
    data = await export_user_data(db_session, test_user)
    
    assert "profile" in data
    assert data["profile"]["display_name"] == "Privacy Tester"
    assert data["profile"]["email"] == "test@example.com"
    
    assert "characters" in data
    assert len(data["characters"]) == 1
    assert data["characters"][0]["class_name"] == "Mage"
    
    assert "recaps" in data
    assert len(data["recaps"]) == 0
    
    assert "push_subscriptions" in data

@pytest.mark.asyncio
async def test_delete_user_account(db_session: AsyncSession, test_user: uuid.UUID):
    await delete_user_account(db_session, test_user, reason="testing")
    
    # Verify profile is gone
    prof = await db_session.get(Profile, test_user)
    assert prof is None
    
    # Verify auth session is gone
    res = await db_session.execute(select(AuthSession).where(AuthSession.user_id == test_user))
    assert len(res.scalars().all()) == 0
    
    # Verify tombstone exists
    res_tomb = await db_session.execute(select(DeletedAccount).where(DeletedAccount.user_id == test_user))
    tomb = res_tomb.scalar_one_or_none()
    assert tomb is not None
    assert tomb.reason == "testing"
