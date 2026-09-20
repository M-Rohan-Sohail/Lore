import re

with open("app/tests/test_idor_suite.py", "r") as f:
    content = f.read()

# Fix token enumeration by hashing the token in the setup
if "from app.services.cards import _hash_token" not in content:
    content = content.replace(
        "import jwt",
        "import jwt\nfrom app.services.cards import _hash_token"
    )
    content = content.replace(
        'st = ShareToken(created_by=u1, kind="weekly_recap", artifact_id=r_id, token_hash="abcdef")',
        'st = ShareToken(created_by=u1, kind="weekly_recap", artifact_id=r_id, token_hash=_hash_token("abcdef"))'
    )

with open("app/tests/test_idor_suite.py", "w") as f:
    f.write(content)
