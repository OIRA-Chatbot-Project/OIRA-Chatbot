from __future__ import annotations

class UnitOfWork:
    """Transaction boundary for multi-repository operations."""

    def begin(self) -> None:
        raise NotImplementedError("TODO: implement UnitOfWork.begin")

    def commit(self) -> None:
        raise NotImplementedError("TODO: implement UnitOfWork.commit")

    def rollback(self) -> None:
        raise NotImplementedError("TODO: implement UnitOfWork.rollback")

    def __enter__(self) -> "UnitOfWork":
        self.begin()
        return self

    def __exit__(self, exc_type, exc, exc_tb) -> None:
        if exc is None:
            self.commit()
            return
        self.rollback()

class NoOpUnitOfWork(UnitOfWork):
    """Default in-memory UoW used until a concrete DB transaction is wired."""

    def begin(self) -> None:
        return

    def commit(self) -> None:
        return

    def rollback(self) -> None:
        return