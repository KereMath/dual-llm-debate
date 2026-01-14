"""
Callback system for real-time progress tracking
"""

from typing import Callable, Optional
from dataclasses import dataclass


@dataclass
class ProgressUpdate:
    """Progress update message"""
    phase: str
    status: str  # "running", "completed", "error"
    progress: float  # 0.0 to 1.0
    message: str
    details: Optional[dict] = None


class ProgressCallback:
    """
    Global callback for progress updates
    Used to stream progress to UI
    """

    def __init__(self):
        self.callback: Optional[Callable[[ProgressUpdate], None]] = None

    def set_callback(self, callback: Callable[[ProgressUpdate], None]):
        """Set the callback function"""
        self.callback = callback

    def clear_callback(self):
        """Clear the callback"""
        self.callback = None

    def update(self, phase: str, status: str, progress: float, message: str, details: dict = None):
        """Send progress update"""
        if self.callback:
            update = ProgressUpdate(
                phase=phase,
                status=status,
                progress=progress,
                message=message,
                details=details or {}
            )
            self.callback(update)


# Global singleton
progress_callback = ProgressCallback()
