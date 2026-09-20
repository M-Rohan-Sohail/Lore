from fastapi import APIRouter, Depends, Header
from app.core.envelope import success, error
from app.core.errors import AppException
from app.jobs.backups import perform_backup
from app.config import settings

router = APIRouter(prefix="/v1/jobs", tags=["jobs"])

@router.post("/backup")
async def trigger_backup(authorization: str = Header(None)):
    # simple auth for cron endpoint, using cron secret
    if not authorization or authorization != f"Bearer {settings.CRON_SECRET}":
        raise AppException("E_UNAUTHORIZED", "Invalid cron secret")
        
    result = perform_backup()
    if result:
        return success({"message": "Backup completed successfully"})
    else:
        # Returning 500 equivalent but keeping our envelope
        raise AppException("E_INTERNAL", "Backup failed")
