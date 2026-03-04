"""
Clara AI Pipeline – LLM Client (Groq free tier)
Provides a zero-cost interface to Llama models via Groq's free API.
Falls back to rule-based extraction if no API key is configured.
"""
from __future__ import annotations
import json, re, time
from scripts.config import GROQ_API_KEY, GROQ_MODEL, GROQ_FALLBACK, logger

_client = None

def _get_client():
    global _client
    if _client is None:
        if not GROQ_API_KEY or GROQ_API_KEY == "your_groq_api_key_here":
            logger.warning("No Groq API key configured – falling back to rule-based extraction")
            return None
        from groq import Groq
        _client = Groq(api_key=GROQ_API_KEY)
    return _client


def llm_extract_json(system_prompt: str, user_prompt: str, retries: int = 2) -> dict | None:
    """Call Groq LLM and parse JSON from response. Returns None on failure."""
    client = _get_client()
    if client is None:
        return None

    for attempt in range(retries + 1):
        model = GROQ_MODEL if attempt < retries else GROQ_FALLBACK
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                max_tokens=4096,
                response_format={"type": "json_object"},
            )
            text = resp.choices[0].message.content.strip()
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
            if match:
                try:
                    return json.loads(match.group(1).strip())
                except json.JSONDecodeError:
                    pass
            logger.warning(f"LLM returned non-JSON (attempt {attempt+1})")
        except Exception as e:
            logger.warning(f"LLM call failed (attempt {attempt+1}): {e}")
            if attempt < retries:
                time.sleep(2 ** attempt)
    return None


def llm_generate_text(system_prompt: str, user_prompt: str) -> str:
    """Call Groq LLM for free-form text generation."""
    client = _get_client()
    if client is None:
        return ""
    try:
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=4096,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"LLM text generation failed: {e}")
        return ""
