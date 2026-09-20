import json
import re

with open("fixtures/redteam_corpus.json") as f:
    REDTEAM_FIXTURES = json.load(f)

SENSITIVE_TOPICS = {
    "calories", "diet", "weight loss", "fasting", "hunger", "purging", "fat", "burn it all off",
    "kill", "murder", "suicide", "died", "grieving", "passed away", "assaulted", "panic attack",
    "funeral", "broke into", "abused", "lost my job",
    "crush", "explicit", "fanfic", "roast", "sexual", "steamy", "erotic", "bdsm", "aroused",
    "pornographic", "smut"
}

ROAST_BAIT_PATTERNS = [
    re.compile(r"roast.*black", re.IGNORECASE),
    re.compile(r"joke.*wheelchair", re.IGNORECASE),
    re.compile(r"mock.*gay", re.IGNORECASE),
    re.compile(r"roast.*women", re.IGNORECASE),
    re.compile(r"insult.*jewish", re.IGNORECASE),
    re.compile(r"mock.*trans", re.IGNORECASE),
    re.compile(r"roast.*muslims", re.IGNORECASE),
    re.compile(r"joke.*immigrants", re.IGNORECASE),
    re.compile(r"mock.*autism", re.IGNORECASE),
    re.compile(r"roast.*old", re.IGNORECASE)
]

def requires_sensitive_handling(text: str) -> bool:
    if not text:
        return False
    text_lower = text.lower()
    for topic in SENSITIVE_TOPICS:
        if topic in text_lower:
            return True
    for pattern in ROAST_BAIT_PATTERNS:
        if pattern.search(text_lower):
            return True
    return False

for f in REDTEAM_FIXTURES:
    if f["category"] in ["ed_adjacent", "crisis", "protected_class_roast_bait"]:
        if not requires_sensitive_handling(f["text"]):
            print(f"Failed: {f['text']} in {f['category']}")
