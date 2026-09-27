import json

with open("openapi.json", "r") as f:
    spec = json.load(f)

expected_endpoints = [
    ("/health", "get"),
    ("/v1/auth/sessions", "get"),
    ("/v1/auth/sessions/{id}/revoke", "post"),
    ("/v1/accounts/age-gate", "post"),
    ("/v1/accounts/consent", "post"),
    ("/v1/accounts/timezone", "patch"),
    ("/v1/characters/quiz", "post"),
    ("/v1/characters/generate", "post"),
    ("/v1/characters/reroll", "post"),
    ("/v1/quests/main", "post"),
    ("/v1/quests/daily", "get"),
    ("/v1/quests/{id}/complete", "post"),
    ("/v1/quests/{id}/reshuffle", "post"),
    ("/v1/recaps/{id}/regenerate", "post"),
    ("/v1/jobs/recap-tick", "post"),
    ("/v1/jobs/push-send", "post"),
    ("/v1/jobs/backup", "post"),
    ("/v1/parties", "post"),
    ("/v1/parties/join", "post"),
    ("/v1/parties/leave", "post"),
    ("/v1/parties/{id}/remove", "post"),
    ("/v1/parties/{id}/checkin", "post"),
    ("/v1/cards/share", "post"),
    ("/v1/cards/{token}", "get"),
    ("/v1/cards/{token}/revoke", "post"),
    ("/v1/notifications/register", "post"),
    ("/v1/notifications/prefs", "patch"),
    ("/v1/billing/webhook", "post"),
    ("/v1/settings/export", "get"),
    ("/v1/settings/delete", "post"),
    ("/v1/settings/ai-personalization", "patch")
]

missing = []
for path, method in expected_endpoints:
    if path not in spec["paths"]:
        missing.append(f"{method.upper()} {path} (path missing)")
    elif method not in spec["paths"][path]:
        missing.append(f"{method.upper()} {path} (method missing)")

if missing:
    print("MISSING ENDPOINTS:")
    for m in missing:
        print(" -", m)
    exit(1)
else:
    print("All required endpoints are present in the OpenAPI spec!")
