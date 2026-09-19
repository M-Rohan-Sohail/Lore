from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.db.session import get_db
from app.deps import get_current_user
from app.db.models.accounts import Profile
from app.core.envelope import success, error
from app.schemas.cards import ShareCardRequest, ShareCardResponse
from app.services.cards import mint_share_token, revoke_share_token, resolve_and_render_card
from app.core.errors import AppException

router = APIRouter(prefix="/v1/cards", tags=["cards"])

@router.post("/share")
async def share_card(
    payload: ShareCardRequest,
    current_user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    token, expires_at = await mint_share_token(
        session=db,
        user_id=current_user_id,
        kind=payload.kind,
        artifact_id=payload.artifact_id
    )
    return success(ShareCardResponse(token=token, expires_at=expires_at).model_dump())

@router.post("/{token}/revoke")
async def revoke_card(
    token: str,
    current_user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await revoke_share_token(db, current_user_id, token)
    return success({"revoked": True})

@router.get("/{token}")
async def render_card(token: str, db: AsyncSession = Depends(get_db)):
    try:
        png_bytes = await resolve_and_render_card(db, token)
        return Response(content=png_bytes, media_type="image/png")
    except AppException as e:
        if e.code == "E_NOT_FOUND":
            return Response(status_code=404, content="Card not found")
        raise e
