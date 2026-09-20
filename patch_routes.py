import re

with open("app/tests/test_idor_suite.py", "r") as f:
    content = f.read()

# Fix Quest missing title instead of name
content = content.replace(
    'db_session.add(Quest(id=q_id, user_id=u1, type="main", name="Test", category="fitness", difficulty="easy", source="ai", status="active"))',
    'db_session.add(Quest(id=q_id, user_id=u1, type="main", title="Test", category="fitness", difficulty="easy", source="ai", status="active"))'
)

# Fix ShareToken missing uses_left
content = content.replace(
    ', uses_left=-1)',
    ')'
)

# Fix endpoints by adding /v1 prefix
content = content.replace('client.post("/quests/', 'client.post("/v1/quests/')
content = content.replace('client.post("/recaps/', 'client.post("/v1/recaps/')
content = content.replace('client.get(f"/party/', 'client.get(f"/v1/party/')
content = content.replace('client.post(f"/party/', 'client.post(f"/v1/party/')
content = content.replace('client.post("/cards"', 'client.post("/v1/cards"')
content = content.replace('client.get("/cards/', 'client.get("/v1/cards/')

with open("app/tests/test_idor_suite.py", "w") as f:
    f.write(content)
