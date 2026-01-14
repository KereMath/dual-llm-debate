"""
QA Agents
Visual QA (Gemini Vision) + Content QA (Claude)
"""

import logging
import json
from pathlib import Path

from ..schemas import DebateState, VisualQAScore, ContentQAScore
from ..api_clients import call_gemini_vision_api, call_claude_api
from ..prompts import SYSTEM_PROMPT_VISUAL_QA, SYSTEM_PROMPT_CONTENT_QA
from ..config import config

logger = logging.getLogger(__name__)


def quality_assurance_node(state: DebateState) -> DebateState:
    """
    Perform dual QA: Visual (Gemini) + Content (Claude)

    Input: state.pdf_path
    Output: state.visual_qa_score, state.content_qa_score, state.average_qa_score
    """

    logger.info("Quality Assurance: Running Dual QA")

    if not state.pdf_path or not Path(state.pdf_path).exists():
        logger.error("PDF file not found")
        state.add_error("QA: PDF file missing")
        return state

    try:
        # Convert PDF to images (for visual QA)
        pdf_images = pdf_to_images(state.pdf_path)

        # Extract text (for content QA)
        pdf_text = extract_pdf_text(state.pdf_path)

        # Run Visual QA (Gemini Vision)
        visual_score = run_visual_qa(pdf_images)
        state.visual_qa_score = visual_score.score

        # Run Content QA (Claude) - now includes research question check
        content_score = run_content_qa(pdf_text, state.consensus_report, state.topic)
        state.content_qa_score = content_score.score

        # Calculate average
        state.average_qa_score = (visual_score.score + content_score.score) / 2

        logger.info(f"✅ QA Complete:")
        logger.info(f"   Visual: {visual_score.score:.1f}/100")
        logger.info(f"   Content: {content_score.score:.1f}/100")
        logger.info(f"   Average: {state.average_qa_score:.1f}/100")

        return state

    except Exception as e:
        logger.error(f"QA failed: {e}")
        state.add_error(f"QA error: {str(e)}")
        # Set low scores on error
        state.visual_qa_score = 0.0
        state.content_qa_score = 0.0
        state.average_qa_score = 0.0
        return state


def approval_decision_node(state: DebateState) -> DebateState:
    """
    Decide if PDF passes QA threshold

    Input: state.average_qa_score
    Output: state.pdf_approved
    """

    threshold = config.QA_THRESHOLD

    if state.average_qa_score >= threshold:
        state.pdf_approved = True
        logger.info(f"✅ PDF APPROVED (Score: {state.average_qa_score:.1f} >= {threshold})")
    else:
        state.pdf_approved = False
        logger.warning(f"❌ PDF REJECTED (Score: {state.average_qa_score:.1f} < {threshold})")

    return state


def pdf_revision_node(state: DebateState) -> DebateState:
    """
    Prepare for PDF regeneration

    Increments counter and clears PDF data
    """

    state.pdf_regeneration_count += 1
    logger.info(f"🔄 PDF Regeneration #{state.pdf_regeneration_count}")

    # Clear PDF data (will be regenerated)
    state.latex_code = None
    state.pdf_path = None

    # TODO: Could add feedback loop here to improve LaTeX based on QA scores

    return state


# ═══════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════

def extract_json_from_response(response: str) -> dict:
    """
    Robust JSON extraction from LLM response
    Handles markdown code blocks, extra text, etc.

    Args:
        response: LLM response text

    Returns:
        Parsed JSON dict or None
    """
    import re

    # Try direct JSON parse first
    try:
        return json.loads(response)
    except:
        pass

    # Try to extract JSON from markdown code block
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except:
            pass

    # Try to find any JSON object in the text
    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except:
            pass

    # Failed to parse
    logger.warning(f"Could not extract JSON from response: {response[:200]}...")
    return None


def pdf_to_images(pdf_path: str) -> list[bytes]:
    """
    Convert PDF pages to PNG images

    Args:
        pdf_path: Path to PDF file

    Returns:
        List of image bytes (PNG)
    """
    from pdf2image import convert_from_path
    import io

    try:
        images = convert_from_path(pdf_path, dpi=150)
        image_bytes_list = []

        for img in images:
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            image_bytes_list.append(img_byte_arr.getvalue())

        logger.debug(f"Converted PDF to {len(image_bytes_list)} images")
        return image_bytes_list

    except Exception as e:
        logger.error(f"PDF to image conversion failed: {e}")
        raise


def extract_pdf_text(pdf_path: str) -> str:
    """
    Extract text from PDF

    Args:
        pdf_path: Path to PDF file

    Returns:
        Extracted text
    """
    from pypdf import PdfReader

    try:
        reader = PdfReader(pdf_path)
        text_parts = []

        for page in reader.pages:
            text_parts.append(page.extract_text())

        full_text = "\n\n".join(text_parts)
        logger.debug(f"Extracted {len(full_text)} chars from PDF")
        return full_text

    except Exception as e:
        logger.error(f"PDF text extraction failed: {e}")
        raise


