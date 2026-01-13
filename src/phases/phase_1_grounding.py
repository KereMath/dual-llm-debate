"""
Phase 1: Grounding (Veri Çapalama)
V1 Mode: Offline (no search)
V2 Mode: Tavily search (advanced)
Auto Mode: Keyword-based decision
"""

import logging
from datetime import datetime
from typing import Literal

from ..schemas import DebateState, WebContext, Source
from ..config import config

logger = logging.getLogger(__name__)


def phase_1_grounding(state: DebateState) -> DebateState:
    """
    Faz 1: Grounding (Mode-Aware)

    LOGIC:
    1. Offline (V1) → No search, use internal knowledge
    2. Internet (V2) → TAVILY search (NOT DuckDuckGo)
    3. Auto → Keyword-based decision

    Input: state.topic + state.research_mode
    Process: Mode'a göre Tavily veya internal knowledge
    Output: state.shared_context (Değişmez Gerçek)
    """

    current_mode = state.research_mode

    # ═══════════════════════════════════════════════════════
    # AUTO MODE: Keyword-based decision
    # ═══════════════════════════════════════════════════════

    if current_mode == "auto":
        time_sensitive_keywords = config.TIME_SENSITIVE_KEYWORDS

        if any(k in state.topic.lower() for k in time_sensitive_keywords):
            current_mode = "internet"
            logger.info("🤖 Auto Mode → Internet (time-sensitive keywords detected)")
        else:
            current_mode = "offline"
            logger.info("🤖 Auto Mode → Offline (no time-sensitive keywords)")

    # ═══════════════════════════════════════════════════════
    # V1: OFFLINE MODE (No Search)
    # ═══════════════════════════════════════════════════════

    if current_mode == "offline":
        logger.info("⚡ V1 Mode: OFFLINE - Using Internal Knowledge Only")

        state.shared_context = f"""ARAŞTIRMA MODU: OFFLINE (V1 - Internal Knowledge)

Kullanıcı internet araması istemedi.

GÖREVİN:
- SADECE kendi iç bilgi birikimini kullan (training data)
- Güncel olmayan veri kullanabileceğini kullanıcıya BELİRT
- Kaynak olarak "Internal Knowledge" veya "Training Data (pre-{datetime.now().year})" yaz

UYARI:
Bu modda güncel fiyat, haber veya real-time bilgi SAĞLANAMAZ.
"""

        return state

    # ═══════════════════════════════════════════════════════
    # V2: INTERNET MODE (TAVILY FORCED)
    # ═══════════════════════════════════════════════════════

    logger.info(f"🌐 V2 Mode: INTERNET - Searching TAVILY for: {state.topic}")

    try:
        # Import Tavily
        from tavily import TavilyClient

        # Initialize TAVILY (NOT DuckDuckGo!)
        if not config.TAVILY_API_KEY:
            raise ValueError("Tavily API key not configured")

        tavily = TavilyClient(api_key=config.TAVILY_API_KEY)

        # Execute search
        logger.info("Querying Tavily API...")

        search_params = {
            "query": state.topic,
            "search_depth": config.TAVILY_SEARCH_DEPTH,
            "max_results": config.TAVILY_MAX_RESULTS,
        }

        # Add domain filters if specified
        if config.TAVILY_INCLUDE_DOMAINS:
            search_params["include_domains"] = config.TAVILY_INCLUDE_DOMAINS
        if config.TAVILY_EXCLUDE_DOMAINS:
            search_params["exclude_domains"] = config.TAVILY_EXCLUDE_DOMAINS

        response = tavily.search(**search_params)

        # Validate response
        if not response or 'results' not in response:
            raise ValueError("Tavily returned empty response")

        results = response.get('results', [])
        if len(results) == 0:
            raise ValueError("No sources found")

        # Parse sources
        sources = []
        context_parts = []

        for idx, result in enumerate(results, 1):
            content = result.get('content', '')
            url = result.get('url', '')
            title = result.get('title', f'Source {idx}')
            score = result.get('score', 1.0)

            sources.append(Source(
                url=url,
                title=title,
                content=content,
                relevance_score=score
            ))

            context_parts.append(
                f"\n{'='*60}\n"
                f"SOURCE {idx}: {title}\n"
                f"URL: {url}\n"
                f"RELEVANCE: {score:.2f}\n"
                f"{'='*60}\n"
                f"{content}\n"
            )

        # Update state
        state.web_context = WebContext(
            sources=sources,
            combined_text="".join(context_parts),
            search_query=state.topic,
            total_sources=len(sources)
        )

        state.shared_context = state.web_context.combined_text

        logger.info(f"✅ Tavily search complete: {len(sources)} sources")

        return state

    except Exception as e:
        logger.error(f"Tavily search failed: {e}")
        state.add_error(f"Tavily error: {str(e)}")

        # FALLBACK: Use offline mode
        logger.warning("Falling back to offline mode")
        state.shared_context = f"""[FALLBACK - Tavily API Error]

Tavily araması başarısız: {str(e)}

Internal knowledge kullanılıyor (offline mode fallback).
"""

        return state
