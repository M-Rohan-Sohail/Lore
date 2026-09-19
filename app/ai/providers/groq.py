import httpx
from app.config import settings
from app.schemas.ai import AIResponse, AIProviderError

async def generate(system_prompt: str, user_prompt: str, temperature: float = 0.7) -> AIResponse:
    keys = settings.ai_provider_keys_parsed
    api_key = keys.get("groq")
    if not api_key:
        raise AIProviderError("groq", 500, "API key not configured")

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama3-8b-8192",
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
            raise AIProviderError("groq", 503, str(e))

    if response.status_code != 200:
        raise AIProviderError("groq", response.status_code, response.text)

    data = response.json()
    try:
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        tokens_in = usage.get("prompt_tokens", 0)
        tokens_out = usage.get("completion_tokens", 0)
    except (KeyError, IndexError):
        raise AIProviderError("groq", 500, "Unexpected response format")

    return AIResponse(
        content=content,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        provider="groq"
    )
