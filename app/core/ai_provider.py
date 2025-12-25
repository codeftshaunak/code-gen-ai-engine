"""AI provider integration for streaming code generation using OpenRouter."""

import asyncio
from typing import AsyncGenerator, Optional
from openai import AsyncOpenAI

from app.config.settings import settings


class AIProvider:
    """Manages AI provider client and streaming via OpenRouter."""

    def __init__(self):
        """Initialize AI provider client."""
        self._openrouter_client: Optional[AsyncOpenAI] = None

    def _get_openrouter_client(self) -> AsyncOpenAI:
        """Get or create OpenRouter client."""
        if not self._openrouter_client:
            if not settings.OPENROUTER_API_KEY:
                raise ValueError(
                    "OPENROUTER_API_KEY is required. Please set it in your .env file."
                )
            self._openrouter_client = AsyncOpenAI(
                api_key=settings.OPENROUTER_API_KEY,
                base_url=settings.OPENROUTER_BASE_URL
            )
        return self._openrouter_client

    async def stream_with_retry(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = None,
        max_tokens: int = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream AI response with retry logic.

        Args:
            model: Model identifier
            system_prompt: System instructions
            user_prompt: User message
            temperature: Sampling temperature (default: settings.DEFAULT_TEMPERATURE)
            max_tokens: Maximum tokens to generate (default: settings.MAX_TOKENS)

        Yields:
            Text chunks from AI response
        """
        temperature = temperature or settings.DEFAULT_TEMPERATURE
        max_tokens = max_tokens or settings.MAX_TOKENS

        retry_count = 0
        last_error = None

        while retry_count <= settings.MAX_RETRIES:
            try:
                # Stream the response
                async for chunk in self._stream_response(
                    model, system_prompt, user_prompt, temperature, max_tokens
                ):
                    yield chunk
                return  # Success - exit retry loop

            except Exception as error:
                last_error = error
                error_msg = str(error).lower()

                # Check if error is retryable
                is_retryable = any(
                    keyword in error_msg
                    for keyword in ["service unavailable", "rate limit", "timeout", "overloaded"]
                )

                if retry_count < settings.MAX_RETRIES and is_retryable:
                    retry_count += 1
                    wait_time = retry_count * settings.RETRY_DELAY_SECONDS
                    yield f"\n\n<!-- Retry {retry_count}/{settings.MAX_RETRIES + 1} after {wait_time}s... -->\n\n"
                    await asyncio.sleep(wait_time)
                else:
                    # Non-retryable error or max retries reached
                    raise

        # Should not reach here, but just in case
        if last_error:
            raise last_error

    async def _stream_response(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int
    ) -> AsyncGenerator[str, None]:
        """
        Stream response from OpenRouter.

        Args:
            model: Model identifier (e.g., 'anthropic/claude-3-5-sonnet-20241022')
            system_prompt: System instructions
            user_prompt: User message
            temperature: Sampling temperature
            max_tokens: Maximum tokens

        Yields:
            Text chunks from AI response
        """
        client = self._get_openrouter_client()

        # Stream using OpenAI-compatible API through OpenRouter
        stream = await client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            stream=True
        )

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


# Global AI provider instance
ai_provider = AIProvider()
