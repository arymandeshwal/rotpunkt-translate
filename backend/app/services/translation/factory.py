from app.config import get_settings
from app.services.translation.base import TranslationProvider
from app.services.translation.deepl_provider import DeepLProvider
from app.services.translation.gemini_provider import GeminiProvider
from app.services.translation.mock_provider import MockProvider


def get_translation_provider() -> TranslationProvider:
    """
    Factory function to instantiate and return the correct translation provider
    based on the application configuration.

    This function should be used as a FastAPI dependency or directly in workers.
    """
    settings = get_settings()
    provider_name = settings.translation_provider.lower()

    if provider_name == "deepl":
        if not settings.deepl_api_key:
            raise ValueError(
                "DEEPL_API_KEY environment variable is required to use the DeepL provider."
            )
        return DeepLProvider(api_key=settings.deepl_api_key)

    elif provider_name == "gemini":
        if not settings.gemini_api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is required to use the Gemini provider."
            )
        return GeminiProvider(api_key=settings.gemini_api_key)

    elif provider_name == "mock":
        return MockProvider()

    else:
        raise ValueError(f"Unknown translation provider configured: {provider_name}")
