"""Shared chat model factory — Gemini by default."""
from __future__ import annotations

from life_os.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL_NAME,
    LLM_PROVIDER,
    ANTHROPIC_API_KEY,
    LLM_MODEL,
)


def get_chat_model(*, temperature: float = 0.2):
    """Return the configured chat model. Default provider: gemini."""
    provider = (LLM_PROVIDER or "gemini").strip().lower()

    if provider in {"gemini", "google"}:
        if not GEMINI_API_KEY:
            raise RuntimeError(
                "GEMINI_API_KEY is missing. Set it in .env (default LLM is Gemini)."
            )
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=GEMINI_MODEL_NAME,
            google_api_key=GEMINI_API_KEY,
            temperature=temperature,
        )

    if provider == "anthropic":
        if not ANTHROPIC_API_KEY:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is missing. Set LLM_PROVIDER=gemini or add the key."
            )
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=LLM_MODEL,
            api_key=ANTHROPIC_API_KEY,
            temperature=temperature,
        )

    raise RuntimeError(f"Unsupported LLM_PROVIDER={provider!r}. Use gemini or anthropic.")
