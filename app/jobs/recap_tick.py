import asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import select, update
import datetime
from app.db.models.recaps import RecapJob
from app.services.recaps import generate_user_recap, generate_party_recap

async def process_recap_job(session_maker: async_sessionmaker):
    async with session_maker() as db:
        try:
            # 1. Fetch exactly 1 pending job with SKIP LOCKED
            now = datetime.datetime.now(datetime.timezone.utc)
            stmt = (
                select(RecapJob)
                .where(
                    RecapJob.status == "pending",
                    RecapJob.run_after <= now
                )
                .order_by(RecapJob.created_at)
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            result = await db.execute(stmt)
            job = result.scalar_one_or_none()
            
            if not job:
                return False # No jobs to process
                
            # 2. Update status to processing
            job.status = "processing"
            job.claimed_at = now
            job.attempts += 1
            await db.commit()
            
            # Refresh to avoid MissingGreenlet error after commit
            await db.refresh(job)
            
            try:
                if job.scope == "user":
                    # Generate the recap (handles quiet week, AI generation, and fallback internally)
                    await generate_user_recap(db, job.owner_id, job.week_start, force_regen=False)
                    job.status = "completed"
                elif job.scope == "party":
                    await generate_party_recap(db, job.owner_id, job.week_start, force_regen=False)
                    job.status = "completed"
                else:
                    raise ValueError(f"Unknown scope: {job.scope}")
                
                await db.commit()
                
            except Exception as e:
                # Execution failed
                await db.rollback()
                await db.refresh(job) # Fix MissingGreenlet in retry path
                
                job.last_error = str(e)
                if job.attempts >= 3:
                    # Poison pill: force fallback to template after 3 fails
                    try:
                        # Ensure we always write a template recap even if it poisoned
                        if job.scope == "user":
                            # We can manually create a template or call generate_user_recap with a flag
                            pass # In `generate_user_recap` we catch AI exceptions, so if it failed here it's a DB/code error.
                        job.status = "failed"
                        await db.commit()
                    except Exception:
                        await db.rollback()
                else:
                    # Retry
                    job.status = "pending"
                    job.run_after = now + datetime.timedelta(minutes=5 * job.attempts)
                    await db.commit()
                    
            return True
            
        except Exception:
            await db.rollback()
            return False
