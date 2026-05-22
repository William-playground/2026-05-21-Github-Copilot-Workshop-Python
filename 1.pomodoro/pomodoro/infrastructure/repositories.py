"""Repository protocols decouple the application layer from storage details.

Concrete implementations live in `repositories_sqlite.py` (production) and a
purely in-memory Fake is provided in `repositories_memory.py` for unit testing.
"""

from __future__ import annotations

from datetime import date
from typing import Protocol

from ..domain.entities import Session, Settings


class SessionRepository(Protocol):
    def add(self, session: Session) -> Session:
        ...

    def list_for_date(self, day: date) -> list[Session]:
        ...


class SettingsRepository(Protocol):
    def get(self) -> Settings:
        ...

    def update(self, settings: Settings) -> Settings:
        ...
