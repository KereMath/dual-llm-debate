"""
API Client Wrappers
Unified interface for Claude (Anthropic) and Gemini (Google) APIs
"""

import logging
from typing import Optional
from anthropic import Anthropic
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .config import config

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# INITIALIZE CLIENTS
# ═══════════════════════════════════════════════════════════

# Anthropic Claude
anthropic_client = Anthropic(api_key=config.ANTHROPIC_API_KEY) if config.ANTHROPIC_API_KEY else None

# Google Gemini - Initialize new client
if config.GOOGLE_API_KEY:
    gemini_client = genai.Client(api_key=config.GOOGLE_API_KEY)
else:
    gemini_client = None


# ═══════════════════════════════════════════════════════════
# CLAUDE API WRAPPER
# ═══════════════════════════════════════════════════════════

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    reraise=True
)
def call_claude_api(
    prompt: str,
    system_prompt: str,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> str:
    """
    Call Claude API with retry logic (5 attempts with exponential backoff)

    Args:
        prompt: User message
        system_prompt: System instruction
        temperature: Override default temperature
        max_tokens: Override default max tokens

    Returns:
        Generated text

    Raises:
        Exception: If API call fails after retries
    """
    if not anthropic_client:
        raise ValueError("Anthropic API key not configured")

    temp = temperature if temperature is not None else config.CLAUDE_TEMPERATURE
    tokens = max_tokens if max_tokens is not None else config.CLAUDE_MAX_TOKENS

    logger.debug(f"Calling Claude API (temp={temp}, max_tokens={tokens})")

    try:
        response = anthropic_client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=tokens,
            temperature=temp,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}]
        )

        text = response.content[0].text
        logger.debug(f"Claude response: {len(text)} chars")
        return text

    except Exception as e:
        logger.warning(f"Claude API error (will retry): {e}")
        raise


# ═══════════════════════════════════════════════════════════
# GEMINI API WRAPPER
# ═══════════════════════════════════════════════════════════

@retry(
    stop=stop_after_attempt(6),
    wait=wait_exponential(multiplier=3, min=10, max=90),
    reraise=True
)
def _generate_gemini_content(model: str, prompt: str, system_prompt: str,
                             temp: float, tokens: int) -> str:
    """Single-model Gemini call with retry/backoff.

    Waits start at 10s and grow to 90s: free-tier 429s are per-minute rate
    limits, so retrying faster than the window resets just burns the quota.
    """

    logger.debug(f"Calling Gemini API (model={model}, temp={temp}, max_tokens={tokens})")

    try:
        # NOTE: deliberately NO Google Search grounding tool here. Both agents
        # must argue from the SAME shared context (Truth = A ∩ B); giving
        # Gemini private live-web access would break that symmetry. Web
        # evidence enters the pipeline only through the shared Tavily
        # grounding phase. (Grounded calls also have a separate, much
        # smaller free-tier quota, which throttled whole runs.)
        response = gemini_client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temp,
                max_output_tokens=tokens,
                system_instruction=system_prompt
            )
        )

        # Extract text from response - handle different response structures
        if response.text:
            text = response.text
        elif response.candidates and len(response.candidates) > 0:
            candidate = response.candidates[0]
            if candidate.content and candidate.content.parts:
                text = candidate.content.parts[0].text
            else:
                raise ValueError("No content in response candidate")
        else:
            raise ValueError("No valid response from Gemini API")

        logger.debug(f"Gemini response: {len(text)} chars")
        return text

    except Exception as e:
        logger.error(f"Gemini API error ({model}): {e}")
        raise


