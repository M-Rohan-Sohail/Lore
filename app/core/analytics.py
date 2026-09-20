import logging
from typing import Any
import uuid
from app.config import settings

logger = logging.getLogger(__name__)

# Initialize PostHog if configured
posthog = None
if settings.POSTHOG_KEY:
    try:
        from posthog import Posthog
        posthog = Posthog(settings.POSTHOG_KEY, host="https://app.posthog.com")
        logger.info("PostHog telemetry initialized.")
    except ImportError:
        logger.warning("PostHog library is not installed.")
else:
    logger.info("PostHog telemetry disabled (no key provided).")

async def track_event(user_id: uuid.UUID | str, event_name: str, properties: dict[str, Any] | None = None):
    """
    Sends an event to PostHog if initialized.
    Falls back to structured logging.
    """
    props = properties or {}
    uid_str = str(user_id)
    
    if posthog:
        posthog.capture(uid_str, event_name, properties=props)
    
    # Also log it for observability
    logger.info(f"Event Tracked: {event_name}", extra={"user_id": uid_str, "event": event_name, **props})

# Specific telemetry functions according to CP-18 taxonomy
async def track_sign_up(user_id: uuid.UUID, provider: str = "email"):
    await track_event(user_id, "sign_up", {"provider": provider})

async def track_quest_completed(user_id: uuid.UUID, quest_id: uuid.UUID, quest_title: str):
    await track_event(user_id, "quest_completed", {"quest_id": str(quest_id), "quest_title": quest_title})

async def track_recap_generated(user_id: uuid.UUID, recap_id: uuid.UUID, scope: str, provider: str, degraded_level: str):
    await track_event(user_id, "recap_generated", {
        "recap_id": str(recap_id),
        "scope": scope,
        "provider": provider,
        "degraded_level": degraded_level
    })

async def track_card_shared(user_id: uuid.UUID, card_kind: str, artifact_id: uuid.UUID):
    await track_event(user_id, "card_shared", {
        "card_kind": card_kind,
        "artifact_id": str(artifact_id)
    })
