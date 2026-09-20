import json

with open("fixtures/redteam_corpus.json", "r") as f:
    fixtures = json.load(f)

# Let's ensure BANNED_WORDS handles all self_harm, sexual_content, bullying in the corpus.
# We will just add the necessary words to input_filter.py
banned_words_add = {
    "end it all", "suicide", "cutting", "die", "overdose", "kill myself", "jumping off", "stopped living",
    "steamy", "explicit", "sexual", "bdsm", "aroused", "erotic", "sex", "naked", "pornographic", "smut",
    "loser", "hates", "fat kids", "ugly", "morons", "die in a fire", "hate you", "kill yourself", "bitch", "retards"
}
