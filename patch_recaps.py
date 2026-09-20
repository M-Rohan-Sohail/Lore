import re

with open("app/services/recaps.py", "r") as f:
    content = f.read()

# For existing:
content = content.replace("        existing.regen_count += 1\n        from app.core.analytics import track_recap_generated", 
                          "        existing.regen_count += 1")
content = content.replace("        await track_recap_generated(user_id, existing.id, existing.scope, existing.provider, existing.degraded_level)\n        return existing",
                          "        return existing")

# We will just insert tracking at the end of the generate_user_recap and generate_party_recap block.
# Actually, the job/caller might be a better place. Let's just add db.flush() and track before return.
def add_tracking(match):
    return """        await db.flush()
        from app.core.analytics import track_recap_generated
        await track_recap_generated(new_recap.owner_id, new_recap.id, new_recap.scope, new_recap.provider, new_recap.degraded_level)
        return new_recap"""

content = re.sub(r"        db.add\(new_recap\)\n        return new_recap", add_tracking, content)

def add_tracking_existing(match):
    return """        existing.regen_count += 1
        from app.core.analytics import track_recap_generated
        await track_recap_generated(existing.owner_id, existing.id, existing.scope, existing.provider, existing.degraded_level)
        return existing"""

content = re.sub(r"        existing.regen_count \+= 1\n        return existing", add_tracking_existing, content)

with open("app/services/recaps.py", "w") as f:
    f.write(content)
