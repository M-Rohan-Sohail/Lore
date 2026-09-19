import os
from aioapns import APNs, NotificationRequest
from app.core.errors import AppException

APNS_KEY_ID = os.getenv("APNS_KEY_ID", "dummy-key-id")
APNS_TEAM_ID = os.getenv("APNS_TEAM_ID", "dummy-team")
APNS_TOPIC = os.getenv("APNS_TOPIC", "com.lore.app")
APNS_AUTH_KEY = os.getenv("APNS_AUTH_KEY", "dummy.p8")

_apns_client = None

def _get_apns_client():
    global _apns_client
    if _apns_client is None and os.path.exists(APNS_AUTH_KEY):
        _apns_client = APNs(
            key=APNS_AUTH_KEY,
            key_id=APNS_KEY_ID,
            team_id=APNS_TEAM_ID,
            topic=APNS_TOPIC,
            use_sandbox=True, # Toggle based on env
        )
    return _apns_client

async def send_apns_push(device_token: str, title: str, body: str, data: dict = None) -> bool:
    """Sends a push via APNs. Returns False if token is permanently dead."""
    client = _get_apns_client()
    if not client:
        # Mock mode
        if device_token == "dead-token":
            return False
        return True

    request = NotificationRequest(
        device_token=device_token,
        message={"aps": {"alert": {"title": title, "body": body}}, **(data or {})}
    )
    
    response = await client.send_notification(request)
    if not response.is_successful:
        if response.description in ("BadDeviceToken", "Unregistered"):
            return False
        raise AppException("E_INTERNAL", f"APNs failed: {response.description}")
        
    return True