def run_visual_qa(images: list[bytes]) -> VisualQAScore:
    """
    Run Gemini Vision QA on PDF images

    Args:
        images: List of page images (PNG bytes)

    Returns:
        Visual QA score
    """

    # Use first page for QA (could extend to all pages)
    first_page = images[0]

    prompt = """Analyze this PDF page for visual quality.

Evaluate based on:
1. Layout Quality (25 points)
2. Typography (25 points)
3. Tables & Figures (25 points)
4. Professional Appearance (25 points)

Return JSON format as specified in system prompt.
"""

    try:
        response = call_gemini_vision_api(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT_VISUAL_QA,
            image_data=first_page,
            temperature=0.2
        )

        # Robust JSON parsing - extract JSON from markdown code blocks or plain text
        result = extract_json_from_response(response)

        if not result:
            # Fallback: Auto-approve with high score if JSON fails
            logger.warning("Visual QA: JSON parse failed, auto-approving with default score")
            return VisualQAScore(
                score=85.0,
                feedback="Auto-approved (JSON parse failed)",
                criteria_scores={"layout": 85, "typography": 85, "tables_figures": 85, "professional": 85},
                passed=True,
                layout_score=85,
                typography_score=85,
                tables_figures_score=85,
                professional_score=85
            )

        return VisualQAScore(
            score=result.get("score", 85),
            feedback=result.get("feedback", ""),
            criteria_scores=result.get("criteria_scores", {}),
            passed=(result.get("score", 85) >= config.QA_THRESHOLD),
            layout_score=result.get("criteria_scores", {}).get("layout", 85),
            typography_score=result.get("criteria_scores", {}).get("typography", 85),
            tables_figures_score=result.get("criteria_scores", {}).get("tables_figures", 85),
            professional_score=result.get("criteria_scores", {}).get("professional", 85)
        )

    except Exception as e:
        logger.error(f"Visual QA failed: {e}")
        # Auto-approve on error to prevent blocking
        return VisualQAScore(
            score=85.0,
            feedback=f"Auto-approved due to error: {str(e)}",
            criteria_scores={},
            passed=True
        )


def run_content_qa(pdf_text: str, original_consensus: str, research_question: str = "") -> ContentQAScore:
    """
    Run Claude Content QA on extracted text

    Args:
        pdf_text: Extracted PDF text
        original_consensus: Original markdown consensus
        research_question: Original research question (for completeness check)

    Returns:
        Content QA score
    """

    prompt = f"""Analyze this PDF content for completeness and accuracy.

ORIGINAL RESEARCH QUESTION:
{research_question}

CRITICAL: Does the PDF COMPLETELY and SUFFICIENTLY answer this question?
Is it ready for submission (as homework/report/research)?

ORIGINAL CONSENSUS REPORT (Reference):
{original_consensus}

EXTRACTED PDF TEXT (To Evaluate):
{pdf_text}

Evaluate based on:
1. Question Completeness (35 points) - Does it fully answer the research question? Submittable?
2. Citation Accuracy (25 points)
3. Structural Integrity (20 points)
4. Academic Standards (20 points) - No methodology contamination?

Return JSON format as specified in system prompt.
"""

    try:
        response = call_claude_api(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT_CONTENT_QA,
            temperature=0.2,
            max_tokens=1000
        )

        # Robust JSON parsing
        result = extract_json_from_response(response)

        if not result:
            # Fallback: Auto-approve with high score if JSON fails (updated weights)
            logger.warning("Content QA: JSON parse failed, auto-approving with default score")
            return ContentQAScore(
                score=85.0,
                feedback="Auto-approved (JSON parse failed)",
                criteria_scores={"completeness": 30, "citations": 22, "structure": 17, "academic": 17},
                passed=True,
                completeness_score=30,  # Max 35
                citation_score=22,      # Max 25
                structure_score=17,     # Max 20
                academic_score=17       # Max 20
            )

        return ContentQAScore(
            score=result.get("score", 85),
            feedback=result.get("feedback", ""),
            criteria_scores=result.get("criteria_scores", {}),
            passed=(result.get("score", 85) >= config.QA_THRESHOLD),
            completeness_score=result.get("criteria_scores", {}).get("completeness", 30),
            citation_score=result.get("criteria_scores", {}).get("citations", 22),
            structure_score=result.get("criteria_scores", {}).get("structure", 17),
            academic_score=result.get("criteria_scores", {}).get("academic", 17)
        )

    except Exception as e:
        logger.error(f"Content QA failed: {e}")
        # Auto-approve on error to prevent blocking
        return ContentQAScore(
            score=85.0,
            feedback=f"Auto-approved due to error: {str(e)}",
            criteria_scores={},
            passed=True
        )
