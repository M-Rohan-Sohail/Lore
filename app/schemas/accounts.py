from pydantic import BaseModel

class OnboardingRequest(BaseModel):
    birth_ym: str
    tz: str
    consent: bool

class OnboardingResponse(BaseModel):
    status: str
    age_gate_blocked: bool
