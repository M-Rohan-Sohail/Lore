import json
from app.moderation.output_scan import scan_output

with open("fixtures/redteam_corpus.json") as f:
    REDTEAM_FIXTURES = json.load(f)

for f in REDTEAM_FIXTURES:
    if f["category"] == "unsafe_output_seeding":
        if scan_output(f["text"]):
            print(f"Failed to scan: {f['text']}")
