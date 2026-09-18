from fastapi import FastAPI
from app.core.envelope import success
from app.core.errors import setup_exception_handlers
from app.routers import accounts

app = FastAPI(title="LORE Core API", version="0.1.0")

setup_exception_handlers(app)
app.include_router(accounts.router)

@app.get("/health")
async def health_check():
    return success({"status": "ok"})
