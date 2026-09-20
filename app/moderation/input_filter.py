import re
from dataclasses import dataclass
from typing import Optional
from app.core.errors import AppException

@dataclass
class ModerationResult:
    is_safe: bool = True

BANNED_WORDS = {
    # Injection / Hacks
    "<script>", 
    "ignore all previous instructions", 
    "system:", 
    "safety off", 
    "secret_prompt", 
    "base64", 
    "dan", 
    "you are now", 
    "канон",
    # Sexual content
    "sex", "porn", "smut", "erotic", "nsfw", "steamy", "bdsm", "naked", "aroused", "fanfic", "explicit", "sexual", "pornographic",
    # Bullying / Abuse
    "loser", "moron", "bitch", "retard", "ugly", "fat kids", "dumb", "stupid", "idiot", "hates", "hate you", "die in a fire", "kill yourself", "retards", "morons",
    # Self-harm
    "suicide", "overdose", "kill myself", "cutting", "die", "end it all", "jumping off", "stopped living"
}

_HOMOGLYPH_MAP = {
    "а": "a", "с": "c", "е": "e", "о": "o", "р": "p", "х": "x", "у": "y", "і": "i", "ѕ": "s",
    "Α": "a", "Β": "b", "Ε": "e", "Ζ": "z", "Η": "h", "Ι": "i", "Κ": "k", "Μ": "m", "Ν": "n", "Ο": "o", "Ρ": "p", "Τ": "t", "Χ": "x", "Υ": "y"
}

def _normalize_homoglyphs(text: str) -> str:
    res = []
    for char in text:
        res.append(_HOMOGLYPH_MAP.get(char, char))
    return "".join(res)

def check_banned_terms(text: str) -> bool:
    """Returns True if banned terms are found."""
    # 1. Normalize
    normalized = _normalize_homoglyphs(text.lower())
    
    # 2. Substring matching for multi-word phrases (since tokenization splits them)
    for word in BANNED_WORDS:
        if " " in word or "<" in word or ":" in word:
            if word in normalized:
                return True
                
    # 3. Word-tokenized exact-set matching
    tokens = set(re.split(r'\W+', normalized))
    for word in BANNED_WORDS:
        if " " not in word and word in tokens:
            return True
            
    # 4. Spacing-bypass detection: 's e x', 's.e.x'
    # Look at runs of 1-2 character tokens
    raw_tokens = re.split(r'\W+', normalized)
    raw_tokens = [t for t in raw_tokens if t] # remove empty
    # Reconstruct string from short tokens
    short_run = "".join([t for t in raw_tokens if len(t) <= 2])
    for word in BANNED_WORDS:
        if " " not in word and len(word) >= 3 and word in short_run:
            return True
            
    return False

def check(text: str, field: str = "") -> ModerationResult:
    """Check input and raise AppException if rejected."""
    if not text:
        return ModerationResult(is_safe=True)
        
    if len(text) > 10000:
        raise AppException(code="E_MODERATION_BLOCKED", message="Input too long", retryable=False)
        
    if check_banned_terms(text):
        raise AppException(code="E_MODERATION_BLOCKED", message=f"Input violates moderation policies in field {field}", retryable=False)
        
    return ModerationResult(is_safe=True)
