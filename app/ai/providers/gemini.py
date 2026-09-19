import httpx
from app.config import settings
from app.schemas.ai import AIResponse, AIProviderError

async def generate(system_prompt: str, user_prompt: str, temperature: float = 0.7) -> AIResponse:
    keys = settings.ai_provider_keys_parsed
    api_key = keys.get("gemini")
    if not api_key:
        raise AIProviderError("gemini", 500, "API key not configured")

    # This is a standard Google Gemini API integration
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": f"{system_prompt}\n\n{user_prompt}"}]
            }
        ],
        "generationConfig": {
            "temperature": temperature
        }
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, timeout=30.0)
        except httpx.RequestError as e:
            raise AIProviderError("gemini", 503, str(e))

    if response.status_code != 200:
        raise AIProviderError("gemini", response.status_code, response.text)

    data = response.json()
    try:
        content = data["candidates"][0]["content"]["parts"][0]["text"]
        # Gemini does not always return token counts by default in this endpoint shape, but let's parse usageMetadata if present
        usage = data.get("usageMetadata", {})
        tokens_in = usage.get("promptTokenCount", 0)
        tokens_out = usage.get("candidatesTokenCount", 0)
    except (KeyError, IndexError):
        raise AIProviderError("gemini", 500, "Unexpected response format")

    return AIResponse(
        content=content,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        provider="gemini"
    )
