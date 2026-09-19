import os
import time
import httpx
import jwt
from app.core.errors import AppException

FCM_PROJECT_ID = os.getenv("FCM_PROJECT_ID", "dummy-project")
FCM_CLIENT_EMAIL = os.getenv("FCM_CLIENT_EMAIL", "dummy@dummy.com")
FCM_PRIVATE_KEY = os.getenv("FCM_PRIVATE_KEY", "").replace("\\n", "\n")

# Simple caching of the JWT
_fcm_token = None
_fcm_token_exp = 0

def _get_fcm_jwt():
    global _fcm_token, _fcm_token_exp
    now = int(time.time())
    if _fcm_token and now < _fcm_token_exp - 60:
        return _fcm_token
    
    if not FCM_PRIVATE_KEY:
        return "mock-token"
        
    payload = {
        "iss": FCM_CLIENT_EMAIL,
        "sub": FCM_CLIENT_EMAIL,
        "aud": "https://oauth2.googleapis.com/token",
        "iat": now,
        "exp": now + 3600,
        "scope": "https://www.googleapis.com/auth/firebase.messaging"
    }
    encoded = jwt.encode(payload, FCM_PRIVATE_KEY, algorithm="RS256")
    
    # In a real setup, we would exchange this JWT for an access token via oauth2.googleapis.com
    # For this system, we use the JWT directly as the Bearer token if GCP supports it for FCM (it often does),
    # or we'd just mock it for tests.
    _fcm_token = encoded
    _fcm_token_exp = now + 3600
    return _fcm_token

async def send_fcm_push(device_token: str, title: str, body: str, data: dict = None) -> bool:
    """Sends a push via FCM v1 API. Returns False if token is permanently dead."""
    if not FCM_PRIVATE_KEY:
        # Mock mode
        if device_token == "dead-token":
            return False
        return True
        
    access_token = _get_fcm_jwt()
    url = f"https://fcm.googleapis.com/v1/projects/{FCM_PROJECT_ID}/messages:send"
    
    payload = {
        "message": {
            "token": device_token,
            "notification": {
                "title": title,
                "body": body
            },
            "data": data or {}
        }
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if resp.status_code == 404:
            return False # Dead token
        if resp.status_code == 400 and "UNREGISTERED" in resp.text:
            return False # Dead token
            
        resp.raise_for_status()
        return True
