import pytest
import uuid
import json
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.ai import AIRequest, AIResponse
from app.core.errors import AppException
from app.ai.gateway import narrate
from app.moderation.sensitive_router import record_sensitive_flag

with open("fixtures/redteam_corpus.json") as f:
    REDTEAM_FIXTURES = json.load(f)
    
with open("fixtures/injection_corpus.json") as f:
    INJECTION_FIXTURES = json.load(f)

@pytest.fixture
def mock_db():
    return AsyncMock(spec=AsyncSession)

@pytest.mark.asyncio
async def test_redteam_corpus_coverage(mock_db):
    blocked_count = 0
    sensitive_count = 0
    
    for fixture in REDTEAM_FIXTURES:
        request = AIRequest(user_id=uuid.uuid4(), system_prompt="Sys", user_prompt=fixture["text"])
        
        if fixture["category"] in ["self_harm", "sexual_content", "bullying"]:
            # Should be hard-blocked by input filter
            with pytest.raises(AppException) as exc:
                await narrate(request, mock_db)
            assert exc.value.code == "E_MODERATION_BLOCKED"
            blocked_count += 1
            
        elif fixture["category"] in ["ed_adjacent", "crisis", "protected_class_roast_bait"]:
            # Should hit sensitive router
            with patch("app.ai.providers.gemini.generate") as mock_generate:
                mock_generate.return_value = AIResponse(content="Clean", tokens_in=10, tokens_out=5, provider="gemini")
                with patch("app.ai.gateway.record_usage"):
                    await narrate(request, mock_db)
                
                # Verify system prompt modification
                called_sys = mock_generate.call_args.kwargs["system_prompt"]
                assert "SENSITIVE TOPIC DETECTED" in called_sys
                sensitive_count += 1

@pytest.mark.asyncio
async def test_injection_corpus_redaction(mock_db):
    for fixture in INJECTION_FIXTURES:
        request = AIRequest(user_id=uuid.uuid4(), system_prompt="Sys", user_prompt=fixture["text"])
        
        with patch("app.ai.providers.gemini.generate") as mock_generate:
            mock_generate.return_value = AIResponse(content="Clean", tokens_in=10, tokens_out=5, provider="gemini")
            with patch("app.ai.gateway.record_usage"):
                try:
                    await narrate(request, mock_db)
                except AppException as exc:
                    # Some injections might also hit BANNED_WORDS e.g. INJ-01 "ignore all previous instructions" is banned!
                    # "ignore all previous instructions" is in BANNED_WORDS so it will just hard-block.
                    pass
                else:
                    # If it wasn't hard-blocked, ensure it was redacted
                    called_user = mock_generate.call_args.kwargs["user_prompt"]
                    if fixture["category"] == "cyrillic_injection":
                        assert "[REDACTED_INSTRUCTION]" in called_user
                    elif fixture["category"] == "pii_leak":
                        assert "[REDACTED_EMAIL]" in called_user

@pytest.mark.asyncio
async def test_unsafe_output_seeding(mock_db):
    for fixture in REDTEAM_FIXTURES:
        if fixture["category"] == "unsafe_output_seeding":
            request = AIRequest(user_id=uuid.uuid4(), system_prompt="Sys", user_prompt="test")
            
            with patch("app.ai.providers.gemini.generate") as mock_gemini:
                mock_gemini.return_value = AIResponse(content=fixture["text"], tokens_in=10, tokens_out=5, provider="gemini")
                
                with patch("app.ai.providers.groq.generate") as mock_groq:
                    mock_groq.return_value = AIResponse(content="Safe response", tokens_in=10, tokens_out=5, provider="groq")
                    
                    with patch("app.ai.gateway.record_usage"):
                        resp = await narrate(request, mock_db)
                        
                        # Gemini should fail validation, fallback to Groq
                        assert resp.provider == "groq"
