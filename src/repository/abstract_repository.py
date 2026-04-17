from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

EntityT = TypeVar("EntityT")
IdT = TypeVar("IdT")

class BaseRepository(ABC, Generic[EntityT, IdT]):
    """Base CRUD contract for repositories in the data layer."""

    @abstractmethod
    def create(self, entity: EntityT) -> EntityT:
        """Persist a new entity and return the stored result."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, entity_id: IdT) -> EntityT | None:
        """Retrieve one entity by identifier."""
        raise NotImplementedError

    @abstractmethod
    def update(self, entity: EntityT) -> EntityT:
        """Persist updates to an existing entity."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, entity_id: IdT) -> None:
        """Delete one entity by identifier."""
        raise NotImplementedError

    @abstractmethod
    def list(self, limit: int = 100, offset: int = 0) -> list[EntityT]:
        """Return a paginated list of entities."""
        raise NotImplementedError