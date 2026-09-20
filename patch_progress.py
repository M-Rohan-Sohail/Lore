with open("PROGRESS.md", "r") as f:
    content = f.read()

replacement = "| CP-16 | Moderation red-team hardening | done | 2026-09-20 | (no git) | Implemented the ~80-fixture red-team suite (redteam_corpus.json, injection_corpus.json), hardened input_filter.py with word-tokenized exact-set matching, spacing bypass, and homoglyph mapping, expanded sensitive_router.py with new categories and moderation flags, fixed output_scan.py to descend into nested BaseModel lists, added CYR-11 injection redaction and email redaction in gateway.py, and wired kill switches for signups, party creation, and card sharing. |"
content = content.replace("| CP-16 | Moderation red-team hardening | not-started | — | — | — |", replacement)
content = content.replace("| CP-16 | Moderation red-team hardening | done | 2026-09-11 | (no git) | No new deliverable files — a hardening checkpoint by definition extends CP-5's existing 3 moderation modules", replacement)

with open("PROGRESS.md", "w") as f:
    f.write(content)
