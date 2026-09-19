BANNED_OUTPUT_PHRASES = {
    "as an ai", 
    "i cannot fulfill", 
    "i am a large language model",
    "i'm sorry, but",
    "against my programming"
}

def scan_output(text: str) -> bool:
    """Returns True if output is clean and safe to show, False if it contains AI disclaimers or banned language."""
    if not text:
        return True
    text_lower = text.lower()
    for phrase in BANNED_OUTPUT_PHRASES:
        if phrase in text_lower:
            return False
    return True
