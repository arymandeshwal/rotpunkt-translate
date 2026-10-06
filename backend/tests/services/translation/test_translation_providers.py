from unittest.mock import MagicMock, patch

import pytest

from app.services.translation.base import TranslationProvider
from app.services.translation.deepl_provider import DeepLProvider
from app.services.translation.gemini_provider import GeminiProvider
from app.services.translation.mock_provider import MockProvider


async def run_provider_contract_tests(provider: TranslationProvider):
    """
    Shared contract tests that MUST pass for all translation providers.
    Guarantees consistent input/output boundaries across engines.
    """

    # 1. Output length matches input length exactly
    texts = ["Hello", "Kitchen", "Cabinet"]
    results = await provider.translate(texts, "en", "de")
    assert len(results) == 3
    assert isinstance(results, list)
    assert all(isinstance(r, str) for r in results)

    # 2. Empty lists are handled gracefully
    empty_results = await provider.translate([], "en", "de")
    assert empty_results == []

    # 3. Empty strings and pure whitespace are preserved
    # (they should not cause errors, crash, or shift the array length)
    whitespace_texts = ["", "   ", "Valid"]
    ws_results = await provider.translate(whitespace_texts, "en", "de")
    assert len(ws_results) == 3
    # The third item should definitely be modified/translated
    assert ws_results[2] != "Valid" or isinstance(provider, MockProvider)
    # The first item is completely empty so it should likely stay empty
    assert ws_results[0] == ""


@pytest.mark.asyncio
async def test_mock_provider():
    provider = MockProvider()
    await run_provider_contract_tests(provider)

    # Provider-specific behavior test
    texts = ["Testing"]
    res = await provider.translate(texts, "en", "es")
    assert res[0] == "[MOCK_ES] Testing"


@pytest.mark.asyncio
async def test_deepl_provider():
    # Mock the underlying deepl library so we don't hit the real API
    with patch("app.services.translation.deepl_provider.deepl.Translator") as MockTranslator:
        mock_instance = MockTranslator.return_value

        def fake_translate(texts, **kwargs):
            class FakeResult:
                def __init__(self, t):
                    self.text = t if not t.strip() else f"[DEEPL] {t}"

            if isinstance(texts, str):
                return FakeResult(texts)
            return [FakeResult(t) for t in texts]

        mock_instance.translate_text.side_effect = fake_translate

        provider = DeepLProvider("fake_api_key")

        # Test against the shared contract
        await run_provider_contract_tests(provider)

        # Test specific mapping behavior (e.g. en -> EN-US for DeepL)
        res = await provider.translate(["Hello"], "de", "en")
        assert res[0] == "[DEEPL] Hello"

        # Verify it passed the right args to DeepL
        mock_instance.translate_text.assert_called_with(
            ["Hello"], source_lang="DE", target_lang="EN-US", preserve_formatting=True
        )


@pytest.mark.asyncio
async def test_gemini_provider():
    # Mock the google genai client so we don't hit the real API
    with patch("app.services.translation.gemini_provider.genai.Client") as MockClient:
        mock_instance = MockClient.return_value
        mock_aio = MagicMock()
        mock_instance.aio = mock_aio

        async def fake_generate_content(model, contents, config, **kwargs):
            class FakeResponse:
                def __init__(self, texts_in_prompt):
                    # We have to parse the JSON array out of the prompt mock
                    import json

                    # extract the JSON block from the end of the prompt
                    json_str = contents.split("Input array:\n")[-1]
                    input_array = json.loads(json_str)

                    translated = [f"[GEMINI] {t}" for t in input_array]
                    self.text = json.dumps({"translations": translated})
                    self.parsed = None

            return FakeResponse(contents)

        mock_aio.models.generate_content.side_effect = fake_generate_content

        provider = GeminiProvider("fake_api_key")

        # Test against the shared contract
        await run_provider_contract_tests(provider)

        # Test specific gemini behavior
        res = await provider.translate(["Hello", "World"], "en", "de")
        assert res[0] == "[GEMINI] Hello"
        assert res[1] == "[GEMINI] World"
