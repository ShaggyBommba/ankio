from __future__ import annotations

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from infrastructure.config import DatabaseSettings


class Base(DeclarativeBase):
    """Infrastructure foundation that our Shared Kernel models inherit from."""


class SqlDatabase:
    """SQLAlchemy database factory for engines, sessions, and schema setup."""

    def __init__(self, settings: DatabaseSettings) -> None:
        """Keep database settings and lazily create SQLAlchemy objects."""
        self.settings = settings
        self._engine: Engine | None = None
        self._sessions: sessionmaker[Session] | None = None

    def engine(self) -> Engine:
        """Return the shared engine, applying driver-specific options."""
        if self._engine is None:
            self._engine = create_engine(self.settings.dsn)
        return self._engine

    def sessions(self) -> sessionmaker[Session]:
        """Return the session factory used by repositories and units of work."""
        if self._sessions is None:
            self._sessions = sessionmaker(bind=self.engine())
        return self._sessions

    def create_all(self) -> None:
        """Provision extensions and create all known database tables."""
        import infrastructure.persistence.models  # noqa: F401
        Base.metadata.create_all(self.engine())

    def drop_all(self) -> None:
        """Drop all known database tables."""
        import infrastructure.persistence.models  # noqa: F401

        Base.metadata.drop_all(self.engine())

    def close(self) -> None:
        """Dispose the engine and session factory."""
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None
            self._sessions = None
