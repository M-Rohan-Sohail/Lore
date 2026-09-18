from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models.platform import AppFlag

async def get_flag(session: AsyncSession, key: str, default: bool = False) -> bool:
    result = await session.execute(select(AppFlag).where(AppFlag.key == key))
    flag = result.scalar_one_or_none()
    if flag is None:
        return default
    if isinstance(flag.value, bool):
        return flag.value
    return default
