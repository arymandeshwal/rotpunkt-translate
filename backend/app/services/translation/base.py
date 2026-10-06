from abc import ABC, abstractmethod


class TranslationProvider(ABC):
    """
    Abstract base class for all translation providers.
    Ensures a consistent interface across different translation engines
    (DeepL, Gemini, Mock).
    """

    @abstractmethod
    async def translate(
        self, 
        texts: list[str], 
        source_language: str, 
        target_language: str,
        glossary: dict[str, str] | None = None
    ) -> list[str]:
        """
        Translate a list of strings from source_language to target_language.

        Args:
            texts: List of strings to translate.
            source_language: ISO language code (e.g., 'de', 'en') of the input.
            target_language: ISO language code of the output.
            glossary: Optional dictionary mapping source terms to forced target terms.
                      If source == target, it signifies a "Do Not Translate" rule.

        Returns:
            A list of translated strings in the exact same order and length as `texts`.
        """
        pass
