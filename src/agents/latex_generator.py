"""
LaTeX Generator
Convert markdown consensus report to publication-ready LaTeX
"""

import logging
import re
from datetime import datetime

from ..schemas import DebateState
from ..api_clients import call_claude_api
from ..prompts import SYSTEM_PROMPT_LATEX_GENERATOR

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# CITATION HANDLING FOR OFFLINE MODE
# ═══════════════════════════════════════════════════════════

def strip_citations(latex: str) -> str:
    r"""
    Remove all citation commands and reference numbers from LaTeX

    Removes:
    - \citep{key}, \cite{key}, \citet{key}
    - [1], [2], [3] style inline citation numbers
    - \bibliography{...}
    - \begin{thebibliography}...\end{thebibliography}
    - Bibliography/References sections
    """

    # Remove \citep{...}, \cite{...}, \citet{...}
    latex = re.sub(r'\\cite[pt]?\{[^}]+\}', '', latex)

    # Remove inline citation numbers: [1], [2], [1,2,3], [1-3]
    # Match [number] or [number,number] or [number-number]
    latex = re.sub(r'\[\d+(?:[-,]\d+)*\]', '', latex)

    # Remove \bibliography{...}
    latex = re.sub(r'\\bibliography\{[^}]+\}', '', latex)

    # Remove \begin{thebibliography}...\end{thebibliography}
    latex = re.sub(
        r'\\begin\{thebibliography\}.*?\\end\{thebibliography\}',
        '',
        latex,
        flags=re.DOTALL
    )

    # Remove References/Bibliography sections entirely
    # Match: \section{References} or \section{Bibliography} until next \section or end
    latex = re.sub(
        r'\\section\{(?:References|Bibliography)\}.*?(?=\\section|\\end\{document\}|$)',
        '',
        latex,
        flags=re.DOTALL | re.IGNORECASE
    )

    # Remove natbib package
    latex = re.sub(r'\\usepackage\{natbib\}', '', latex)

    # Clean up extra blank lines (more than 2 consecutive newlines)
    latex = re.sub(r'\n{3,}', '\n\n', latex)

    return latex


def get_latex_system_prompt(research_mode: str) -> str:
    """
    Get appropriate system prompt based on research mode

    NOTE: Citations are ALWAYS stripped now per user request
    """

    # User request: NO citations in any mode
    return SYSTEM_PROMPT_LATEX_GENERATOR + """

CRITICAL - TURKISH SUPPORT:
⚠️ ALWAYS include these packages at the top:
   \\usepackage[utf8]{{inputenc}}
   \\usepackage[T1]{{fontenc}}
   \\usepackage[turkish]{{babel}}
⚠️ Turkish characters (ı, ş, ğ, ü, ö, ç, İ, Ş, Ğ, Ü, Ö, Ç) should be written naturally - DO NOT escape them!
⚠️ DO NOT use ASCII escapes like \\i, \\c{c}, etc. - just use UTF-8 directly

CRITICAL - NO CITATIONS MODE:
⚠️ DO NOT use \\citep{} or \\cite{} commands
⚠️ DO NOT include [1], [2], [3] style reference numbers
⚠️ DO NOT include \\begin{thebibliography} or \\bibliography{}
⚠️ DO NOT include References or Bibliography sections
⚠️ DO NOT use natbib package
⚠️ Write content as plain academic text without any citation markers
⚠️ Present facts directly without reference numbers
⚠️ The document should be a clean, self-contained academic text
"""


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
- CRITICAL: Turkish support için MUTLAKA bu paketleri ekle:
  \\usepackage[utf8]{{inputenc}}
  \\usepackage[T1]{{fontenc}}
  \\usepackage[turkish]{{babel}}
- Diğer paketler: geometry, hyperref, amsmath (NO natbib)
- Title: "{state.topic}"
- Author: "Research Consensus Machine (Dual-LLM System)"
- Date: {datetime.now().strftime("%Y-%m-%d")}
- Abstract, Introduction, Findings, Conclusion içermeli
- NO References/Bibliography section
- NO citation commands (\\citep, \\cite, etc.)
- NO citation numbers [1], [2], etc.
- Turkish karakterler (ı, ş, ğ, ü, ö, ç, İ, Ş, Ğ, Ü, Ö, Ç) doğal kullan - ESCAPE ETME!
- Clean, self-contained academic text

SADECE LaTeX kodu döndür (\\documentclass ile başla, \\end{{document}} ile bitir).
Markdown code block YOK, açıklama YOK.
"""

    try:
        # Get appropriate system prompt based on research mode
        system_prompt = get_latex_system_prompt(state.research_mode)

        latex_code = call_claude_api(
            prompt=prompt,
            system_prompt=system_prompt,
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

        # ALWAYS strip citations per user request (all modes)
        logger.info("  Stripping all citations and reference numbers from LaTeX")
        latex_code = strip_citations(latex_code)

        state.latex_code = latex_code

        logger.info(f"✅ LaTeX generation complete ({len(latex_code)} chars)")

        return state

    except Exception as e:
        logger.error(f"LaTeX generation failed: {e}")
        state.add_error(f"LaTeX generation error: {str(e)}")
        return state
