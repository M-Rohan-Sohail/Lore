import re

with open("app/tests/test_idor_suite.py", "r") as f:
    content = f.read()

# Fix PartyMember missing role
content = content.replace(
    'db_session.add(PartyMember(party_id=p_id, user_id=u1))',
    'db_session.add(PartyMember(party_id=p_id, user_id=u1, role="lead"))'
)

# Fix Recap missing fields and invalid narrative field
# db_session.add(Recap(id=r_id, owner_id=u1, scope="user", narrative="Heroic stuff"))
from datetime import date
replacement_recap = """import datetime
      db_session.add(Recap(id=r_id, owner_id=u1, scope="user", week_start=datetime.date.today(), provider="gemini", degraded_level="none", payload={"narrative": "Heroic stuff"}))"""

content = re.sub(
    r'db_session\.add\(Recap\(id=r_id, owner_id=u1, scope="user", narrative="Heroic stuff"\)\)',
    r'db_session.add(Recap(id=r_id, owner_id=u1, scope="user", week_start=datetime.date.today(), provider="gemini", degraded_level="none", payload={"narrative": "Heroic stuff"}))',
    content
)

# add import datetime if it's not there
if "import datetime" not in content:
    content = "import datetime\n" + content

with open("app/tests/test_idor_suite.py", "w") as f:
    f.write(content)
