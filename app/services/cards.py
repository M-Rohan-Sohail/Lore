import datetime
import secrets
import hashlib
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from fastapi import Request

from app.db.models.recaps import ShareToken, Recap
from app.db.models.characters import Character
from app.db.models.accounts import Profile
from app.core.errors import AppException
from app.schemas.cards import CardKind
from app.services.card_templates import build_payload
from app.services.card_render import render_html_to_png
from app.core.flags import require_flag

def _hash_token(token: str) -> str:
    """Hashes the token with SHA-256 for secure DB storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

async def mint_share_token(
    session: AsyncSession,
    user_id: uuid.UUID,
    kind: CardKind,
    artifact_id: uuid.UUID,
    ttl_days: int = 30
) -> tuple[str, datetime.datetime]:
    """Mints a new share token for the given artifact."""
    
    # Check kill switch per CP-16
    await require_flag(session, "sharing_enabled")

    # Verify ownership before minting
    if kind == CardKind.CHARACTER:
        char = await session.get(Character, artifact_id)
        if not char or char.user_id != user_id:
            raise AppException("E_AUTH_REQUIRED", "Not found or not owner")
    elif kind in (CardKind.WEEKLY_RECAP, CardKind.PARTY_RECAP, CardKind.QUIET_WEEK):
        recap = await session.get(Recap, artifact_id)
        # Note: Recap owner_id can be user_id or party_id. For now, we only allow users to mint for their own scope or if they are in the party.
        # Strict scope verification per CP-17
        if not recap:
            raise AppException("E_AUTH_REQUIRED", "Not found or not owner")
        if recap.scope == "user" and recap.owner_id != user_id:
            raise AppException("E_AUTH_REQUIRED", "Not found or not owner")
        if recap.scope == "party":
            # Must check if user is in party
            from app.db.models.party import PartyMember
            pm = await session.execute(
                select(PartyMember).where(PartyMember.party_id == recap.owner_id, PartyMember.user_id == user_id)
            )
            if not pm.scalar_one_or_none():
                raise AppException("E_NOT_PARTY_MEMBER", "Not a member of this party")
    elif kind == CardKind.LEVEL_UP:
        # artifact_id is profile.id
        if artifact_id != user_id:
            raise AppException("E_AUTH_REQUIRED", "Not found or not owner")
    else:
        raise AppException("E_VALIDATION", "Invalid card kind")

    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw_token)
    expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=ttl_days)

    st = ShareToken(
        kind=kind.value,
        artifact_id=artifact_id,
        token_hash=token_hash,
        created_by=user_id,
        expires_at=expires_at,
        card_kind=kind.value
    )
    session.add(st)
    await session.commit()
    
    return raw_token, expires_at

async def revoke_share_token(session: AsyncSession, user_id: uuid.UUID, raw_token: str) -> None:
    token_hash = _hash_token(raw_token)
    res = await session.execute(
        select(ShareToken).where(ShareToken.token_hash == token_hash)
    )
    st = res.scalar_one_or_none()
    
    if not st or st.created_by != user_id:
        raise AppException("E_AUTH_REQUIRED", "Not found or not owner")
        
    st.revoked_at = datetime.datetime.now(datetime.timezone.utc)
    await session.commit()

async def resolve_and_render_card(session: AsyncSession, raw_token: str) -> bytes:
    """Public endpoint logic: Resolves token and renders PNG. Returns raw bytes."""
    token_hash = _hash_token(raw_token)
    res = await session.execute(
        select(ShareToken).where(ShareToken.token_hash == token_hash)
    )
    st = res.scalar_one_or_none()
    
    now = datetime.datetime.now(datetime.timezone.utc)
    expires_at = st.expires_at if st else None
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=datetime.timezone.utc)
        
    if not st or (expires_at and expires_at < now) or st.revoked_at:
        # PDR CP-11 Step 4: Revoked or expired -> 404, not 403
        raise AppException("E_NOT_FOUND", "Card not found")

    kind = CardKind(st.card_kind) if st.card_kind else CardKind(st.kind)

    # Re-fetch the artifact to build the payload (ensure it still exists)
    raw_data = {}
    referral_code = ""

    # Always get the creator's profile for display name and referral
    creator = await session.get(Profile, st.created_by)
    if not creator:
        raise AppException("E_NOT_FOUND", "Card not found")

    referral_code = creator.referral_code
    
    if kind == CardKind.CHARACTER:
        char = await session.get(Character, st.artifact_id)
        if not char:
            raise AppException("E_NOT_FOUND", "Card not found")
        raw_data = {
            "display_name": creator.display_name,
            "class_name": char.class_name,
            "base_stats": creator.base_stats,
            "founding_player": creator.founding_player
        }
    elif kind == CardKind.LEVEL_UP:
        if creator.id != st.artifact_id:
            raise AppException("E_NOT_FOUND", "Card not found")
        # Find active character for class_name
        res_char = await session.execute(
            select(Character).where(Character.user_id == creator.id).order_by(Character.created_at.desc()).limit(1)
        )
        char = res_char.scalar_one_or_none()
        c_class = char.class_name if char else "Adventurer"
        raw_data = {
            "display_name": creator.display_name,
            "level": creator.level,
            "class_name": c_class,
            "founding_player": creator.founding_player
        }
    elif kind in (CardKind.WEEKLY_RECAP, CardKind.PARTY_RECAP, CardKind.QUIET_WEEK):
        recap = await session.get(Recap, st.artifact_id)
        if not recap or not recap.payload:
            raise AppException("E_NOT_FOUND", "Card not found")
            
        payload = recap.payload
        raw_data = {
            "display_name": creator.display_name,
            "episode_number": recap.episode_number,
            "episode_title": payload.get("episode_title"),
            "stat_deltas": payload.get("stat_deltas"),
            "narrator_quote": payload.get("narrator_quote"),
            "party_name": payload.get("party_name"), # Custom injected at recap gen
            "member_lines": payload.get("member_lines")
        }

    # Render pipeline
    html = build_payload(kind.value, raw_data, referral_code)
    png_bytes = await render_html_to_png(html)
    return png_bytes
