"""
Configuration Management
Loads environment variables and provides centralized settings
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from typing import Literal

# Load .env file
load_dotenv()

class Config(BaseSettings):
    """
    Application configuration
    All settings loaded from environment variables
    """

    # ═══════════════════════════════════════════════════════════
    # API KEYS (Required)
    # ═══════════════════════════════════════════════════════════

    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")

    # ═══════════════════════════════════════════════════════════
    # MODEL CONFIGURATION
    # ═══════════════════════════════════════════════════════════

    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5-20250929")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-pro-latest")

    # Temperature settings
    GEMINI_TEMPERATURE: float = 0.7  # Higher creativity (Explorer)
    CLAUDE_TEMPERATURE: float = 0.5  # Higher precision (Judge)
    SYNTHESIZER_TEMPERATURE: float = 0.2  # Minimal creativity (Hakem)

    # Token limits
    CLAUDE_MAX_TOKENS: int = 4096
    GEMINI_MAX_TOKENS: int = 8192

    # ═══════════════════════════════════════════════════════════
    # DEBATE CONFIGURATION
    # ═══════════════════════════════════════════════════════════

    MAX_ROUNDS: int = int(os.getenv("MAX_ROUNDS", "3"))
    CONVERGENCE_THRESHOLD: float = float(os.getenv("CONVERGENCE_THRESHOLD", "0.95"))

    # ═══════════════════════════════════════════════════════════
    # RESEARCH MODE
    # ═══════════════════════════════════════════════════════════

    DEFAULT_RESEARCH_MODE: Literal["offline", "internet", "auto"] = os.getenv(
        "DEFAULT_RESEARCH_MODE", "auto"
    )

    # Auto mode keywords (for decision making)
    TIME_SENSITIVE_KEYWORDS: list[str] = [
        "news", "price", "current", "latest", "bugün", "fiyat",
        "haber", "2024", "2025", "2026", "güncel", "recent", "today"
    ]

    # ═══════════════════════════════════════════════════════════
    # TAVILY SEARCH SETTINGS
    # ═══════════════════════════════════════════════════════════

    TAVILY_SEARCH_DEPTH: str = "advanced"
    TAVILY_MAX_RESULTS: int = 5
    TAVILY_INCLUDE_DOMAINS: list[str] = []  # Empty = all
    TAVILY_EXCLUDE_DOMAINS: list[str] = ["pinterest.com", "quora.com"]

    # ═══════════════════════════════════════════════════════════
    # PDF & LATEX CONFIGURATION
    # ═══════════════════════════════════════════════════════════

    QA_THRESHOLD: int = int(os.getenv("QA_THRESHOLD", "75"))
    LATEX_TIMEOUT: int = int(os.getenv("LATEX_TIMEOUT", "30"))
    MAX_LATEX_RETRIES: int = int(os.getenv("MAX_LATEX_RETRIES", "3"))
    MAX_PDF_REGENERATIONS: int = int(os.getenv("MAX_PDF_REGENERATIONS", "2"))

    # ═══════════════════════════════════════════════════════════
    # OUTPUT PATHS
    # ═══════════════════════════════════════════════════════════

    OUTPUT_DIR: Path = Path(os.getenv("OUTPUT_DIR", "./output"))
    PDF_DIR: Path = Path(os.getenv("PDF_DIR", "./output/pdfs"))
    LATEX_DIR: Path = Path(os.getenv("LATEX_DIR", "./output/latex"))
    LOG_DIR: Path = Path(os.getenv("LOG_DIR", "./output/logs"))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create output directories if they don't exist
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.PDF_DIR.mkdir(parents=True, exist_ok=True)
        self.LATEX_DIR.mkdir(parents=True, exist_ok=True)
        self.LOG_DIR.mkdir(parents=True, exist_ok=True)

    # ═══════════════════════════════════════════════════════════
    # VALIDATION
    # ═══════════════════════════════════════════════════════════

    def validate_api_keys(self, mode: str = "auto") -> list[str]:
        """
        Validate required API keys based on mode

        Args:
            mode: Research mode (offline/internet/auto)

        Returns:
            List of missing keys
        """
        missing = []

        # Claude & Gemini always required
        if not self.ANTHROPIC_API_KEY:
            missing.append("ANTHROPIC_API_KEY")
        if not self.GOOGLE_API_KEY:
            missing.append("GOOGLE_API_KEY")

        # Tavily only required for internet mode
        if mode in ["internet", "auto"] and not self.TAVILY_API_KEY:
            missing.append("TAVILY_API_KEY (required for internet/auto mode)")

        return missing

    model_config = {"env_file": ".env", "case_sensitive": True, "extra": "ignore"}


# ═══════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════

config = Config()


# ═══════════════════════════════════════════════════════════
# VALIDATION ON IMPORT
# ═══════════════════════════════════════════════════════════

def validate_config():
    """Validate configuration on module import"""
    missing = config.validate_api_keys(mode=config.DEFAULT_RESEARCH_MODE)
    if missing:
        print("[!] WARNING: Missing API keys:")
        for key in missing:
            print(f"   - {key}")
        print("\nCreate a .env file with required keys (see .env.example)")
    else:
        print("[OK] Configuration validated successfully")


# Auto-validate when imported (but don't crash)
if __name__ != "__main__":
    try:
        validate_config()
    except Exception as e:
        print(f"[!] Config validation warning: {e}")
