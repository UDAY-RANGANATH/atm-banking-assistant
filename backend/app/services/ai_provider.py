"""
AI Provider abstraction (Phase 7).

A thin, provider-agnostic client for an OpenAI-compatible Chat Completions
endpoint. Configuration comes entirely from environment variables:

    AI_PROVIDER=openai_compatible
    AI_API_KEY=...          (server-side only, never sent to the browser)
    AI_BASE_URL=https://api.example.com/v1
    AI_MODEL=my-model-name

Design rules:
- No credentials are hardcoded; when the provider is "mock" (default) or no
  key/base URL is configured, the assistant runs a deterministic local engine
  and makes NO network calls.
- Every call is bounded by a timeout; transient failures retry a limited
  number of times; HTTP 429 rate limits trigger a cooldown window.
- All failures raise AIProviderError; callers fall back to the deterministic
  engine so the ATM never depends on an external AI service.
- Uses only the Python standard library (urllib in a worker thread) so no new
  runtime dependency is introduced.

Privacy: callers must already have sanitised the prompt. This module never
logs prompts, responses, or API keys.
"""

import json
import time
import urllib.error
import urllib.request
import asyncio
from typing import Any, Dict, List, Optional


class AIProviderError(Exception):
    """Raised for any provider failure: configuration, timeout, HTTP error,
    rate limiting, or an unusable response body."""

    def __init__(self, detail: str, status: Optional[int] = None,
                 retryable: bool = False):
        super().__init__(detail)
        self.detail = detail
        self.status = status
        self.retryable = retryable


class LLMProvider:
    """Env-configured provider client for an OpenAI-compatible chat API."""

    def __init__(self, provider: str, api_key: str, base_url: str,
                 model: str, timeout: float = 20.0, max_retries: int = 1,
                 rate_limit_cooldown: float = 10.0):
        self.provider = (provider or "mock").strip().lower()
        self.api_key = api_key or ""
        self.base_url = (base_url or "").strip().rstrip("/")
        self.model = model or ""
        self.timeout = timeout
        self.max_retries = max_retries
        self.rate_limit_cooldown = rate_limit_cooldown
        self._rate_limited_until = 0.0
        self._last_error: Optional[str] = None
        self._last_ok_at: Optional[float] = None

    # ------------------------------------------------------------------
    # Configuration / health
    # ------------------------------------------------------------------

    def is_configured(self) -> bool:
        """True only when a real provider with key, base URL and model is set."""
        return (
            self.provider not in ("", "mock", "none")
            and bool(self.api_key)
            and bool(self.base_url)
            and bool(self.model)
        )

    def status(self) -> Dict[str, Any]:
        """Non-sensitive health snapshot for GET /api/ai/health."""
        configured = self.is_configured()
        return {
            "provider": self.provider if configured else "mock",
            "configured": configured,
            "model": self.model if configured else "",
            "last_error": self._last_error,  # plain detail string, no secrets
            "last_ok_at": self._last_ok_at,
            "rate_limited": self._in_rate_limit_cooldown(),
        }

    def _in_rate_limit_cooldown(self) -> bool:
        return self._rate_limited_until > time.monotonic()

    # ------------------------------------------------------------------
    # Chat completion
    # ------------------------------------------------------------------

    async def complete(self, messages: List[Dict[str, str]]) -> str:
        """Run a chat completion and return the assistant message text.
        Raises AIProviderError on any failure."""
        if not self.is_configured():
            raise AIProviderError("provider_not_configured")
        if self._in_rate_limit_cooldown():
            raise AIProviderError(
                "provider_rate_limited", status=429, retryable=False
            )

        last: Optional[AIProviderError] = None
        for attempt in range(self.max_retries + 1):
            try:
                text = await self._post_chat(messages)
                self._last_ok_at = time.time()
                self._last_error = None
                return text
            except AIProviderError as exc:
                last = exc
                self._last_error = exc.detail
                if not exc.retryable or attempt >= self.max_retries:
                    break
                await asyncio.sleep(0.5 * (attempt + 1))
        raise last or AIProviderError("provider_failed")

    async def health_ping(self) -> bool:
        """Light connection check: a minimal completion with a hard short
        timeout. Returns True only when the provider answered."""
        try:
            await asyncio.wait_for(
                self.complete(
                    [
                        {"role": "user", "content": "ping"},
                    ]
                ),
                timeout=self.timeout,
            )
            return True
        except (AIProviderError, asyncio.TimeoutError):
            return False

    # ------------------------------------------------------------------
    # Networking (stdlib, executed off the event loop)
    # ------------------------------------------------------------------

    async def _post_chat(self, messages: List[Dict[str, str]]) -> str:
        payload = json.dumps(
            {
                "model": self.model,
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 600,
            }
        ).encode("utf-8")

        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        def _call() -> str:
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as resp:
                    body = resp.read().decode("utf-8", errors="replace")
                return _extract_text(body)
            except urllib.error.HTTPError as exc:
                if exc.code == 429:
                    self._rate_limited_until = time.monotonic() + self.rate_limit_cooldown
                    raise AIProviderError("provider_rate_limited", status=429,
                                          retryable=False) from exc
                if 500 <= exc.code < 600:
                    raise AIProviderError("provider_server_error", status=exc.code,
                                          retryable=True) from exc
                if exc.code == 401:
                    raise AIProviderError("provider_auth_error", status=401) from exc
                raise AIProviderError("provider_http_error", status=exc.code) from exc
            except urllib.error.URLError as exc:
                raise AIProviderError("provider_unreachable",
                                      retryable=True) from exc
            except AIProviderError:
                raise
            except Exception as exc:  # noqa: BLE001 - network layer
                raise AIProviderError("provider_failed",
                                      retryable=True) from exc

        result = await asyncio.to_thread(_call)
        if not result or not result.strip():
            raise AIProviderError("provider_empty_response")
        return result.strip()


def _extract_text(body: str) -> str:
    """Extract choices[0].message.content from a Chat Completions JSON body."""
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise AIProviderError("provider_invalid_body") from exc
    choices = data.get("choices") or []
    if not choices:
        raise AIProviderError("provider_invalid_body")
    content = (choices[0].get("message") or {}).get("content")
    if not isinstance(content, str):
        raise AIProviderError("provider_invalid_body")
    return content
