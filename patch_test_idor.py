with open("app/tests/test_idor_suite.py", "r") as f:
    content = f.read()

replacement = """from app.deps import get_db
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.db.base import Base

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
def override_get_db(db_session_maker):
    async def _override_get_db():
        async with db_session_maker() as session:
            yield session
    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()
"""

# Find where to insert it. Just before u1_token
import re
content = re.sub(r'(@pytest\.fixture\ndef u1_token)', replacement + r'\n\1', content)

with open("app/tests/test_idor_suite.py", "w") as f:
    f.write(content)
