import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.ai import AIRequest, AIResponse, validate_ai_output, AIProviderError
from app.ai.providers import gemini, groq, openrouter
from app.ai.ledger import record_usage
from app.core.errors import AppException
from app.moderation.input_filter import check_input
from app.moderation.sensitive_router import requires_sensitive_handling
from app.moderation.output_scan import scan_output

from app.db.models.accounts import Profile

logger = logging.getLogger(__name__)

async def narrate(request: AIRequest, db: AsyncSession) -> AIResponse:
    profile = await db.get(Profile, request.user_id)
    if profile and not profile.ai_personalization:
        # Strip out any personalization
        request.system_prompt += "\n\n[USER OPTED OUT OF AI PERSONALIZATION. Provide a generic, unpersonalized response.]"
        
    if not check_input(request.user_prompt):
        raise AppException(code="E_MODERATION_BLOCKED", message="Input violates moderation policies", retryable=False)
        
    system_prompt = request.system_prompt
    if requires_sensitive_handling(request.user_prompt):
        system_prompt += "\n\n[SENSITIVE TOPIC DETECTED. DO NOT generate harmful, explicit, or abusive content.]"

    providers = [
        ("gemini", gemini.generate),
        ("groq", groq.generate),
        ("openrouter", openrouter.generate)
    ]
    
    for name, generate_func in providers:
        try:
            response = await generate_func(
                system_prompt=system_prompt,
                user_prompt=request.user_prompt,
                temperature=request.temperature
            )
            
            validated_content = validate_ai_output(response.content)
            
            if not scan_output(validated_content):
                raise ValueError("Output moderation scan failed")
                
            response.content = validated_content
            
            await record_usage(
                db=db,
                user_id=request.user_id,
                budget_class=request.budget_class,
                provider=name,
                tokens_in=response.tokens_in,
                tokens_out=response.tokens_out
            )
            return response
            
        except AIProviderError as e:
            logger.warning(f"Provider {name} failed: {e.message} (status {e.status_code})")
            if 400 <= e.status_code < 500 and e.status_code != 429:
                raise AppException(code="E_AI_BAD_REQUEST", message=f"AI rejected prompt: {e.message}", retryable=False)
        except ValueError as e:
            # Output validation failed
            logger.warning(f"Provider {name} output validation failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error with provider {name}: {str(e)}")
            
    raise AppException(
        code="E_AI_GATEWAY_DOWN",
        message="All AI providers failed or timed out",
        retryable=True
    )
