"""Settings API - surface current LLM config and test connections."""

import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

_DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-6",
    "openai": "gpt-4o",
    "ollama": "llama3.2",
    "gemini": "gemini-2.0-flash",
    "openrouter": "(auto — fallback chain)",
}


class SettingsResponse(BaseModel):
    provider: str
    model: str
    has_api_key: bool
    base_url: str | None


class TestRequest(BaseModel):
    provider: str
    model: str | None = None
    api_key: str | None = None
    base_url: str | None = None


@router.get("/settings", response_model=SettingsResponse)
def get_settings():
    """Return current server-side LLM configuration (no key exposure)."""
    provider = os.environ.get("LLM_PROVIDER", "anthropic").lower()
    model = os.environ.get("LLM_MODEL", _DEFAULT_MODELS.get(provider, ""))

    if provider == "anthropic":
        api_key = os.environ.get("LLM_API_KEY") or os.environ.get("ANTHROPIC_API_KEY", "")
    elif provider == "openai":
        api_key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
    elif provider == "gemini":
        api_key = os.environ.get("LLM_API_KEY") or os.environ.get("GEMINI_API_KEY", "")
    elif provider == "openrouter":
        api_key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENROUTER_API_KEY", "")
    else:
        api_key = os.environ.get("LLM_API_KEY", "")

    base_url = os.environ.get("LLM_BASE_URL") or None

    return SettingsResponse(
        provider=provider,
        model=model,
        has_api_key=bool(api_key),
        base_url=base_url,
    )


@router.post("/settings/test")
def test_connection(req: TestRequest):
    """Test an LLM connection with given credentials. Returns ok or error."""
    provider_name = req.provider.lower()

    try:
        if provider_name == "anthropic":
            import anthropic as sdk
            key = req.api_key or os.environ.get("LLM_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
            if not key:
                raise HTTPException(status_code=400, detail="No API key provided for Anthropic")
            model = req.model or "claude-haiku-4-5-20251001"
            client = sdk.Anthropic(api_key=key)
            resp = client.messages.create(
                model=model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Say 'ok'"}],
            )
            return {"ok": True, "response": resp.content[0].text.strip()}

        elif provider_name == "openai":
            from openai import OpenAI
            key = req.api_key or os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
            base_url = req.base_url or os.environ.get("LLM_BASE_URL") or None
            model = req.model or "gpt-4o-mini"
            client = OpenAI(api_key=key, base_url=base_url)
            resp = client.chat.completions.create(
                model=model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Say 'ok'"}],
            )
            return {"ok": True, "response": resp.choices[0].message.content.strip()}

        elif provider_name == "ollama":
            import httpx
            base_url = req.base_url or os.environ.get("LLM_BASE_URL", "http://localhost:11434")
            model = req.model or "llama3.2"
            url = f"{base_url.rstrip('/')}/api/chat"
            with httpx.Client(timeout=30.0) as client:
                r = client.post(url, json={
                    "model": model,
                    "stream": False,
                    "options": {"num_predict": 5},
                    "messages": [{"role": "user", "content": "Say ok"}],
                })
                r.raise_for_status()
                return {"ok": True, "response": r.json()["message"]["content"].strip()}

        elif provider_name == "gemini":
            import google.generativeai as genai
            key = req.api_key or os.environ.get("LLM_API_KEY") or os.environ.get("GEMINI_API_KEY")
            if not key:
                raise HTTPException(status_code=400, detail="No API key provided for Gemini")
            model_name = req.model or "gemini-2.0-flash"
            genai.configure(api_key=key)
            model = genai.GenerativeModel(model_name)
            resp = model.generate_content("Say 'ok'", generation_config=genai.GenerationConfig(max_output_tokens=10))
            return {"ok": True, "response": resp.text.strip()}

        elif provider_name == "openrouter":
            from openai import OpenAI
            key = req.api_key or os.environ.get("LLM_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
            if not key:
                raise HTTPException(status_code=400, detail="No API key provided for OpenRouter")
            model_name = req.model or "meta-llama/llama-3.2-3b-instruct:free"
            client = OpenAI(
                api_key=key,
                base_url="https://openrouter.ai/api/v1",
                default_headers={"HTTP-Referer": "https://athenaeum.herakles.dev", "X-Title": "Athenaeum"},
            )
            resp = client.chat.completions.create(
                model=model_name, max_tokens=10,
                messages=[{"role": "user", "content": "Say 'ok'"}],
            )
            return {"ok": True, "response": resp.choices[0].message.content.strip()}

        else:
            raise HTTPException(status_code=400, detail=f"Unknown provider: {provider_name!r}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
