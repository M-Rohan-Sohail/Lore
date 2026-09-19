from fastapi import FastAPI
from app.core.envelope import success
from app.core.errors import setup_exception_handlers
from app.routers import accounts, characters, quests, recaps, party, cards, notifications

app = FastAPI(title="LORE Core API", version="0.1.0")

setup_exception_handlers(app)
app.include_router(accounts.auth_router)
app.include_router(accounts.accounts_router)
app.include_router(characters.router)
app.include_router(quests.router)
app.include_router(recaps.router)
app.include_router(party.router)
app.include_router(cards.router)
app.include_router(notifications.router)

@app.get("/health")
async def health_check():
    return success({"status": "ok"})
