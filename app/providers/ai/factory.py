"""Factory for AI task idea providers."""
from app.core.config import Settings
from app.core.exceptions import AIProviderException
from app.providers.ai.base import TaskIdeaProvider


def build_task_idea_provider(settings: Settings) -> TaskIdeaProvider:
    provider_name = settings.ai_provider.strip().lower()

    if provider_name == "gemini":
        from app.providers.ai.gemini_task_provider import GeminiTaskIdeaProvider

        return GeminiTaskIdeaProvider(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
        )

    raise AIProviderException(
        f"Unsupported AI provider: {settings.ai_provider}",
        "unsupported_ai_provider",
    )