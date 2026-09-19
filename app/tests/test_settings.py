import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.main import app
from app.db.models.accounts import Profile, AuthSession, DeletedAccount
from app.deps import get_db
from app.db.base import Base
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

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
    await db_session.commit()
    return u_id

@pytest.fixture
async def auth_client(db_session: AsyncSession, test_user: uuid.UUID):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_get_settings(db_session: AsyncSession, test_user: uuid.UUID):
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        from app.deps import get_current_user, get_db
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_db] = lambda: db_session
        
        response = await ac.get("/v1/settings")
        assert response.status_code == 200
        assert response.json()["data"]["email"] == "test@example.com"
        assert response.json()["data"]["ai_personalization"] is True

@pytest.mark.asyncio
async def test_update_settings(db_session: AsyncSession, test_user: uuid.UUID):
    from app.deps import get_current_user, get_db
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_db] = lambda: db_session
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.patch("/v1/settings", json={"ai_personalization": False, "tz": "Europe/London"})
        assert response.status_code == 200
        
        # Verify db
        prof = await db_session.get(Profile, test_user)
        assert prof.ai_personalization is False
        assert prof.tz == "Europe/London"

@pytest.mark.asyncio
async def test_export_data(db_session: AsyncSession, test_user: uuid.UUID):
    from app.deps import get_current_user, get_db
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_db] = lambda: db_session
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/v1/settings/export")
        assert response.status_code == 200
        data = response.json()["data"]
        assert "profile" in data
        assert data["profile"]["email"] == "test@example.com"

@pytest.mark.asyncio
async def test_delete_account(db_session: AsyncSession, test_user: uuid.UUID):
    from app.deps import get_current_user, get_db
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_db] = lambda: db_session
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/v1/settings/delete", json={"reason": "too busy"})
        assert response.status_code == 200
        
        prof = await db_session.get(Profile, test_user)
        assert prof is None
        
        res = await db_session.execute(select(DeletedAccount).where(DeletedAccount.user_id == test_user))
        tomb = res.scalar_one_or_none()
        assert tomb is not None
        assert tomb.reason == "too busy"
