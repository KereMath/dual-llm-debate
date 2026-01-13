"""
PDF Compiler
Compile LaTeX source to PDF (with retry logic)
"""

import logging
import subprocess
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from ..schemas import DebateState
from ..config import config

logger = logging.getLogger(__name__)


def pdf_compilation_node(state: DebateState) -> DebateState:
    """
    Compile LaTeX source to PDF

    Input: state.latex_code
    Output: state.pdf_path
    """

    logger.info("PDF Compilation: Compiling LaTeX to PDF")

    if not state.latex_code:
        logger.error("No LaTeX code available")
        state.add_error("PDF compilation: No LaTeX code")
        return state

    # Retry logic
    max_retries = config.MAX_LATEX_RETRIES
    for attempt in range(max_retries):
        try:
            pdf_path = compile_latex_to_pdf(state.latex_code)
            state.pdf_path = str(pdf_path)
            state.latex_retry_count = attempt
            logger.info(f"✅ PDF compiled successfully: {pdf_path}")
            return state

        except Exception as e:
            logger.warning(f"Compilation attempt {attempt + 1}/{max_retries} failed: {e}")
            state.latex_retry_count = attempt + 1

            if attempt == max_retries - 1:
                # Final failure
                logger.error(f"PDF compilation failed after {max_retries} attempts")
                state.add_error(f"PDF compilation failed: {str(e)}")
                return state

    return state


def compile_latex_to_pdf(latex_code: str) -> Path:
    """
    Compile LaTeX to PDF using pdflatex

    Args:
        latex_code: Full LaTeX source

    Returns:
        Path to compiled PDF

    Raises:
        Exception: If compilation fails
    """

    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Write LaTeX file
        tex_file = temp_path / "document.tex"
        tex_file.write_text(latex_code, encoding='utf-8')

        # Compile with pdflatex (twice for references)
        for run in range(2):
            try:
                result = subprocess.run(
                    ["pdflatex", "-interaction=nonstopmode", "document.tex"],
                    cwd=temp_path,
                    capture_output=True,
                    text=True,
                    timeout=config.LATEX_TIMEOUT
                )

                if result.returncode != 0:
                    logger.error(f"pdflatex error (run {run + 1}):\n{result.stdout}\n{result.stderr}")
                    if run == 1:  # Only raise on second run
                        raise Exception(f"pdflatex failed: {result.stderr}")

            except subprocess.TimeoutExpired:
                raise Exception(f"pdflatex timeout after {config.LATEX_TIMEOUT}s")

            except FileNotFoundError:
                raise Exception("pdflatex not found. Please install TeX Live or MiKTeX.")

        # Check if PDF was created
        pdf_file = temp_path / "document.pdf"
        if not pdf_file.exists():
            raise Exception("PDF file not generated")

        # Move to output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"research_{timestamp}.pdf"
        output_path = config.PDF_DIR / output_filename

        shutil.copy(pdf_file, output_path)

        return output_path
