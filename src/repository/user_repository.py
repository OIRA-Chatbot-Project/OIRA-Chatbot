from __future__ import annotations
from src.repository.abstract_repository import BaseRepository
from src.repository.orm import AcademicRecord, FeedbackRecord, UserRecord

class UserRepository(BaseRepository[UserRecord, str]):
    """Repository for user profiles."""
    def create(self, entity: UserRecord) -> UserRecord:
        raise NotImplementedError("TODO: implement UserRepository.create")

    def get_by_id(self, entity_id: str) -> UserRecord | None:
        raise NotImplementedError("TODO: implement UserRepository.get_by_id")

    def update(self, entity: UserRecord) -> UserRecord:
        raise NotImplementedError("TODO: implement UserRepository.update")

    def delete(self, entity_id: str) -> None:
        raise NotImplementedError("TODO: implement UserRepository.delete")

    def list(self, limit: int = 100, offset: int = 0) -> list[UserRecord]:
        raise NotImplementedError("TODO: implement UserRepository.list")

    def get_by_email(self, email: str) -> UserRecord | None:
        """Lookup user by unique email."""
        raise NotImplementedError("TODO: implement UserRepository.get_by_email")

class AcademicRecordRepository(BaseRepository[AcademicRecord, str]):
    """Repository for student course completion/enrollment records."""
    def create(self, entity: AcademicRecord) -> AcademicRecord:
        raise NotImplementedError("TODO: implement AcademicRecordRepository.create")

    def get_by_id(self, entity_id: str) -> AcademicRecord | None:
        raise NotImplementedError(
            "TODO: implement AcademicRecordRepository.get_by_id"
        )

    def update(self, entity: AcademicRecord) -> AcademicRecord:
        raise NotImplementedError("TODO: implement AcademicRecordRepository.update")

    def delete(self, entity_id: str) -> None:
        raise NotImplementedError("TODO: implement AcademicRecordRepository.delete")

    def list(self, limit: int = 100, offset: int = 0) -> list[AcademicRecord]:
        raise NotImplementedError("TODO: implement AcademicRecordRepository.list")

    def get_completed_courses(self, user_id: str) -> list[str]:
        """Return normalized completed course codes for a student."""
        raise NotImplementedError(
            "TODO: implement AcademicRecordRepository.get_completed_courses"
        )

    def upsert_completed_courses(
        self, user_id: str, completed_courses: list[str]
    ) -> AcademicRecord:
        """Create or update completed courses in one call."""
        raise NotImplementedError(
            "TODO: implement AcademicRecordRepository.upsert_completed_courses"
        )

class FeedbackRepository(BaseRepository[FeedbackRecord, str]):
    """Repository for user feedback on advising responses."""
    def create(self, entity: FeedbackRecord) -> FeedbackRecord:
        raise NotImplementedError("TODO: implement FeedbackRepository.create")

    def get_by_id(self, entity_id: str) -> FeedbackRecord | None:
        raise NotImplementedError("TODO: implement FeedbackRepository.get_by_id")

    def update(self, entity: FeedbackRecord) -> FeedbackRecord:
        raise NotImplementedError("TODO: implement FeedbackRepository.update")

    def delete(self, entity_id: str) -> None:
        raise NotImplementedError("TODO: implement FeedbackRepository.delete")

    def list(self, limit: int = 100, offset: int = 0) -> list[FeedbackRecord]:
        raise NotImplementedError("TODO: implement FeedbackRepository.list")

    def list_feedback_by_user(self, user_id: str) -> list[FeedbackRecord]:
        """Return all feedback records authored by a user."""
        raise NotImplementedError(
            "TODO: implement FeedbackRepository.list_feedback_by_user"
        )