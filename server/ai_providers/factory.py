from django.conf import settings
from .base import BaseAIProvider
from .mock_provider import MockAIProvider
from .gemini_provider import GeminiProvider

def get_ai_provider() -> BaseAIProvider:
    """
    Returns the configured AI provider based on settings.AI_PROVIDER
    """
    provider_name = getattr(settings, 'AI_PROVIDER', 'mock').lower()
    
    if provider_name == 'gemini':
        return GeminiProvider()
    
    # Default is Mock
    return MockAIProvider()
