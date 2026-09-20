import json
from app.moderation.input_filter import check_banned_terms

with open("fixtures/redteam_corpus.json") as f:
    REDTEAM_FIXTURES = json.load(f)

for f in REDTEAM_FIXTURES:
    if f["category"] in ["self_harm", "sexual_content", "bullying"]:
        if not check_banned_terms(f["text"]):
            print(f"Failed to block: {f['text']} in {f['category']}")
