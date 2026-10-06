from .base import TranslationProvider


class MockProvider(TranslationProvider):
    """
    Mock translation provider for tests and CI.
    It does not call any external API, simply prefixing strings.
    """

    async def translate(
        self, texts: list[str], source_language: str, target_language: str
    ) -> list[str]:
        """
        Simulate translating a list of strings by prefixing them with the target language.

        This method strictly obeys the TranslationProvider contract, including
        preserving empty or purely whitespace strings.

        Args:
            texts: List of strings to mock-translate.
            source_language: The original language code (ignored in mock).
            target_language: The target language code to include in the mock prefix.

        Returns:
            A list of mock-translated strings.
        """
        target = target_language.upper()
        # To strictly obey the contract, we preserve empty or purely whitespace strings
        # and only mock-translate strings with actual content.
        return [f"[MOCK_{target}] {text}" if text.strip() else text for text in texts]
