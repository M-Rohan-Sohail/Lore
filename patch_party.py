with open("app/routers/party.py", "r") as f:
    content = f.read()

replacement_create = """async def create(
    request: PartyCreateRequest,
    user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from app.core.flags import get_flag
    if not await get_flag(db, "party_enabled", default=True):
        raise AppException(code="E_PARTY_DISABLED", message="Party creation is currently disabled", retryable=False)
"""

replacement_join = """async def join(
    request: PartyJoinRequest,
    user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from app.core.flags import get_flag
    if not await get_flag(db, "party_enabled", default=True):
        raise AppException(code="E_PARTY_DISABLED", message="Joining parties is currently disabled", retryable=False)
"""

content = content.replace("async def create(\n    request: PartyCreateRequest,\n    user_id: uuid.UUID = Depends(get_current_user),\n    db: AsyncSession = Depends(get_db)\n):", replacement_create)
content = content.replace("async def join(\n    request: PartyJoinRequest,\n    user_id: uuid.UUID = Depends(get_current_user),\n    db: AsyncSession = Depends(get_db)\n):", replacement_join)

with open("app/routers/party.py", "w") as f:
    f.write(content)
