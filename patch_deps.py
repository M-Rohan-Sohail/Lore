with open("app/deps.py", "r") as f:
    content = f.read()

replacement = """    # Check if account is deleted
    deleted = await session.scalar(select(DeletedAccount).where(DeletedAccount.user_id == user_id))
    if deleted:
        raise AppException(code="E_ACCOUNT_DELETED", message="Account has been deleted", retryable=False)
        
    # Upsert Profile with email (check signups_enabled if new)
    profile = await session.get(Profile, user_id)
    if profile is None:
        from app.core.flags import get_flag
        if not await get_flag(session, "signups_enabled", default=True):
            raise AppException(code="E_SIGNUPS_DISABLED", message="New account creation is currently disabled", retryable=False)
            
    stmt = insert(Profile).values(
        id=user_id,
        email=email
    ).on_conflict_do_update(
        index_elements=['id'],
        set_={"email": email}
    )
    await session.execute(stmt)
    await session.commit()"""

content = content.replace("""    # Check if account is deleted
    deleted = await session.scalar(select(DeletedAccount).where(DeletedAccount.user_id == user_id))
    if deleted:
        raise AppException(code="E_ACCOUNT_DELETED", message="Account has been deleted", retryable=False)
        
    # Upsert Profile with email
    stmt = insert(Profile).values(
        id=user_id,
        email=email
    ).on_conflict_do_update(
        index_elements=['id'],
        set_={"email": email}
    )
    await session.execute(stmt)
    await session.commit()""", replacement)

with open("app/deps.py", "w") as f:
    f.write(content)
