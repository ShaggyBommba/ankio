from __future__ import annotations

import asyncio
from functools import lru_cache
from logging import getLogger

from infrastructure.config import Settings, get_settings
from infrastructure.observability.logger import LoggingService


logger = getLogger(__name__)


class App:
    """Application facade used by entrypoints."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def name(self) -> str:
        return self.settings.name

    @property
    def version(self) -> str:
        return self.settings.version

    @property
    def healthy(self) -> bool:
        return True

    def start(self) -> None:
        """Start the application."""
        logger.info(f"Starting {self.name} v{self.version}...")

    def close(self) -> None:
        """Close the application."""
        logger.info(f"Closing {self.name}...")

@lru_cache(maxsize=1)
def get_app() -> App:
    """Build the application from concrete infrastructure adapters."""
    settings = get_settings()
    LoggingService.setup(settings.logging)
    return App(settings=settings)
