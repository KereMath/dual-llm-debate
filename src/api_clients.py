"""
API Client Wrappers
Unified interface for Claude (Anthropic) and Gemini (Google) APIs
"""

import logging
from typing import Optional
from anthropic import Anthropic
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import config

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# INITIALIZE CLIENTS
# ═══════════════════════════════════════════════════════════

# Anthropic Claude
anthropic_client = Anthropic(api_key=config.ANTHROPIC_API_KEY) if config.ANTHROPIC_API_KEY else None

# Google Gemini
if config.GOOGLE_API_KEY:
    genai.configure(api_key=config.GOOGLE_API_KEY)


# ═══════════════════════════════════════════════════════════
# CLAUDE API WRAPPER
# ═══════════════════════════════════════════════════════════

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def call_claude_api(
    prompt: str,
    system_prompt: str,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> str:
    """
    Call Claude API with retry logic

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
        logger.error(f"Claude API error: {e}")
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
    Call Gemini API with retry logic

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
    if not config.GOOGLE_API_KEY:
        raise ValueError("Google API key not configured")

    temp = temperature if temperature is not None else config.GEMINI_TEMPERATURE
    tokens = max_tokens if max_tokens is not None else config.GEMINI_MAX_TOKENS

    logger.debug(f"Calling Gemini API (temp={temp}, max_tokens={tokens})")

    try:
        model = genai.GenerativeModel(
            model_name=config.GEMINI_MODEL,
            generation_config={
                "temperature": temp,
                "max_output_tokens": tokens,
            }
        )

        # Combine system prompt and user prompt for older API versions
        full_prompt = f"System: {system_prompt}\n\nUser: {prompt}"
        response = model.generate_content(full_prompt)
        text = response.text
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
    Call Gemini Vision API for image analysis

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
    if not config.GOOGLE_API_KEY:
        raise ValueError("Google API key not configured")

    temp = temperature if temperature is not None else config.GEMINI_TEMPERATURE

    logger.debug(f"Calling Gemini Vision API (temp={temp})")

    try:
        # Create image part
        import PIL.Image
        import io
        image = PIL.Image.open(io.BytesIO(image_data))

        model = genai.GenerativeModel(
            model_name=config.GEMINI_MODEL,
            generation_config={"temperature": temp}
        )

        # Combine system prompt with user prompt
        full_prompt = f"System: {system_prompt}\n\nUser: {prompt}"
        response = model.generate_content([full_prompt, image])
        text = response.text
        logger.debug(f"Gemini Vision response: {len(text)} chars")
        return text

    except Exception as e:
        logger.error(f"Gemini Vision API error: {e}")
        raise


# ═══════════════════════════════════════════════════════════
# HELPER: Semantic Similarity via Claude
# ═══════════════════════════════════════════════════════════

def calculate_semantic_similarity(text_a: str, text_b: str) -> float:
    """
    Use Claude to calculate semantic similarity between two texts

    Args:
        text_a: First text
        text_b: Second text

    Returns:
        Similarity score (0.0 to 1.0)
    """
    # Quick filters
    if text_a.strip() == text_b.strip():
        return 1.0
    if not text_a.strip() or not text_b.strip():
        return 0.0

    prompt = f"""İki araştırma taslağını semantik (anlamsal) benzerlik açısından karşılaştır.

METIN A:
{text_a}

METIN B:
{text_b}

Karşılaştırma Kriterleri:
1. Faktüel Uyum (50%): Aynı gerçekleri mi söylüyorlar?
2. Mantıksal Tutarlılık (30%): Çelişki var mı?
3. Kanıt Gücü (20%): Her ikisi de kaynak kullanıyor mu?

IGNORE (Önemseme):
- Kelime seçimi farkları ("kurdu" vs "kuruldu")
- Cümle yapısı
- Yazım stili
- Sunum sırası

FOCUS (Odaklan):
- Semantik anlam (aynı gerçekler mi?)
- Mantıksal eşdeğerlik
- Faktüel örtüşme yüzdesi

SADECE 0-100 arası bir sayı ver (benzerlik yüzdesi):"""

    try:
        response = call_claude_api(
            prompt=prompt,
            system_prompt="You are a semantic similarity analyzer. Output only a number.",
            temperature=0.0,
            max_tokens=10
        )

        # Parse number
        import re
        match = re.search(r'\b(\d+)\b', response)

        if match:
            percentage = int(match.group(1))
            percentage = max(0, min(100, percentage))
            return percentage / 100.0
        else:
            logger.warning(f"Could not parse similarity: {response}")
            return 0.5

    except Exception as e:
        logger.error(f"Similarity calculation failed: {e}")
        return 0.5


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
