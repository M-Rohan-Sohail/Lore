from pydantic import BaseModel, Field
from typing import Dict

class QuizSubmission(BaseModel):
    answers: list[int] = Field(..., min_length=7, max_length=7)

class CharacterResponse(BaseModel):
    class_name: str
    class_tagline: str
    origin_blurb: str
    base_stats: Dict[str, int]