def call_gemini_api(
    prompt: str,
    system_prompt: str,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> str:
    """
    Call Gemini API with retry logic and an optional fallback model.

    The primary model (GEMINI_MODEL) is tried with exponential backoff;
    if it is still failing (e.g. 503 "high demand" spikes on the free tier),
    the call is repeated once more against GEMINI_FALLBACK_MODEL.

    Args:
        prompt: User message
        system_prompt: System instruction
        temperature: Override default temperature
        max_tokens: Override default max tokens

    Returns:
        Generated text

    Raises:
        Exception: If both the primary and the fallback model fail
    """
    if not gemini_client:
        raise ValueError("Google API key not configured")

    temp = temperature if temperature is not None else config.GEMINI_TEMPERATURE
    tokens = max_tokens if max_tokens is not None else config.GEMINI_MAX_TOKENS

    try:
        return _generate_gemini_content(config.GEMINI_MODEL, prompt, system_prompt, temp, tokens)
    except Exception as primary_err:
        fallback = config.GEMINI_FALLBACK_MODEL
        if not fallback or fallback == config.GEMINI_MODEL:
            raise
        logger.warning(
            f"Primary Gemini model '{config.GEMINI_MODEL}' exhausted retries "
            f"({primary_err}); falling back to '{fallback}'"
        )
        return _generate_gemini_content(fallback, prompt, system_prompt, temp, tokens)


# ═══════════════════════════════════════════════════════════
# STRUCTURED OUTPUT CALLS
# The debate round's comparison is schema-enforced instead of
# parsed out of free text: Claude via forced tool-use, Gemini
# via response_schema. The regex parser remains only as a
# fallback for these calls failing outright.
# ═══════════════════════════════════════════════════════════

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    reraise=True
)
def call_claude_structured(
    prompt: str,
    system_prompt: str,
    schema: dict,
    tool_name: str = "submit_comparison",
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> dict:
    """
    Call Claude with a forced tool-use so the response IS the schema.

    Returns:
        The tool input as a dict (guaranteed to match the JSON schema)
    """
    if not anthropic_client:
        raise ValueError("Anthropic API key not configured")

    temp = temperature if temperature is not None else config.CLAUDE_TEMPERATURE
    tokens = max_tokens if max_tokens is not None else config.CLAUDE_MAX_TOKENS

    response = anthropic_client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=tokens,
        temperature=temp,
        system=system_prompt,
        messages=[{"role": "user", "content": prompt}],
        tools=[{
            "name": tool_name,
            "description": "Submit the structured claim-by-claim comparison for this debate round",
            "input_schema": schema,
        }],
        tool_choice={"type": "tool", "name": tool_name},
    )

    for block in response.content:
        if block.type == "tool_use":
            return block.input

    raise ValueError("Claude returned no tool_use block despite forced tool_choice")


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=3, min=10, max=90),
    reraise=True
)
def _generate_gemini_structured(model: str, prompt: str, system_prompt: str,
                                response_model, temp: float, tokens: int) -> dict:
    """Single-model structured Gemini call (response_schema-enforced JSON)"""
    import json as _json

    response = gemini_client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=temp,
            max_output_tokens=tokens,
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=response_model,
        )
    )

    parsed = getattr(response, "parsed", None)
    if parsed is not None:
        return parsed.model_dump() if hasattr(parsed, "model_dump") else parsed
    if response.text:
        return _json.loads(response.text)
    raise ValueError("No structured response from Gemini API")


def call_gemini_structured(
    prompt: str,
    system_prompt: str,
    response_model,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> dict:
    """
    Structured Gemini call with the same primary/fallback-model policy
    as call_gemini_api.

    Args:
        response_model: a Pydantic model class describing the output schema

    Returns:
        Dict matching the schema
    """
    if not gemini_client:
        raise ValueError("Google API key not configured")

    temp = temperature if temperature is not None else config.GEMINI_TEMPERATURE
    tokens = max_tokens if max_tokens is not None else config.GEMINI_MAX_TOKENS

    try:
        return _generate_gemini_structured(config.GEMINI_MODEL, prompt, system_prompt,
                                           response_model, temp, tokens)
    except Exception as primary_err:
        fallback = config.GEMINI_FALLBACK_MODEL
        if not fallback or fallback == config.GEMINI_MODEL:
            raise
        logger.warning(
            f"Primary Gemini model '{config.GEMINI_MODEL}' failed structured call "
            f"({primary_err}); falling back to '{fallback}'"
        )
        return _generate_gemini_structured(fallback, prompt, system_prompt,
                                           response_model, temp, tokens)


# ═══════════════════════════════════════════════════════════
# GEMINI VISION API (for PDF QA)
# ═══════════════════════════════════════════════════════════

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def call_gemini_vision_api(
    prompt: str,
    system_prompt: str,
    image_data: bytes,
    temperature: Optional[float] = None
) -> str:
    """
    Call Gemini Vision API for image analysis (using new google.genai package)

    Args:
        prompt: User message
        system_prompt: System instruction
        image_data: Image bytes (PNG/JPEG)
        temperature: Override default temperature

    Returns:
        Generated analysis text

    Raises:
        Exception: If API call fails after retries
    """
    if not gemini_client:
        raise ValueError("Google API key not configured")

    temp = temperature if temperature is not None else config.GEMINI_TEMPERATURE

    logger.debug(f"Calling Gemini Vision API (temp={temp})")

    try:
        # Create image part from bytes
        import PIL.Image
        import io
        image = PIL.Image.open(io.BytesIO(image_data))

        # Convert PIL Image to bytes for new API
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()

        # Use new API with multimodal input
        response = gemini_client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=[
                types.Part.from_bytes(data=img_byte_arr, mime_type="image/png"),
                prompt
            ],
            config=types.GenerateContentConfig(
                temperature=temp,
                system_instruction=system_prompt
            )
        )

        text = response.text
        logger.debug(f"Gemini Vision response: {len(text)} chars")
        return text

    except Exception as e:
        logger.error(f"Gemini Vision API error: {e}")
        raise


# ═══════════════════════════════════════════════════════════
# ASYNC WRAPPERS (for parallel drafting)
# ═══════════════════════════════════════════════════════════

import asyncio

async def call_claude_async(prompt: str, system_prompt: str) -> str:
    """Async wrapper for Claude API"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, call_claude_api, prompt, system_prompt)


async def call_gemini_async(prompt: str, system_prompt: str) -> str:
    """Async wrapper for Gemini API"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, call_gemini_api, prompt, system_prompt)
