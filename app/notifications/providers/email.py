import os
import httpx
from app.core.errors import AppException

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")

async def send_email(to: str, subject: str, html: str) -> bool:
    """Sends an email via Resend API. Returns True if successful."""
    if not RESEND_API_KEY:
        # Mock mode
        if to == "bounce@test.com":
            return False
        return True
        
    url = "https://api.resend.com/emails"
    payload = {
        "from": "LORE <notifications@lore.app>",
        "to": to,
        "subject": subject,
        "html": html
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {RESEND_API_KEY}"}
        )
        if resp.status_code >= 400:
            # Check for hard bounce or invalid email
            if "invalid_to_address" in resp.text:
                return False
            raise AppException("E_INTERNAL", f"Email failed: {resp.text}")
            
        return True
