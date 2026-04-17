from __future__ import annotations
from src.repository.orm import AcademicRecord, FeedbackRecord, UserRecord
from src.repository.unit_of_work import UnitOfWork
from src.repository.user_repository import (
    AcademicRecordRepository,
    FeedbackRepository,
    UserRepository,
)

class UserService:
    """Business logic for user profile and academic context management."""
    def __init__(
        self,
        user_repository: UserRepository,
        academic_record_repository: AcademicRecordRepository,
        feedback_repository: FeedbackRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self.user_repository = user_repository
        self.academic_record_repository = academic_record_repository
        self.feedback_repository = feedback_repository
        self.unit_of_work = unit_of_work

    def register_user(
        self, email: str, first_name: str, last_name: str
    ) -> UserRecord:
        with self.unit_of_work:
            return self._register_user_in_transaction(
                email=email,
                first_name=first_name,
                last_name=last_name,
            )

    def get_profile(self, user_id: str) -> UserRecord | None:
        raise NotImplementedError("TODO: implement UserService.get_profile")

    def update_profile(self, profile: UserRecord) -> UserRecord:
        with self.unit_of_work:
            return self._update_profile_in_transaction(profile=profile)

    def upsert_academic_record(
        self,
        user_id: str,
        completed_courses: list[str],
        current_courses: list[str],
        target_term: str | None,
    ) -> AcademicRecord:
        with self.unit_of_work:
            return self._upsert_academic_record_in_transaction(
                user_id=user_id,
                completed_courses=completed_courses,
                current_courses=current_courses,
                target_term=target_term,
            )

    def add_feedback(
        self,
        user_id: str,
        session_id: str,
        message_id: str,
        rating: int,
        comment: str | None = None,
    ) -> FeedbackRecord:
        with self.unit_of_work:
            return self._add_feedback_in_transaction(
                user_id=user_id,
                session_id=session_id,
                message_id=message_id,
                rating=rating,
                comment=comment,
            )

    def get_completed_courses(self, user_id: str) -> list[str]:
        raise NotImplementedError("TODO: implement UserService.get_completed_courses")

    def _register_user_in_transaction(
        self,
        email: str,
        first_name: str,
        last_name: str,
    ) -> UserRecord:
        raise NotImplementedError(
            "TODO: implement UserService._register_user_in_transaction"
        )

    def _update_profile_in_transaction(self, profile: UserRecord) -> UserRecord:
        raise NotImplementedError(
            "TODO: implement UserService._update_profile_in_transaction"
        )

    def _upsert_academic_record_in_transaction(
        self,
        user_id: str,
        completed_courses: list[str],
        current_courses: list[str],
        target_term: str | None,
    ) -> AcademicRecord:
        raise NotImplementedError(
            "TODO: implement UserService._upsert_academic_record_in_transaction"
        )

    def _add_feedback_in_transaction(
        self,
        user_id: str,
        session_id: str,
        message_id: str,
        rating: int,
        comment: str | None = None,
    ) -> FeedbackRecord:
        raise NotImplementedError(
            "TODO: implement UserService._add_feedback_in_transaction"
        )
