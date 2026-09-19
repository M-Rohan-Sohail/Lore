from enum import Enum
from pydantic import BaseModel
import uuid
import datetime

class CardKind(str, Enum):
    CHARACTER = "character"
    LEVEL_UP = "level_up"
    WEEKLY_RECAP = "weekly_recap"
    PARTY_RECAP = "party_recap"
    QUIET_WEEK = "quiet_week"

class ShareCardRequest(BaseModel):
    kind: CardKind
    artifact_id: uuid.UUID

class ShareCardResponse(BaseModel):
    token: str
    expires_at: datetime.datetime
