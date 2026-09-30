"""
Run Store
Local, per-machine persistence for completed pipeline runs.

Every finished run is written to OUTPUT_DIR/runs/<timestamp>_<slug>.json by
the pipeline itself (not the UI), so results survive browser refreshes,
closed tabs and restarts. The Streamlit UI lists this directory as its
run history.
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .config import config
from .schemas import DebateState

logger = logging.getLogger(__name__)

RUNS_DIR = config.OUTPUT_DIR / "runs"


def _slugify(text: str, max_len: int = 40) -> str:
    slug = re.sub(r"[^0-9A-Za-z]+", "-", text).strip("-").lower()
    return slug[:max_len] or "run"


def save_run(state: DebateState) -> Optional[Path]:
    """Persist a finished run as JSON. Returns the file path, or None on error."""
    try:
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = RUNS_DIR / f"{stamp}_{_slugify(state.topic)}.json"
        path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
        logger.info(f"Run saved to {path}")
        return path
    except Exception as e:
        # Persistence must never take down a completed run
        logger.error(f"Could not save run: {e}")
        return None


def list_runs() -> List[Path]:
    """All saved runs, newest first."""
    if not RUNS_DIR.exists():
        return []
    return sorted(RUNS_DIR.glob("*.json"), reverse=True)


def load_run(path: Path) -> Optional[DebateState]:
    """Load a saved run; returns None if the file is unreadable or invalid."""
    try:
        return DebateState.model_validate_json(Path(path).read_text(encoding="utf-8"))
    except Exception as e:
        logger.error(f"Could not load run {path}: {e}")
        return None


def run_label(path: Path) -> str:
    """Human-readable label for the history list: 'YYYY-MM-DD HH:MM · topic'."""
    stem = Path(path).stem
    m = re.match(r"(\d{8})_(\d{6})_(.*)", stem)
    if not m:
        return stem
    date, time_, slug = m.groups()
    return (f"{date[:4]}-{date[4:6]}-{date[6:]} {time_[:2]}:{time_[2:4]} · "
            f"{slug.replace('-', ' ')}")
