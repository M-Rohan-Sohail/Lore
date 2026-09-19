from pydantic import BaseModel
import uuid
import datetime

class PartyCreate(BaseModel):
    name: str

class PartyResponse(BaseModel):
    id: uuid.UUID
    name: str
    lead_id: uuid.UUID | None
    invite_code: str
    archived_at: datetime.datetime | None
