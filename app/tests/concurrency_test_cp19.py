import asyncio
import uuid
import datetime
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.base import Base
from app.db.models.accounts import Profile
from app.db.models.quests import Quest
from app.deps import get_current_user
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

async def main():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    db_session_maker = async_sessionmaker(engine, expire_on_commit=False)
    
    test_user_id = uuid.uuid4()
    
    async with db_session_maker() as session:
        p = Profile(id=test_user_id, display_name="Load Tester", tz="UTC")
        session.add(p)
        
        # Create a single quest to hammer
        quest_id = uuid.uuid4()
        q = Quest(id=quest_id, user_id=test_user_id, title="Hammer Quest", type="main", category="physical", difficulty="medium", source="template", status="active")
        session.add(q)
        
        await session.commit()

    async def _get_current_user():
        return test_user_id
        
    async def _get_db():
        async with db_session_maker() as session:
            yield session

    app.dependency_overrides[get_current_user] = _get_current_user
    from app.db.session import get_db
    app.dependency_overrides[get_db] = _get_db

    print("Starting concurrency test for /v1/quests/{id}/complete")
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Fire 50 requests concurrently
        tasks = []
        for i in range(50):
            req = client.post(
                f"/v1/quests/{quest_id}/complete",
                json={"tz": "UTC", "note_text": "Concurrent completion"},
                headers={"Idempotency-Key": f"key_{i}"} # using different keys to simulate same quest completed many times, or same key to test idempotency
            )
            tasks.append(req)
            
        responses = await asyncio.gather(*tasks)
        
        successes = [r for r in responses if r.status_code == 200]
        errors = [r for r in responses if r.status_code != 200]
        
        print(f"Total requests: {len(responses)}")
        print(f"Successes: {len(successes)}")
        print(f"Errors: {len(errors)}")
        if errors:
            print(f"Sample error: {errors[0].status_code} {errors[0].text}")

    app.dependency_overrides.clear()
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
