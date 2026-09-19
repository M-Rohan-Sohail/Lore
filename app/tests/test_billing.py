import pytest
import datetime
import uuid
import json
import hmac
import hashlib
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.db.base import Base
from app.db.models.accounts import Profile, Entitlement
from app.db.models.platform import BillingWebhookEvent
from app.services.billing import process_stripe_webhook, is_plus_entitled
from app.billing.stripe_client import STRIPE_WEBHOOK_SECRET, verify_stripe_signature

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
async def user_id(db_session):
    u_id = uuid.uuid4()
    profile = Profile(id=u_id, tz="UTC")
    db_session.add(profile)
    await db_session.commit()
    return u_id

def sign_payload(payload: dict) -> str:
    timestamp = int(datetime.datetime.now().timestamp())
    payload_str = json.dumps(payload, separators=(',', ':'))
    signed_payload = f"{timestamp}.".encode("utf-8") + payload_str.encode("utf-8")
    sig = hmac.new(
        STRIPE_WEBHOOK_SECRET.encode("utf-8"),
        signed_payload,
        hashlib.sha256
    ).hexdigest()
    return f"t={timestamp},v1={sig}"

@pytest.mark.asyncio
async def test_verify_stripe_signature():
    payload = {"type": "checkout.session.completed"}
    payload_str = json.dumps(payload, separators=(',', ':'))
    sig = sign_payload(payload)
    
    assert verify_stripe_signature(payload_str.encode("utf-8"), sig) is True
    assert verify_stripe_signature(payload_str.encode("utf-8"), "t=123,v1=bad") is False

@pytest.mark.asyncio
async def test_billing_webhook_lifecycle(db_session: AsyncSession, user_id: uuid.UUID):
    # 1. Purchase
    event_id_1 = str(uuid.uuid4())
    payload_1 = {
        "id": event_id_1,
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "client_reference_id": str(user_id),
                "customer": "cus_123",
                "subscription": "sub_123"
            }
        }
    }
    await process_stripe_webhook(db_session, payload_1)
    
    ent_res = await db_session.execute(select(Entitlement).where(Entitlement.user_id == user_id))
    ent = ent_res.scalar_one_or_none()
    assert ent is not None
    assert ent.status == "active"
    assert ent.provider_subscription_id == "sub_123"
    assert await is_plus_entitled(db_session, user_id) is True
    
    # 2. Replay attack (should be no-op)
    # We will try to send the same checkout.session.completed event
    # If it was not idempotent, it might crash or duplicate
    await process_stripe_webhook(db_session, payload_1)
    
    ev_res = await db_session.execute(select(BillingWebhookEvent).where(BillingWebhookEvent.id == event_id_1))
    assert len(ev_res.scalars().all()) == 1
    
    # 3. Grace period (past_due)
    event_id_2 = str(uuid.uuid4())
    payload_2 = {
        "id": event_id_2,
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_123",
                "status": "past_due"
            }
        }
    }
    await process_stripe_webhook(db_session, payload_2)
    
    await db_session.refresh(ent)
    assert ent.status == "past_due"
    assert ent.past_due_since is not None
    assert await is_plus_entitled(db_session, user_id) is True # Grace period is active
    
    # Simulate grace period expired (we mock the past_due_since date)
    ent.past_due_since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=8)
    await db_session.commit()
    assert await is_plus_entitled(db_session, user_id) is False # Expired
    
    # 4. Recovered
    event_id_3 = str(uuid.uuid4())
    payload_3 = {
        "id": event_id_3,
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_123",
                "status": "active"
            }
        }
    }
    await process_stripe_webhook(db_session, payload_3)
    
    await db_session.refresh(ent)
    assert ent.status == "active"
    assert ent.past_due_since is None
    assert await is_plus_entitled(db_session, user_id) is True
    
    # 5. Canceled
    event_id_4 = str(uuid.uuid4())
    payload_4 = {
        "id": event_id_4,
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": "sub_123"
            }
        }
    }
    await process_stripe_webhook(db_session, payload_4)
    
    await db_session.refresh(ent)
    assert ent.status == "inactive"
    assert await is_plus_entitled(db_session, user_id) is False
