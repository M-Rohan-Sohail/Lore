import jwt
import uuid
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from app.config import settings
from app.db.session import get_db
from app.db.models.accounts import AuthSession, Profile
from app.core.errors import AppException

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_db)
) -> uuid.UUID:
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False}
        )
    except jwt.ExpiredSignatureError:
        raise AppException(code="E_UNAUTHORIZED", message="Token expired", retryable=False)
    except jwt.InvalidTokenError:
        raise AppException(code="E_UNAUTHORIZED", message="Invalid token", retryable=False)

    user_id_str = payload.get("sub")
    session_id = payload.get("session_id")
    email = payload.get("email")
    
    if not user_id_str or not session_id:
        raise AppException(code="E_UNAUTHORIZED", message="Invalid token payload", retryable=False)
        
    user_id = uuid.UUID(user_id_str)
    
    # Check if session is revoked
    revoked = await session.scalar(select(AuthSession).where(AuthSession.id == uuid.UUID(session_id)))
    if revoked:
        raise AppException(code="E_UNAUTHORIZED", message="Session revoked", retryable=False)
        
    # Upsert Profile with email
    stmt = insert(Profile).values(
        id=user_id,
        email=email
    ).on_conflict_do_update(
        index_elements=['id'],
        set_={"email": email}
    )
    await session.execute(stmt)
    await session.commit()
        
    return user_id

async def get_current_session_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False, "verify_exp": False} # allow extracting session id even if expired for logout
        )
    except Exception:
        raise AppException(code="E_UNAUTHORIZED", message="Invalid token", retryable=False)
    
    session_id = payload.get("session_id")
    if not session_id:
        raise AppException(code="E_UNAUTHORIZED", message="Invalid token payload", retryable=False)
    return session_id
