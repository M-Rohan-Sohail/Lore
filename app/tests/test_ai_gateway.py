import pytest
import uuid
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.ai import AIRequest, AIResponse, AIProviderError
from app.core.errors import AppException
from app.ai.gateway import narrate

@pytest.fixture
def mock_db():
    db = AsyncMock(spec=AsyncSession)
    return db

@pytest.mark.asyncio
@patch("app.ai.providers.gemini.generate")
@patch("app.ai.providers.groq.generate")
@patch("app.ai.gateway.record_usage")
async def test_gateway_failover_success(mock_record_usage, mock_groq, mock_gemini, mock_db):
    # Gemini fails with 503
    mock_gemini.side_effect = AIProviderError("gemini", 503, "Service Unavailable")
    # Groq succeeds
    mock_groq.return_value = AIResponse(content="Hello Groq", tokens_in=10, tokens_out=5, provider="groq")
    
    request = AIRequest(user_id=uuid.uuid4(), system_prompt="Sys", user_prompt="User")
    
    response = await narrate(request, mock_db)
    
    assert response.content == "Hello Groq"
    assert response.provider == "groq"
    mock_gemini.assert_called_once()
    mock_groq.assert_called_once()
    mock_record_usage.assert_called_once()

@pytest.mark.asyncio
@patch("app.ai.providers.gemini.generate")
@patch("app.ai.providers.groq.generate")
@patch("app.ai.providers.openrouter.generate")
async def test_gateway_all_down(mock_openrouter, mock_groq, mock_gemini, mock_db):
    # All fail with 503
    mock_gemini.side_effect = AIProviderError("gemini", 503, "Service Unavailable")
    mock_groq.side_effect = AIProviderError("groq", 503, "Service Unavailable")
    mock_openrouter.side_effect = AIProviderError("openrouter", 503, "Service Unavailable")
    
    request = AIRequest(user_id=uuid.uuid4(), system_prompt="Sys", user_prompt="User")
    
    with pytest.raises(AppException) as exc:
        await narrate(request, mock_db)
        
    assert exc.value.code == "E_AI_GATEWAY_DOWN"
    mock_gemini.assert_called_once()
    mock_groq.assert_called_once()
    mock_openrouter.assert_called_once()

@pytest.mark.asyncio
@patch("app.ai.providers.gemini.generate")
@patch("app.ai.providers.groq.generate")
async def test_gateway_bad_request_no_failover(mock_groq, mock_gemini, mock_db):
    # Gemini fails with 400 (e.g. content policy block or bad prompt)
    mock_gemini.side_effect = AIProviderError("gemini", 400, "Bad Request")
    
    request = AIRequest(user_id=uuid.uuid4(), system_prompt="Sys", user_prompt="User")
    
    with pytest.raises(AppException) as exc:
        await narrate(request, mock_db)
        
    assert exc.value.code == "E_AI_BAD_REQUEST"
    mock_gemini.assert_called_once()
    # Should not failover to groq
    mock_groq.assert_not_called()
