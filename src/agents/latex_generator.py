"""
LaTeX Generator
Convert markdown consensus report to publication-ready LaTeX
"""

import logging
from datetime import datetime

from ..schemas import DebateState
from ..api_clients import call_claude_api
from ..prompts import SYSTEM_PROMPT_LATEX_GENERATOR

logger = logging.getLogger(__name__)


def latex_generation_node(state: DebateState) -> DebateState:
    """
    Convert consensus report (markdown) to LaTeX source

    Input: state.consensus_report
    Output: state.latex_code
    """

    logger.info("LaTeX Generation: Converting consensus to LaTeX")

    if not state.consensus_report:
        logger.error("No consensus report available")
        state.add_error("LaTeX generation: No consensus report")
        return state

    prompt = f"""Aşağıdaki konsensus raporunu akademik LaTeX dökümanına çevir.

KONSENSUS RAPORU (Markdown):
{state.consensus_report}

GEREKSINIMLER:
- \\documentclass[11pt,a4paper]{{article}} ile başla
- Minimal paketler kullan (geometry, hyperref, amsmath, natbib)
- Title: "{state.topic}"
- Author: "Research Consensus Machine (Dual-LLM System)"
- Date: {datetime.now().strftime("%Y-%m-%d")}
- Abstract, Introduction, Methodology, Findings, Disputed Claims, Conclusion, Bibliography içermeli
- Tüm [Source: ...] referanslarını \\bibitem olarak bibliography'ye ekle
- Özel karakterleri escape et

SADECE LaTeX kodu döndür (\\documentclass ile başla, \\end{{document}} ile bitir).
Markdown code block YOK, açıklama YOK.
"""

    try:
        latex_code = call_claude_api(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT_LATEX_GENERATOR,
            temperature=0.3,
            max_tokens=8000
        )

        # Clean up potential markdown artifacts
        latex_code = latex_code.strip()
        if latex_code.startswith("```latex"):
            latex_code = latex_code[8:]
        if latex_code.startswith("```"):
            latex_code = latex_code[3:]
        if latex_code.endswith("```"):
            latex_code = latex_code[:-3]

        latex_code = latex_code.strip()

        state.latex_code = latex_code

        logger.info(f"✅ LaTeX generation complete ({len(latex_code)} chars)")

        return state

    except Exception as e:
        logger.error(f"LaTeX generation failed: {e}")
        state.add_error(f"LaTeX generation error: {str(e)}")
        return state
