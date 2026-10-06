import asyncio
from functools import partial

import deepl

from .base import TranslationProvider
from .utils import filter_relevant_glossary


class DeepLProvider(TranslationProvider):
    """
    DeepL translation provider using the official Python SDK.
    """

    def __init__(self, api_key: str):
        """
        Initialize the DeepL provider with an API key.

        Args:
            api_key: The authentication key for the DeepL API.
        """
        self.translator = deepl.Translator(api_key)

    async def translate(
        self, 
        texts: list[str], 
        source_language: str, 
        target_language: str,
        glossary: dict[str, str] | None = None
    ) -> list[str]:
        """
        Translate texts using the DeepL API.

        This method maps standard ISO codes to DeepL's expected formats (e.g., 'EN-US')
        and executes the synchronous DeepL SDK calls within an asyncio threadpool
        to prevent blocking the event loop.

        Args:
            texts: List of strings to translate.
            source_language: ISO language code of the input (e.g., 'de').
            target_language: ISO language code of the output (e.g., 'en').
            glossary: Optional dictionary mapping source terms to forced target terms.

        Returns:
            A list of translated strings matching the order and length of the input.
        """
        if not texts:
            return []

        # Map typical ISO codes to DeepL's expected uppercase format.
        # DeepL requires regional specifics for English and Portuguese targets.
        target = target_language.upper()
        if target == "EN":
            target = "EN-US"
        if target == "PT":
            target = "PT-PT"

        source = source_language.upper() if source_language else None

        # DeepL glossary creation and deletion are synchronous
        deepl_glossary = None
        relevant_glossary = filter_relevant_glossary(texts, glossary)
        
        loop = asyncio.get_running_loop()
        
        if relevant_glossary:
            if not source:
                raise ValueError("DeepL glossaries require a defined source_language.")
                
            # Create a temporary glossary on DeepL servers
            create_func = partial(
                self.translator.create_glossary,
                name="rotpunkt_temp_glossary",
                source_lang=source,
                target_lang=target,
                entries=relevant_glossary
            )
            deepl_glossary = await loop.run_in_executor(None, create_func)

        try:
            # The translate_text method is synchronous, so we run it in a threadpool
            func = partial(
                self.translator.translate_text,
                texts,
                source_lang=source,
                target_lang=target,
                preserve_formatting=True,
                glossary=deepl_glossary,
            )

            results = await loop.run_in_executor(None, func)
        finally:
            if deepl_glossary:
                delete_func = partial(self.translator.delete_glossary, deepl_glossary)
                await loop.run_in_executor(None, delete_func)

        # DeepL SDK returns a single TextResult if only one string was passed,
        # otherwise it returns a list of TextResult objects.
        if not isinstance(results, list):
            results = [results]

        return [r.text for r in results]
