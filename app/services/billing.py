import uuid
import datetime
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.db.models.platform import BillingWebhookEvent
from app.db.models.accounts import Entitlement
from app.core.errors import AppException

async def is_plus_entitled(session: AsyncSession, user_id: uuid.UUID) -> bool:
    """
    Returns True if the user has an active Plus entitlement.
    """
    res = await session.execute(
        select(Entitlement).where(Entitlement.user_id == user_id)
    )
    ent = res.scalar_one_or_none()
    if not ent:
        return False
        
    if ent.status == "active":
        return True
    elif ent.status == "past_due":
        # Grace period is 7 days.
        if ent.past_due_since:
            past_due = ent.past_due_since
            if past_due.tzinfo is None:
                past_due = past_due.replace(tzinfo=datetime.timezone.utc)
            now = datetime.datetime.now(datetime.timezone.utc)
            if (now - past_due).days <= 7:
                return True
                
    return False

async def process_stripe_webhook(session: AsyncSession, payload: dict) -> None:
    """
    Process Stripe webhooks idempotently.
    """
    event_id = payload.get("id")
    event_type = payload.get("type")
    
    if not event_id or not event_type:
        return
        
    # Idempotency check
    stmt = insert(BillingWebhookEvent).values(
        id=event_id,
        type=event_type
    ).on_conflict_do_nothing(index_elements=['id'])
    
    res = await session.execute(stmt)
    if res.rowcount == 0:
        # Event already processed
        return
        
    data = payload.get("data", {}).get("object", {})
    
    if event_type == "checkout.session.completed":
        client_reference_id = data.get("client_reference_id")
        if not client_reference_id:
            return
            
        user_id = uuid.UUID(client_reference_id)
        customer_id = data.get("customer")
        subscription_id = data.get("subscription")
        
        # Create or update entitlement
        stmt_ent = insert(Entitlement).values(
            id=uuid.uuid4(),
            user_id=user_id,
            plan="plus",
            status="active",
            source="stripe",
            provider_customer_id=customer_id,
            provider_subscription_id=subscription_id,
            past_due_since=None
        ).on_conflict_do_update(
            index_elements=['user_id'],
            set_={
                "status": "active",
                "provider_customer_id": customer_id,
                "provider_subscription_id": subscription_id,
                "past_due_since": None
            }
        )
        await session.execute(stmt_ent)
        await session.commit()
        
    elif event_type == "customer.subscription.updated":
        subscription_id = data.get("id")
        status = data.get("status")
        
        # Map Stripe status to our status
        mapped_status = "active"
        past_due_since = None
        
        if status in ("past_due", "unpaid"):
            mapped_status = "past_due"
            past_due_since = datetime.datetime.now(datetime.timezone.utc)
        elif status == "canceled":
            mapped_status = "inactive"
            
        res_ent = await session.execute(
            select(Entitlement).where(Entitlement.provider_subscription_id == subscription_id)
        )
        ent = res_ent.scalar_one_or_none()
        if ent:
            ent.status = mapped_status
            if mapped_status == "past_due" and not ent.past_due_since:
                ent.past_due_since = past_due_since
            elif mapped_status == "active":
                ent.past_due_since = None
            await session.commit()
            
    elif event_type == "customer.subscription.deleted":
        subscription_id = data.get("id")
        res_ent = await session.execute(
            select(Entitlement).where(Entitlement.provider_subscription_id == subscription_id)
        )
        ent = res_ent.scalar_one_or_none()
        if ent:
            ent.status = "inactive"
            ent.past_due_since = None
            await session.commit()
