"""
Centralised LLM service — async wrapper around the Ollama REST API.
"""

import json

import httpx

from backend.config import settings

_TIMEOUT = 120.0  # seconds — LLM calls can be slow


async def call_llama(
    prompt: str,
    expect_json: bool = False,
    system: str = "",
) -> str:
    """
    Send a prompt to the locally-running Ollama instance and return the
    response text.  If *expect_json* is True the ``format`` field is set to
    ``\"json\"`` so the model returns structured output.
    """
    url = f"{settings.OLLAMA_BASE_URL}/api/generate"
    payload: dict = {
        "model": settings.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    if system:
        payload["system"] = system
    if expect_json:
        payload["format"] = "json"

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "")
    except httpx.ConnectError:
        err = "Cannot connect to Ollama — is it running on " + settings.OLLAMA_BASE_URL + "?"
        return json.dumps({"error": err}) if expect_json else err
    except Exception as exc:
        err = f"LLM error: {exc}"
        return json.dumps({"error": err}) if expect_json else err
