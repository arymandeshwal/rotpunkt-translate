from unittest.mock import patch

import pytest

from app.config import Settings
from app.services.translation.deepl_provider import DeepLProvider
from app.services.translation.factory import get_translation_provider
from app.services.translation.gemini_provider import GeminiProvider
from app.services.translation.mock_provider import MockProvider


@pytest.fixture
def mock_settings():
    with patch("app.services.translation.factory.get_settings") as mock:
        yield mock


def test_factory_mock_provider(mock_settings):
    mock_settings.return_value = Settings(translation_provider="mock")
    provider = get_translation_provider()
    assert isinstance(provider, MockProvider)


def test_factory_deepl_provider(mock_settings):
    mock_settings.return_value = Settings(translation_provider="deepl", deepl_api_key="test_key")
    provider = get_translation_provider()
    assert isinstance(provider, DeepLProvider)


def test_factory_deepl_missing_key(mock_settings):
    mock_settings.return_value = Settings(translation_provider="deepl", deepl_api_key=None)
    with pytest.raises(ValueError, match="DEEPL_API_KEY"):
        get_translation_provider()


def test_factory_gemini_provider(mock_settings):
    mock_settings.return_value = Settings(translation_provider="gemini", gemini_api_key="test_key")
    provider = get_translation_provider()
    assert isinstance(provider, GeminiProvider)


def test_factory_gemini_missing_key(mock_settings):
    mock_settings.return_value = Settings(translation_provider="gemini", gemini_api_key=None)
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        get_translation_provider()
