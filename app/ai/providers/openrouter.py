import httpx
from app.config import settings
from app.schemas.ai import AIResponse, AIProviderError

async def generate(system_prompt: str, user_prompt: str, temperature: float = 0.7) -> AIResponse:
    keys = settings.ai_provider_keys_parsed
    api_key = keys.get("openrouter")
    if not api_key:
        raise AIProviderError("openrouter", 500, "API key not configured")

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://lore.app",
        "X-Title": "LORE Core",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "anthropic/claude-3-haiku",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": temperature
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload, timeout=30.0)
        except httpx.RequestError as e:
            raise AIProviderError("openrouter", 503, str(e))

    if response.status_code != 200:
        raise AIProviderError("openrouter", response.status_code, response.text)

    data = response.json()
    try:
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        tokens_in = usage.get("prompt_tokens", 0)
        tokens_out = usage.get("completion_tokens", 0)
    except (KeyError, IndexError):
        raise AIProviderError("openrouter", 500, "Unexpected response format")

    return AIResponse(
        content=content,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        provider="openrouter"
    )
