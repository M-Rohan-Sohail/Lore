from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import uuid
import json

from app.db.session import get_db
from app.deps import get_current_user
from app.core.envelope import success
from app.billing.stripe_client import verify_stripe_signature, create_checkout_session
from app.services.billing import process_stripe_webhook
from app.db.models.accounts import Profile

router = APIRouter(prefix="/v1/billing", tags=["billing"])

class CheckoutRequest(BaseModel):
    return_url: str

@router.post("/checkout")
async def checkout(
    payload: CheckoutRequest,
    current_user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    profile = await db.get(Profile, current_user_id)
    email = profile.email if profile else "unknown@example.com"
    
    url = await create_checkout_session(str(current_user_id), email, payload.return_url)
    return success({"url": url})

@router.post("/webhook")
async def webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature", "")
    
    if not verify_stripe_signature(payload, sig_header):
        raise HTTPException(status_code=400, detail="Invalid signature")
        
    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid payload")
        
    await process_stripe_webhook(db, event)
    
    return {"status": "ok"}
