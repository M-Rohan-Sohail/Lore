import pytest
import datetime
import uuid
from PIL import Image
import io
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.db.base import Base
from app.db.models.accounts import Profile
from app.db.models.characters import Character
from app.db.models.recaps import ShareToken
from app.db.models.platform import AppFlag
from app.schemas.cards import CardKind
from app.services.cards import mint_share_token, resolve_and_render_card, revoke_share_token
from app.core.errors import AppException

@pytest.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest.fixture
async def db_session(db_engine):
    async_session = async_sessionmaker(db_engine, expire_on_commit=False)
    async with async_session() as session:
        yield session

@pytest.fixture
async def user_profile(db_session):
    profile = Profile(id=uuid.uuid4(), display_name="Tester", tz="UTC")
    db_session.add(profile)
    await db_session.commit()
    return profile

@pytest.mark.asyncio
async def test_card_mint_and_resolve(db_session: AsyncSession, user_profile: Profile):
    # Enable sharing
    flag = AppFlag(key="sharing_enabled", value=True)
    db_session.add(flag)

    char = Character(
        user_id=user_profile.id,
        class_name="Mage",
        tagline="A wise one",
        origin_blurb="From the hills",
        generated_by="fallback"
    )
    db_session.add(char)
    await db_session.commit()

    token, exp = await mint_share_token(db_session, user_profile.id, CardKind.CHARACTER, char.id)
    assert token

    png_bytes = await resolve_and_render_card(db_session, token)
    img = Image.open(io.BytesIO(png_bytes))
    assert img.size == (1080, 1920)

@pytest.mark.asyncio
async def test_card_enumeration_and_revocation(db_session: AsyncSession, user_profile: Profile):
    flag = AppFlag(key="sharing_enabled", value=True)
    db_session.add(flag)

    char = Character(
        user_id=user_profile.id,
        class_name="Knight",
        tagline="Brave",
        origin_blurb="From castle",
        generated_by="fallback"
    )
    db_session.add(char)
    await db_session.commit()

    token, _ = await mint_share_token(db_session, user_profile.id, CardKind.CHARACTER, char.id)

    # Enumeration
    for bad_token in [token[:-1] + "a", token + "b", "A" * 32]:
        with pytest.raises(AppException) as exc:
            await resolve_and_render_card(db_session, bad_token)
        assert exc.value.code == "E_NOT_FOUND"

    # Revocation
    await revoke_share_token(db_session, user_profile.id, token)

    # Resolve should fail
    with pytest.raises(AppException) as exc:
        await resolve_and_render_card(db_session, token)
    assert exc.value.code == "E_NOT_FOUND"

@pytest.mark.asyncio
async def test_card_referral_link(db_session: AsyncSession, user_profile: Profile):
    from app.services.card_templates import build_payload
    # Test that the referral link is included in the raw HTML payload built for rendering
    html = build_payload("character", {"display_name": "Hero"}, user_profile.referral_code)
    expected_url = f"lore.app/j/{user_profile.referral_code}"
    assert expected_url in html
    
    html = build_payload("weekly_recap", {"display_name": "Hero"}, user_profile.referral_code)
    assert expected_url in html
