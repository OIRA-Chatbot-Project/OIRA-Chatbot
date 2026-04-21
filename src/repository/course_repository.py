from __future__ import annotations
from src.repository.abstract_repository import BaseRepository
from src.repository.orm import (
    CourseRecord,
    CourseRequirementRecord,
)


class CourseRepository(BaseRepository[CourseRecord, str]):
    """Repository for structured course catalog records."""

    def create(self, entity: CourseRecord) -> CourseRecord:
        raise NotImplementedError("TODO: implement CourseRepository.create")

    def get_by_id(self, entity_id: str) -> CourseRecord | None:
        raise NotImplementedError("TODO: implement CourseRepository.get_by_id")

    def update(self, entity: CourseRecord) -> CourseRecord:
        raise NotImplementedError("TODO: implement CourseRepository.update")

    def delete(self, entity_id: str) -> None:
        raise NotImplementedError("TODO: implement CourseRepository.delete")

    def list(self, *args) -> list[CourseRecord]:
        raise NotImplementedError("TODO: implement CourseRepository.list")

    def get_by_course_code(
        self, course_prefix: str, course_number: str, catalog_year: str | None = None
    ) -> CourseRecord | None:
        """Lookup one course by catalog-visible course code."""
        raise NotImplementedError(
            "TODO: implement CourseRepository.get_by_course_code"
        )

    def search_courses(
        self, query: str, catalog_year: str | None = None, limit: int = 20
    ) -> list[CourseRecord]:
        """Perform structured course search (code/title/description)."""
        raise NotImplementedError("TODO: implement CourseRepository.search_courses")

    def upsert_course(self, entity: CourseRecord) -> CourseRecord:
        """Create or update a course in one call."""
        raise NotImplementedError("TODO: implement CourseRepository.upsert_course")


class CourseRequirementRepository(BaseRepository[CourseRequirementRecord, str]):
    """Repository for prerequisite and corequisite expressions."""

    def create(self, entity: CourseRequirementRecord) -> CourseRequirementRecord:
        raise NotImplementedError(
            "TODO: implement CourseRequirementRepository.create"
        )

    def get_by_id(self, entity_id: str) -> CourseRequirementRecord | None:
        raise NotImplementedError(
            "TODO: implement CourseRequirementRepository.get_by_id"
        )
    
    def get_by_course_code(
        self, course_prefix: str, course_number: str, catalog_year: str | None = None
    ) -> CourseRequirementRecord | None:
        raise NotImplementedError(
            "TODO: implement CourseRequirementRepository.get_by_course_code"
        )

    def update(self, entity: CourseRequirementRecord) -> CourseRequirementRecord:
        raise NotImplementedError(
            "TODO: implement CourseRequirementRepository.update"
        )

    def delete(self, entity_id: str) -> None:
        raise NotImplementedError(
            "TODO: implement CourseRequirementRepository.delete"
        )

    def list(
        self, query: str, limit: int = 100, offset: int = 0
    ) -> list[CourseRequirementRecord]:
        raise NotImplementedError("TODO: implement CourseRequirementRepository.list")

    def upsert_requirements(
        self,
        course_prefix: str,
        course_number: str,
        requirement_records: list[CourseRequirementRecord],
        catalog_year: str | None = None,
    ) -> list[CourseRequirementRecord]:
        """Replace or merge requirement records for one course."""
        raise NotImplementedError(
            "TODO: implement CourseRequirementRepository.upsert_requirements"
        )