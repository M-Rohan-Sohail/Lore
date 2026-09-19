import uuid
import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from app.db.models.platform import AiUsage

async def record_usage(
    db: AsyncSession, 
    user_id: uuid.UUID, 
    budget_class: str, 
    provider: str, 
    tokens_in: int, 
    tokens_out: int
):
    today = datetime.datetime.now(datetime.timezone.utc).date()
    
    stmt = insert(AiUsage).values(
        user_id=user_id,
        day=today,
        budget_class=budget_class,
        calls=1,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        provider=provider
    ).on_conflict_do_update(
        index_elements=['user_id', 'day', 'budget_class'],
        set_={
            'calls': AiUsage.calls + 1,
            'tokens_in': AiUsage.tokens_in + tokens_in,
            'tokens_out': AiUsage.tokens_out + tokens_out,
            'provider': provider
        }
    )
    
    await db.execute(stmt)
    await db.commit()
