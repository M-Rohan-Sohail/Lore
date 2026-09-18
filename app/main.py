from fastapi import FastAPI
from app.core.envelope import success

app = FastAPI(title="LORE Core API", version="0.1.0")

@app.get("/health")
async def health_check():
    return success({"status": "ok"})
