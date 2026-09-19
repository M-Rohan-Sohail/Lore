BANNED_WORDS = {
    "<script>", 
    "ignore all previous instructions", 
    "system:", 
    "safety off", 
    "secret_prompt", 
    "base64", 
    "dan", 
    "you are now", 
    "канон"
}

def check_input(text: str) -> bool:
    """Returns True if the input is clean, False if it contains banned words or patterns."""
    if not text:
        return True
    text_lower = text.lower()
    for word in BANNED_WORDS:
        if word in text_lower:
            return False
    
    # Check for excessive length indicating context window blowup attempt
    if len(text) > 10000:
        return False
        
    return True
