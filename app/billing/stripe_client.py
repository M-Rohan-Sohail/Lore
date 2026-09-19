import os
import hmac
import hashlib
import time
import httpx
from typing import Dict, Any
from app.core.errors import AppException

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "sk_test_dummy")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_dummy")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID", "price_dummy")

def verify_stripe_signature(payload: bytes, sig_header: str) -> bool:
    """
    Verifies the Stripe webhook signature manually without the Stripe SDK.
    """
    if not sig_header:
        return False
        
    try:
        parts = dict(p.split("=") for p in sig_header.split(",") if "=" in p)
        timestamp = parts.get("t")
        signatures = [p.split("=")[1] for p in sig_header.split(",") if p.startswith("v1=")]
        
        if not timestamp or not signatures:
            return False
            
        # Optional: check if timestamp is within tolerance (e.g., 5 mins)
        now = int(time.time())
        if abs(now - int(timestamp)) > 300:
            return False
            
        signed_payload = f"{timestamp}.".encode("utf-8") + payload
        expected_sig = hmac.new(
            STRIPE_WEBHOOK_SECRET.encode("utf-8"),
            signed_payload,
            hashlib.sha256
        ).hexdigest()
        
        return expected_sig in signatures
    except Exception:
        return False

async def create_checkout_session(user_id: str, email: str, return_url: str) -> str:
    """
    Creates a Stripe Checkout Session via REST API and returns the URL.
    """
    # In test mode or when lacking a key, just mock the URL
    if STRIPE_SECRET_KEY == "sk_test_dummy":
        return f"https://checkout.stripe.com/pay/cs_test_mock?client_reference_id={user_id}"

    url = "https://api.stripe.com/v1/checkout/sessions"
    data = {
        "payment_method_types[]": "card",
        "mode": "subscription",
        "line_items[0][price]": STRIPE_PRICE_ID,
        "line_items[0][quantity]": "1",
        "client_reference_id": user_id,
        "customer_email": email,
        "success_url": f"{return_url}?success=true",
        "cancel_url": f"{return_url}?canceled=true",
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            data=data,
            auth=(STRIPE_SECRET_KEY, "")
        )
        if resp.status_code >= 400:
            raise AppException("E_INTERNAL", f"Stripe API error: {resp.text}")
            
        return resp.json()["url"]
