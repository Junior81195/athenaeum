"""Pluggable LLM backend — supports Anthropic, OpenAI-compatible, Ollama, Gemini, and OpenRouter."""

import logging
import os
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, system: str, user: str, max_tokens: int = 1500) -> str:
        ...


class AnthropicProvider(LLMProvider):
    def __init__(self):
        from anthropic import Anthropic
        api_key = os.environ.get("LLM_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
        self._client = Anthropic(api_key=api_key)
        self._model = os.environ.get("LLM_MODEL", "claude-sonnet-4-6")

    def generate(self, system: str, user: str, max_tokens: int = 1500) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return response.content[0].text


class OpenAIProvider(LLMProvider):
    def __init__(self):
        from openai import OpenAI
        api_key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
        base_url = os.environ.get("LLM_BASE_URL") or None
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = os.environ.get("LLM_MODEL", "gpt-4o")

    def generate(self, system: str, user: str, max_tokens: int = 1500) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content


class OllamaProvider(LLMProvider):
    def __init__(self):
        import httpx
        self._client = httpx.Client(timeout=120.0)
        base_url = os.environ.get("LLM_BASE_URL", "http://localhost:11434")
        self._url = f"{base_url.rstrip('/')}/api/chat"
        self._model = os.environ.get("LLM_MODEL", "llama3.2")

    def generate(self, system: str, user: str, max_tokens: int = 1500) -> str:
        payload = {
            "model": self._model,
            "stream": False,
            "options": {"num_predict": max_tokens},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        response = self._client.post(self._url, json=payload)
        response.raise_for_status()
        return response.json()["message"]["content"]


class GeminiProvider(LLMProvider):
    def __init__(self):
        import google.generativeai as genai
        api_key = os.environ.get("LLM_API_KEY") or os.environ.get("GEMINI_API_KEY")
        genai.configure(api_key=api_key)
        model_name = os.environ.get("LLM_MODEL", "gemini-2.0-flash")
        self._model_name = model_name
        self._api_key = api_key

    def generate(self, system: str, user: str, max_tokens: int = 1500) -> str:
        import google.generativeai as genai
        genai.configure(api_key=self._api_key)
        model = genai.GenerativeModel(
            model_name=self._model_name,
            system_instruction=system,
        )
        response = model.generate_content(
            user,
            generation_config=genai.GenerationConfig(max_output_tokens=max_tokens),
        )
        return response.text


# Free models ranked best → worst for philosophy/persona RAG tasks.
# Deliberately diversified across backend providers to avoid shared rate limits.
# Venice backs: llama-3.3-70b, qwen3, hermes, mistral-small (shared rate limit pool)
# Independent backends: stepfun, upstage, z-ai, google (separate limits)
OPENROUTER_FREE_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",            # Venice — 70B Llama, best quality
    "stepfun/step-3.5-flash:free",                       # StepFun — 256K ctx, independent backend
    "upstage/solar-pro-3:free",                          # Upstage — 128K ctx, independent backend
    "z-ai/glm-4.5-air:free",                             # Z.ai — 131K ctx, independent backend
    "qwen/qwen3-next-80b-a3b-instruct:free",             # Venice — 80B Qwen3, 262K ctx
    "mistralai/mistral-small-3.1-24b-instruct:free",     # Venice — 24B Mistral
    "google/gemma-3-27b-it:free",                        # Google AI Studio — 27B Gemma
    "nousresearch/hermes-3-llama-3.1-405b:free",         # Venice — 405B persona-tuned
    "google/gemma-3-12b-it:free",                        # Google AI Studio — 12B fallback
    "meta-llama/llama-3.2-3b-instruct:free",             # Venice — 3B last resort
]


class OpenRouterProvider(LLMProvider):
    """OpenRouter with automatic fallback through free models (best → worst)."""

    OPENROUTER_BASE = "https://openrouter.ai/api/v1"

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self._api_key = api_key or os.environ.get("LLM_API_KEY") or os.environ.get("OPENROUTER_API_KEY", "")
        # If a specific model is set, use it alone (no fallback chain)
        self._fixed_model = model or os.environ.get("LLM_MODEL") or None

    def _make_client(self):
        from openai import OpenAI
        return OpenAI(
            api_key=self._api_key,
            base_url=self.OPENROUTER_BASE,
            default_headers={
                "HTTP-Referer": "https://athenaeum.herakles.dev",
                "X-Title": "Athenaeum",
            },
        )

    def _call_model(self, client, model: str, system: str, user: str, max_tokens: int) -> str:
        response = client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        text = response.choices[0].message.content or ""
        # Strip thinking blocks some models emit (e.g. <think>...</think>)
        import re
        text = re.sub(r"<think>.*?</think>\s*", "", text, flags=re.DOTALL).strip()
        return text

    def generate(self, system: str, user: str, max_tokens: int = 1500) -> str:
        client = self._make_client()

        if self._fixed_model:
            return self._call_model(client, self._fixed_model, system, user, max_tokens)

        # Fallback chain: try each free model until one succeeds
        last_err = None
        for model in OPENROUTER_FREE_MODELS:
            try:
                logger.info("OpenRouter: trying %s", model)
                result = self._call_model(client, model, system, user, max_tokens)
                logger.info("OpenRouter: success with %s", model)
                return result
            except Exception as e:
                logger.warning("OpenRouter: %s failed — %s", model, e)
                last_err = e
                continue

        raise RuntimeError(f"All OpenRouter free models failed. Last error: {last_err}")


_provider_instance: LLMProvider | None = None


def get_provider() -> LLMProvider:
    """Return the configured LLM provider (singleton per process)."""
    global _provider_instance
    if _provider_instance is None:
        name = os.environ.get("LLM_PROVIDER", "openrouter").lower()
        if name == "anthropic":
            _provider_instance = AnthropicProvider()
        elif name == "openai":
            _provider_instance = OpenAIProvider()
        elif name == "ollama":
            _provider_instance = OllamaProvider()
        elif name == "gemini":
            _provider_instance = GeminiProvider()
        elif name == "openrouter":
            _provider_instance = OpenRouterProvider()
        else:
            raise ValueError(
                f"Unknown LLM_PROVIDER={name!r}. "
                "Choose: anthropic | openai | ollama | gemini | openrouter"
            )
    return _provider_instance
