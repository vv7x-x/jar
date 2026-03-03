import asyncio
import logging
import json
import os
from typing import Any, AsyncGenerator, Dict, Optional, Callable
from config import GEMINI_API_KEY, RETRY_MAX, RETRY_BASE

logger = logging.getLogger(__name__)


class GeminiNotAvailable(RuntimeError):
    pass


class Brain:
    """Robust wrapper around Google Gemini (official google-genai SDK).

    Features:
    - Attempts to import and configure the official `google-genai` SDK.
    - Auto-retry with exponential backoff.
    - Streaming support when SDK exposes it (defensive).
    - Registerable local function handlers (function-calling support).
    - Graceful fallback to a local echo/stub when SDK is missing.
    """

    def __init__(self):
        self.client = None
        self.handlers: Dict[str, Callable[..., Any]] = {}
        self._init_client()

    def _init_client(self):
        try:
            # Preferred package name
            import google_genai as genai  # type: ignore

            self.client = genai
            # ensure SDK can pick the API key from env
            try:
                if GEMINI_API_KEY:
                    os.environ.setdefault("GOOGLE_API_KEY", GEMINI_API_KEY)
            except Exception:
                pass
            logger.info("google-genai SDK imported as google_genai")
            return
        except Exception:
            logger.debug("google_genai import failed, trying google.genai")

        try:
            from google import genai  # type: ignore

            self.client = genai
            logger.info("google.genai imported")
            try:
                if GEMINI_API_KEY:
                    os.environ.setdefault("GOOGLE_API_KEY", GEMINI_API_KEY)
            except Exception:
                pass
            return
        except Exception:
            logger.warning("google-genai SDK not available; Gemini disabled")
            self.client = None

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

    def register_function(self, name: str, func: Callable[..., Any]):
        """Register a local function that the model can call via function-calling."""
        self.handlers[name] = func

    def _parse_response(self, raw: Any) -> Dict[str, Any]:
        """Try to extract a dict with keys 'text' or 'function_call' from SDK response."""
        # If already a dict
        if isinstance(raw, dict):
            return raw

        # If has attribute 'text'
        if hasattr(raw, "text"):
            return {"text": getattr(raw, "text")}

        # If has 'output' or similar
        if hasattr(raw, "output"):
            out = getattr(raw, "output")
            try:
                if isinstance(out, (list, tuple)) and len(out) > 0:
                    first = out[0]
                    if isinstance(first, dict) and "content" in first:
                        content = first["content"]
                        if isinstance(content, list) and len(content) > 0:
                            c0 = content[0]
                            if isinstance(c0, dict) and "text" in c0:
                                return {"text": c0["text"]}
            except Exception:
                pass

        # Fallback: convert to string
        return {"text": str(raw)}

    async def generate_text(self, prompt: str, stream: bool = False, functions: Optional[list] = None) -> str:
        """Generate text from Gemini. Supports function-calling and returns final text.

        If the SDK is missing, returns a local fallback echo reply.
        """
        if not self.client:
            # graceful fallback: echo
            logger.warning("Gemini SDK not available — using local fallback response")
            return f"[local-fallback] {prompt}"

        async def call():
            # Try several SDK shapes defensively and run sync calls in an executor
            loop = asyncio.get_event_loop()

            # 1) TextGenerationClient
            if hasattr(self.client, "TextGenerationClient"):
                C = self.client.TextGenerationClient()
                if hasattr(C, "generate"):
                    return await loop.run_in_executor(None, lambda: C.generate(prompt=prompt))

            # 2) ResponsesClient / Responses
            if hasattr(self.client, "ResponsesClient"):
                C = self.client.ResponsesClient()
                if hasattr(C, "generate"):
                    return await loop.run_in_executor(None, lambda: C.generate(prompt=prompt))

            # 3) top-level convenience function
            if hasattr(self.client, "generate"):
                return await loop.run_in_executor(None, lambda: self.client.generate(prompt))

            # 4) client.Client() pattern
            if hasattr(self.client, "Client"):
                c = self.client.Client()
                if hasattr(c, "generate"):
                    return await loop.run_in_executor(None, lambda: c.generate(prompt))

            raise RuntimeError("Unsupported google-genai SDK shape; please adapt core/brain.py")

        raw = await self._request_with_retry(call)

        parsed = self._parse_response(raw)

        # handle function call if present
        fc = parsed.get("function_call") or parsed.get("functionCall")
        if fc:
            name = fc.get("name")
            args = fc.get("arguments") or {}
            if name and name in self.handlers:
                try:
                    result = self.handlers[name](**args)
                except Exception as exc:
                    result = {"error": str(exc)}
                return json.dumps({"function": name, "result": result})

        return parsed.get("text", json.dumps(parsed))

    async def stream_generate(self, prompt: str, functions: Optional[list] = None) -> AsyncGenerator[str, None]:
        """Yield streaming chunks when SDK supports streaming; otherwise yield chunked final text."""
        if not self.client:
            raise GeminiNotAvailable("google-genai SDK not installed")

        # Try SDK streaming patterns
        loop = asyncio.get_event_loop()

        try:
            # TextGenerationClient.stream pattern
            if hasattr(self.client, "TextGenerationClient"):
                C = self.client.TextGenerationClient()
                if hasattr(C, "stream"):
                    def gen():
                        for chunk in C.stream(prompt=prompt):
                            yield chunk
                    for ch in await loop.run_in_executor(None, lambda: list(gen())):
                        yield str(ch)
                    return

            # ResponsesClient.stream pattern
            if hasattr(self.client, "ResponsesClient"):
                C = self.client.ResponsesClient()
                if hasattr(C, "stream"):
                    def gen2():
                        for p in C.stream(prompt=prompt):
                            yield p
                    for ch in await loop.run_in_executor(None, lambda: list(gen2())):
                        yield str(ch)
                    return
        except Exception:
            logger.debug("SDK streaming failed or not available; falling back to non-streaming")

        # Fallback: call non-streaming and chunk
        full = await self.generate_text(prompt, stream=False, functions=functions)
        for i in range(0, len(full), 128):
            await asyncio.sleep(0.02)
            yield full[i : i + 128]
