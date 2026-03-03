import asyncio
import logging
import json
from typing import Any, AsyncGenerator, Dict, Optional
from config import GEMINI_API_KEY, RETRY_MAX, RETRY_BASE

logger = logging.getLogger(__name__)


class GeminiNotAvailable(RuntimeError):
    pass


class Brain:
    """Wrapper around Google Gemini (official google-genai SDK).

    This implementation attempts to import the official SDK and provides
    a retrying async interface with a streaming generator placeholder.
    """

    def __init__(self):
        self.client = None
        self._init_client()

    def _init_client(self):
        try:
            # Official SDK import — may vary by release. Try common package names.
            import google_genai as genai  # type: ignore

            self.client = genai
            logger.info("google-genai SDK imported as google_genai")
        except Exception:
            try:
                # older experimental names
                from google import genai  # type: ignore

                self.client = genai
                logger.info("google.genai imported")
            except Exception:
                logger.warning("google-genai SDK not available; Gemini disabled")

    async def _request_with_retry(self, call_coro, max_attempts: int = RETRY_MAX) -> Any:
        attempt = 0
        while True:
            try:
                return await call_coro()
            except Exception as exc:
                attempt += 1
                backoff = RETRY_BASE * (2 ** (attempt - 1))
                logger.warning("Gemini request failed (attempt %d/%d): %s", attempt, max_attempts, exc)
                if attempt >= max_attempts:
                    logger.error("Max retries reached for Gemini request")
                    raise
                await asyncio.sleep(backoff)

    async def generate_text(self, prompt: str, stream: bool = False, functions: Optional[list] = None) -> str:
        """Generate text from Gemini. If streaming is requested this returns the
        final assembled text (streaming generator exists separately).
        """
        if not self.client:
            raise GeminiNotAvailable("google-genai SDK not installed")

        async def call():
            # TODO: adapt to real SDK call signature
            # Example placeholder using synchronous interface — replace with real async call
            if hasattr(self.client, "TextGenerationClient"):
                # hypothetical modern client
                c = self.client.TextGenerationClient()
                resp = c.generate(prompt=prompt)
                return getattr(resp, "text", str(resp))
            elif hasattr(self.client, "generate"):
                return self.client.generate(prompt)
            else:
                raise RuntimeError("Unsupported google-genai SDK shape")

        result = await self._request_with_retry(call)
        if isinstance(result, dict):
            return json.dumps(result)
        return str(result)

    async def stream_generate(self, prompt: str, functions: Optional[list] = None) -> AsyncGenerator[str, None]:
        """Async generator streaming partial responses. Implementation depends on SDK streaming support.

        Yields: string chunks
        """
        if not self.client:
            raise GeminiNotAvailable("google-genai SDK not installed")

        # Placeholder streaming: call generate_text and yield progressively
        full = await self.generate_text(prompt)
        # naive chunking for skeleton
        for i in range(0, len(full), 128):
            await asyncio.sleep(0.05)
            yield full[i : i + 128]
