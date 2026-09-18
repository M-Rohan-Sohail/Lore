from pydantic import BaseModel
import uuid

class LogoutResponse(BaseModel):
    status: str
