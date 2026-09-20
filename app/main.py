import time
import uuid
import logging
from fastapi import FastAPI, Request
from starlette.responses import Response

import sentry_sdk
from pythonjsonlogger import jsonlogger

from app.core.envelope import success
from app.core.errors import setup_exception_handlers
from app.routers import accounts, characters, quests, recaps, party, cards, notifications, billing, settings, jobs
from app.config import settings as app_settings

# Configure structured JSON logging
logger = logging.getLogger()
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(name)s %(message)s')
logHandler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

# Initialize Sentry
if app_settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=app_settings.SENTRY_DSN,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )
    logging.getLogger("main").info("Sentry initialized.")

app = FastAPI(title="LORE Core API", version="0.1.0")

@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start_time = time.time()
    
    # Extract pseudo user info if present
    auth_header = request.headers.get("Authorization", "")
    pseudo_user = "anonymous"
    if auth_header.startswith("Bearer "):
        pseudo_user = "authenticated"  # In a real app we might parse the JWT (carefully) for logs, but usually we just log the identity later in the route
        
    try:
        response = await call_next(request)
        latency = (time.time() - start_time) * 1000
        
        # Check for degraded_level from AI routes (can be stuffed into a custom header or extracted from body, but usually custom header is best for middleware)
        degraded = response.headers.get("X-Degraded-Level", "none")
        
        logging.getLogger("http").info(
            "Request processed", 
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "latency_ms": latency,
                "pseudo_user": pseudo_user,
                "degraded_level": degraded
            }
        )
        return response
    except Exception as exc:
        latency = (time.time() - start_time) * 1000
        logging.getLogger("http").error(
            "Request failed", 
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "latency_ms": latency,
                "pseudo_user": pseudo_user,
                "error": str(exc)
            },
            exc_info=True
        )
        raise

setup_exception_handlers(app)
app.include_router(accounts.router)
app.include_router(characters.router)
app.include_router(quests.router)
app.include_router(recaps.router)
app.include_router(party.router)
app.include_router(cards.router)
app.include_router(notifications.router)
app.include_router(billing.router)
app.include_router(settings.router)
app.include_router(jobs.router)

@app.get("/health")
async def health_check():
    return success({"status": "ok"})
