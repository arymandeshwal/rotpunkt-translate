import json

from google import genai
from google.genai import types
from pydantic import BaseModel

from .base import TranslationProvider
from .utils import filter_relevant_glossary


class TranslationResponse(BaseModel):
    translations: list[str]


class GeminiProvider(TranslationProvider):
    """
    Google Gemini translation provider.
    Uses Gemini Flash and structured outputs to enforce the contract.
    """

    def __init__(self, api_key: str):
        """
        Initialize the Gemini provider.
        
        Args:
            api_key: The authentication key for the Gemini API.
        """
        self.client = genai.Client(
            vertexai=True,
            api_key=api_key
        )
        self.model = "gemini-3.5-flash-lite"

    async def translate(
        self, 
        texts: list[str], 
        source_language: str, 
        target_language: str,
        glossary: dict[str, str] | None = None
    ) -> list[str]:
        """
        Translate texts using Gemini 1.5 Flash.

        We use structured outputs (passing a Pydantic schema) to guarantee
        the LLM returns exactly a JSON object containing our array of strings,
        which perfectly aligns with the TranslationProvider contract.

        Args:
            texts: List of strings to translate.
            source_language: ISO language code of the input.
            target_language: ISO language code of the output.
            glossary: Optional dictionary mapping source terms to forced target terms.

        Returns:
            A list of translated strings matching the order and length of the input.
        """
        if not texts:
            return []

        # Find which items actually need translation (skip pure whitespace/empty)
        # to save tokens and prevent the LLM from hallucinating on empty strings.
        to_translate = []
        mapping = []
        for i, text in enumerate(texts):
            if text.strip():
                to_translate.append(text)
                mapping.append(i)

        if not to_translate:
            # Everything was empty or whitespace
            return list(texts)

        # Filter the glossary down to only terms present in the text to save tokens
        relevant_glossary = filter_relevant_glossary(to_translate, glossary)
        
        glossary_rules = ""
        if relevant_glossary:
            do_not_translate = []
            forced_translations = {}
            for k, v in relevant_glossary.items():
                if k == v:
                    do_not_translate.append(k)
                else:
                    forced_translations[k] = v
            
            if forced_translations:
                glossary_json = json.dumps(forced_translations, ensure_ascii=False)
                glossary_rules += f"\nGlossary (Force these exact translations): {glossary_json}"
            if do_not_translate:
                dnt_json = json.dumps(do_not_translate, ensure_ascii=False)
                glossary_rules += f"\nDo Not Translate (Keep these exact words): {dnt_json}"

        # Provide a strict prompt
        prompt = f"""You are an expert translator for the kitchen manufacturing industry.
Translate the following array of strings from {source_language} to {target_language}.
Preserve industry-specific terminology.{glossary_rules}
Return a JSON object containing a 'translations' array.
The output array MUST have exactly {len(to_translate)} items, matching the input.
Input array:
{json.dumps(to_translate, ensure_ascii=False)}
"""

        # We must await an async wrapper if genai doesn't natively expose an async client
        # In the new genai SDK, async is available via client.aio.models.generate_content
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=TranslationResponse,
                temperature=0.1,  # Low temperature for deterministic translation
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    disable=True,
                ),
            ),
        )

        try:
            # The SDK parses the structured output into a Pydantic object if possible,
            # or we parse the JSON string manually.
            if hasattr(response, "parsed") and response.parsed:
                parsed_translations = response.parsed.translations
            else:
                parsed_translations = json.loads(response.text)["translations"]

            # Fallback if the LLM hallucinated the wrong length
            if len(parsed_translations) != len(to_translate):
                raise ValueError(
                    f"LLM returned {len(parsed_translations)} items, expected {len(to_translate)}"
                )

            # Reconstruct the final array, merging the translations with preserved whitespace
            result = list(texts)
            for parsed_idx, original_idx in enumerate(mapping):
                result[original_idx] = parsed_translations[parsed_idx]

            return result

        except Exception as e:
            # In a production environment, we'd log this properly.
            # If the LLM fails structured output, we raise so the system knows to retry or fail.
            raise RuntimeError(f"Failed to parse Gemini translation response: {e}") from e
