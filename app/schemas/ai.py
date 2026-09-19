from pydantic import BaseModel, Field
import uuid
from typing import Optional

class AIRequest(BaseModel):
    user_id: uuid.UUID
    system_prompt: str
    user_prompt: str
    budget_class: str = Field(default="standard")
    temperature: float = Field(default=0.7)

class AIResponse(BaseModel):
    content: str
    tokens_in: int
    tokens_out: int
    provider: str

class AIProviderError(Exception):
    def __init__(self, provider: str, status_code: int, message: str):
        self.provider = provider
        self.status_code = status_code
        self.message = message
        super().__init__(f"[{provider}] {status_code}: {message}")

def validate_ai_output(content: str) -> str:
    """Validates and sanitizes AI output structure."""
    if not content or not content.strip():
        raise ValueError("AI output is empty")
    return content.strip()
