import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
import jwt
import uuid
from app.deps import get_current_user
from app.config import settings
from app.core.errors import setup_exception_handlers

app = FastAPI()
setup_exception_handlers(app)

@app.get("/test-auth")
async def test_auth(user_id: uuid.UUID = Depends(get_current_user)):
    return {"user_id": str(user_id)}

client = TestClient(app)

def test_auth_valid_token(monkeypatch):
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", "supersecret123")
    user_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    token = jwt.encode(
        {"sub": user_id, "session_id": session_id, "aud": "authenticated"},
        "supersecret123",
        algorithm="HS256"
    )
    
    response = client.get("/test-auth", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["user_id"] == user_id

def test_auth_invalid_token():
    response = client.get("/test-auth", headers={"Authorization": "Bearer invalid.token.here"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "E_UNAUTHORIZED"
