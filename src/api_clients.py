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
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    reraise=True,
    retry=retry_if_exception_type((Exception,))
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
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def call_gemini_api(
    prompt: str,
    system_prompt: str,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> str:
    """
    Call Gemini API with retry logic (using new google.genai package)

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
    if not gemini_client:
        raise ValueError("Google API key not configured")

    temp = temperature if temperature is not None else config.GEMINI_TEMPERATURE
    tokens = max_tokens if max_tokens is not None else config.GEMINI_MAX_TOKENS

    logger.debug(f"Calling Gemini API (temp={temp}, max_tokens={tokens})")

    try:
        # Use new API with system instruction support
        # Note: Gemini 2.5 Pro may use thinking tokens internally
        # ✅ Google Search Grounding enabled
        response = gemini_client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temp,
                max_output_tokens=tokens,
                system_instruction=system_prompt,
                tools=[types.Tool(google_search=types.GoogleSearch())]
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
        logger.error(f"Gemini API error: {e}")
        raise


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
