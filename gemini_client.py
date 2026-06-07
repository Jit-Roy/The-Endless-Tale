"""
Google Gemini API client wrapper.
"""

import logging
import os
import time
from pathlib import Path
from typing import Optional
from google.genai import Client, types
from dotenv import load_dotenv

load_dotenv()

LOG_FILE_NAME = "gemini_api.log"
LOG_FILE_PATH = Path(__file__).resolve().parent / LOG_FILE_NAME


def _get_gemini_logger() -> logging.Logger:
    logger = logging.getLogger("gemini_client")
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(LOG_FILE_PATH, encoding="utf-8")
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(handler)
    logger.propagate = False
    logger.debug("Initialized Gemini logger at %s", LOG_FILE_PATH)
    return logger


logger = _get_gemini_logger()


class Config:
    GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY")
    BACKGROUND_GOOGLE_API_KEY: Optional[str] = os.getenv("BACKGROUND_GOOGLE_API_KEY") or GOOGLE_API_KEY
    DEFAULT_MODEL: str = "gemma-4-31b-it"
    MODEL_TEMPERATURE: float = 0.7
    MAX_TOKENS: int = 2048
    MAX_CONSECUTIVE_AI_TURNS: int = 3
    PRIORITY_RANDOMNESS: float = 0.1
    CHAT_STORAGE_DIR: str = "Chat_Logs"


class GenerativeResponse:
    """Lightweight wrapper around the raw API response text."""
    def __init__(self, content: str):
        self.text = content

    def __str__(self):
        return self.text


class GenerativeModel:
    """Stateless model wrapper for Google Gemini.

    Each call to generate_content() is a fresh, independent request.
    Context is passed explicitly via the prompt (and system_instruction for
    the persona) — the SDK accumulates no history between calls.

    This is intentional: the roleplay system manages all conversation context
    itself via timeline events and memory_context, so letting the SDK also
    accumulate history would cause every prior memory_context to be re-sent
    on every subsequent turn (double-feeding).
    """

    def __init__(
        self,
        model_name: str = Config.DEFAULT_MODEL,
        api_key: Optional[str] = None,
        system_instruction: Optional[str] = None,
        temperature: float = Config.MODEL_TEMPERATURE,
        max_tokens: int = Config.MAX_TOKENS,
        top_p: float = 1.0,
    ):
        self.model_name = model_name
        self.api_key = api_key or Config.GOOGLE_API_KEY

        if not self.api_key:
            raise ValueError(
                "GOOGLE_API_KEY not set. "
                "Please set it in your .env file or pass it to the constructor."
            )

        self._client = Client(api_key=self.api_key)

        # Config is built once and reused on every stateless call.
        # system_instruction carries the character persona so it never needs
        # to be repeated inside the prompt body.
        self._gen_config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            max_output_tokens=max_tokens,
            top_p=top_p,
        )

    def generate_content(self, prompt: str) -> GenerativeResponse:
        """Send a stateless request and return the model's reply.

        Each call is completely independent — no session history is kept.
        Retries up to 2 times on empty responses before raising.
        """
        max_retries = 2

        for attempt in range(max_retries + 1):
            start_time = time.perf_counter()
            logger.info(
                "Gemini request started: model=%s, attempt=%d, prompt_length=%d",
                self.model_name,
                attempt + 1,
                len(prompt or ""),
            )
            logger.debug("Gemini request payload:\n%s", prompt)

            try:
                response = self._client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=self._gen_config,
                )
                text = response.text

            except Exception as e:
                duration = time.perf_counter() - start_time
                error_msg = str(e)
                logger.exception(
                    "Gemini request failed: model=%s, attempt=%d, elapsed=%.4fs, error=%s",
                    self.model_name,
                    attempt + 1,
                    duration,
                    error_msg,
                )
                if "429" in error_msg or "rate" in error_msg.lower():
                    raise Exception(f"ResourceExhausted: Rate limit exceeded. {error_msg}")
                elif "401" in error_msg or "invalid" in error_msg.lower():
                    raise Exception(f"InvalidAPIKey: {error_msg}")
                raise

            # Handle empty response outside the try block — clean retry flow
            duration = time.perf_counter() - start_time
            if not text or not text.strip():
                logger.warning(
                    "Gemini returned empty text: model=%s, attempt=%d, elapsed=%.4fs",
                    self.model_name,
                    attempt + 1,
                    duration,
                )
                if attempt < max_retries:
                    continue
                raise ValueError("Gemini returned an empty response after retries.")

            logger.info(
                "Gemini response received: model=%s, attempt=%d, elapsed=%.4fs, response_length=%d",
                self.model_name,
                attempt + 1,
                duration,
                len(text),
            )
            logger.debug("Gemini response text:\n%s", text)
            return GenerativeResponse(text)