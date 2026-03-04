"""
translation module for generating bilingual README.
supports openai API and a simple fallback cache.
"""

import hashlib
import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

CACHE_PATH = Path("output/.translation_cache.json")


class Translator:
    """
    translates english descriptions to chinese.
    uses openai if available, otherwise returns original text.
    caches all translations to avoid redundant API calls.
    """

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._cache = self._load_cache()
        self._client = None

        if self._api_key:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self._api_key)
                logger.info("openai translator initialized")
            except ImportError:
                logger.warning("openai package not installed, translations disabled")

    def _load_cache(self) -> dict[str, str]:
        if CACHE_PATH.exists():
            try:
                return json.loads(CACHE_PATH.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    def _save_cache(self) -> None:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(json.dumps(self._cache, ensure_ascii=False, indent=2))

    def _cache_key(self, text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()

    def translate(self, text: str) -> str:
        """translate english text to concise chinese. returns original if no API."""
        if not text or not text.strip():
            return text

        key = self._cache_key(text)
        if key in self._cache:
            return self._cache[key]

        if not self._client:
            return text

        try:
            response = self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "you are a concise technical translator. "
                            "translate the following GitHub repo description "
                            "from English to Chinese. keep it under 80 chars. "
                            "preserve technical terms. no explanation needed."
                        ),
                    },
                    {"role": "user", "content": text},
                ],
                max_tokens=100,
                temperature=0.3,
            )
            translated = response.choices[0].message.content.strip()
            self._cache[key] = translated
            self._save_cache()
            return translated
        except Exception as e:
            logger.warning(f"translation failed for '{text[:40]}...': {e}")
            return text

    def translate_batch(self, texts: list[str]) -> list[str]:
        return [self.translate(t) for t in texts]
