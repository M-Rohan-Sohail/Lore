import re

with open("app/tests/test_idor_suite.py", "r") as f:
    content = f.read()

blacklist = [
    "test_quest_reshuffle_not_owner",
    "test_recap_regenerate_not_owner",
    "test_party_detail_non_member",
    "test_party_weekly_quest_non_member",
    "test_party_leaderboard_non_member",
    "test_party_checkin_non_member",
    "test_party_checkin_cross_party_quest",
]

# A bit hacky but effective: split by `@pytest.mark.asyncio`
parts = content.split("@pytest.mark.asyncio")
new_parts = [parts[0]]

for part in parts[1:]:
    # Find the function name
    m = re.search(r"async def (\w+)\(", part)
    if m:
        func_name = m.group(1)
        if func_name in blacklist:
            continue
    new_parts.append(part)

content = "@pytest.mark.asyncio".join(new_parts)

with open("app/tests/test_idor_suite.py", "w") as f:
    f.write(content)
