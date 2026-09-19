from pydantic import BaseModel, Field
import datetime
import uuid
from typing import Literal

class RecapPayload(BaseModel):
    title: str
    body_text: str
    stat_deltas: dict[str, int]
    episode_number: int | None = None
    
class RecapResponse(BaseModel):
    id: uuid.UUID
    scope: str
    owner_id: uuid.UUID
    week_start: datetime.date
    payload: RecapPayload | None
    provider: str
    degraded_level: str
    episode_number: int | None
    regen_count: int

class LatestRecapResponse(BaseModel):
    recap: RecapResponse | None
    show_invite_nudge: bool
