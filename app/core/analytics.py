import logging
from typing import Any
import uuid

logger = logging.getLogger(__name__)

async def track_event(user_id: uuid.UUID, event_name: str, properties: dict[str, Any] = None):
    """Stub for analytics tracking (e.g. PostHog)."""
    props = properties or {}
    logger.info(f"ANALYTICS: User {user_id} triggered {event_name} with {props}")
