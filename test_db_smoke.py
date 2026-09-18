import asyncio
from app.db.session import engine
from app.db.base import Base

async def test_db():
    async with engine.begin() as conn:
        # Just running a simple statement to verify tables exist
        await conn.run_sync(Base.metadata.reflect)
        tables = Base.metadata.tables.keys()
        print(f"Success! Found tables: {list(tables)}")

if __name__ == "__main__":
    asyncio.run(test_db())
