from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models.platform import AppFlag
from app.core.errors import AppException

async def get_flag(session: AsyncSession, key: str, default: bool = False) -> bool:
    result = await session.execute(select(AppFlag).where(AppFlag.key == key))
    flag = result.scalar_one_or_none()
    if flag is None:
        return default
    if isinstance(flag.value, bool):
        return flag.value
    return default

async def require_flag(session: AsyncSession, key: str, default: bool = False) -> None:
    val = await get_flag(session, key, default)
    if not val:
        raise AppException("E_FLAG_DISABLED", f"Flag {key} is disabled")
