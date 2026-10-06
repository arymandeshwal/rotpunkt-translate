import asyncio
from functools import partial

import deepl

from .base import TranslationProvider


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
        target_language: str
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

        # The translate_text method is synchronous, so we run it in a threadpool
        # to avoid blocking the asyncio event loop.
        loop = asyncio.get_running_loop()
        func = partial(
            self.translator.translate_text,
            texts,
            source_lang=source,
            target_lang=target,
            preserve_formatting=True
        )

        results = await loop.run_in_executor(None, func)

        # DeepL SDK returns a single TextResult if only one string was passed,
        # otherwise it returns a list of TextResult objects.
        if not isinstance(results, list):
            results = [results]

        return [r.text for r in results]
