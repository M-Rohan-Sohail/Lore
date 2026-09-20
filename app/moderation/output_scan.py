from pydantic import BaseModel
from typing import Any

BANNED_OUTPUT_PHRASES = {
    "as an ai", 
    "i cannot fulfill", 
    "i am a large language model",
    "i'm sorry, but",
    "i am sorry, but",
    "against my programming",
    "against your programming",
    "i am an ai",
    "being ai",
    "you are a large language model",
    "i am a language model"
}

def _extract_text_fields(obj: Any) -> list[str]:
    texts = []
    if isinstance(obj, str):
        texts.append(obj)
    elif isinstance(obj, dict):
        for val in obj.values():
            texts.extend(_extract_text_fields(val))
    elif isinstance(obj, list):
        for item in obj:
            texts.extend(_extract_text_fields(item))
    elif isinstance(obj, BaseModel):
        for key, val in obj.model_dump().items():
            texts.extend(_extract_text_fields(val))
    return texts

def scan_output(obj: Any) -> bool:
    """Returns True if output is clean and safe to show, False if it contains AI disclaimers or banned language."""
    texts = _extract_text_fields(obj)
    
    for text in texts:
        if not text:
            continue
        text_lower = text.lower()
        for phrase in BANNED_OUTPUT_PHRASES:
            if phrase in text_lower:
                return False
    return True
