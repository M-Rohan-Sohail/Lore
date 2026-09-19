SENSITIVE_TOPICS = {
    "crush", 
    "explicit", 
    "fanfic", 
    "roast", 
    "calories",
    "diet",
    "weight loss",
    "kill",
    "murder",
    "suicide"
}

def requires_sensitive_handling(text: str) -> bool:
    """Returns True if the request touches on sensitive topics that require strict framing."""
    if not text:
        return False
    text_lower = text.lower()
    for topic in SENSITIVE_TOPICS:
        if topic in text_lower:
            return True
    return False
