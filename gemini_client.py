"""
Google Gemini API client wrapper.
"""

import os
from typing import Optional
from google.genai import Client, types
from dotenv import load_dotenv

load_dotenv()


class Config:
    GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY")
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
    """Stateful model wrapper for Google Gemini with persistent chat history."""

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

        # Build generation config once, reuse across all turns
        self._gen_config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            max_output_tokens=max_tokens,
            top_p=top_p,
        )

        # Single chat session shared across all generate_content() calls
        self._chat = self._client.chats.create(
            model=self.model_name,
            config=self._gen_config,
        )

    def generate_content(self, prompt: str, **kwargs) -> GenerativeResponse:
        """Send a message and return the model's reply.
        
        Automatically retries up to 2 times on empty responses before raising.
        """
        max_retries = 2
        last_exc: Exception = None

        for attempt in range(max_retries + 1):
            try:
                if kwargs:
                    # Override config for this turn only, but keep the same chat session
                    config = types.GenerateContentConfig(
                        system_instruction=self._gen_config.system_instruction,
                        temperature=kwargs.get('temperature', self._gen_config.temperature),
                        max_output_tokens=kwargs.get('max_tokens', self._gen_config.max_output_tokens),
                        top_p=kwargs.get('top_p', self._gen_config.top_p),
                    )
                    response = self._chat.send_message(prompt, config=config)
                else:
                    response = self._chat.send_message(prompt)

                text = getattr(response, 'text', None)
                if text is None:
                    if hasattr(response, 'message'):
                        text = getattr(response.message, 'content', None) or getattr(response.message, 'text', None)
                    if text is None and hasattr(response, 'output'):
                        output_items = getattr(response, 'output', []) or []
                        parts = []
                        for item in output_items:
                            contents = getattr(item, 'content', []) or []
                            for part in contents:
                                if hasattr(part, 'text') and part.text:
                                    parts.append(part.text)
                        text = ''.join(parts) if parts else None
                    if text is None and hasattr(response, 'choices'):
                        choices = getattr(response, 'choices', []) or []
                        if choices:
                            message = getattr(choices[0], 'message', None)
                            if message is not None:
                                text = getattr(message, 'content', None) or getattr(message, 'text', None)

                if text is None or text.strip() == '':
                    # Empty response — retry if attempts remain
                    last_exc = ValueError("Google Gemini returned an empty response text.")
                    if attempt < max_retries:
                        continue
                    raise last_exc

                return GenerativeResponse(text)

            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "rate" in error_msg.lower():
                    raise Exception(f"ResourceExhausted: Rate limit exceeded. {error_msg}")
                elif "401" in error_msg or "invalid" in error_msg.lower():
                    raise Exception(f"InvalidAPIKey: {error_msg}")
                # For other exceptions re-raise immediately (no benefit retrying)
                raise

    def reset_chat(self):
        """Start a fresh conversation while keeping the same config."""
        self._chat = self._client.chats.create(
            model=self.model_name,
            config=self._gen_config,
        )