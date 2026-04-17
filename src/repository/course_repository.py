from __future__ import annotations
from src.repository.abstract_repository import BaseRepository
from src.repository.orm import (
    CatalogDocumentRecord,
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

    def list(self, limit: int = 100, offset: int = 0) -> list[CourseRecord]:
        raise NotImplementedError("TODO: implement CourseRepository.list")

    def get_by_course_code(
        self, course_code: str, catalog_version_id: str | None = None
    ) -> CourseRecord | None:
        """Lookup one course by catalog-visible course code."""
        raise NotImplementedError(
            "TODO: implement CourseRepository.get_by_course_code"
        )

    def search_courses(
        self, query: str, catalog_version_id: str | None = None, limit: int = 20
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

    def update(self, entity: CourseRequirementRecord) -> CourseRequirementRecord:
        raise NotImplementedError(
            "TODO: implement CourseRequirementRepository.update"
        )

    def delete(self, entity_id: str) -> None:
        raise NotImplementedError(
            "TODO: implement CourseRequirementRepository.delete"
        )

    def list(
        self, limit: int = 100, offset: int = 0
    ) -> list[CourseRequirementRecord]:
        raise NotImplementedError("TODO: implement CourseRequirementRepository.list")

    def get_requirements_by_course_code(
        self, course_code: str, catalog_version_id: str | None = None
    ) -> list[CourseRequirementRecord]:
        """Return normalized requirements for a specific course code."""
        raise NotImplementedError(
            "TODO: implement CourseRequirementRepository.get_requirements_by_course_code"
        )

    def upsert_requirements(
        self,
        course_code: str,
        requirement_records: list[CourseRequirementRecord],
        catalog_version_id: str | None = None,
    ) -> list[CourseRequirementRecord]:
        """Replace or merge requirement records for one course."""
        raise NotImplementedError(
            "TODO: implement CourseRequirementRepository.upsert_requirements"
        )

class CatalogDocumentRepository(BaseRepository[CatalogDocumentRecord, str]):
    """Repository for catalog source document metadata and lifecycle."""
    def create(self, entity: CatalogDocumentRecord) -> CatalogDocumentRecord:
        raise NotImplementedError("TODO: implement CatalogDocumentRepository.create")

    def get_by_id(self, entity_id: str) -> CatalogDocumentRecord | None:
        raise NotImplementedError(
            "TODO: implement CatalogDocumentRepository.get_by_id"
        )

    def update(self, entity: CatalogDocumentRecord) -> CatalogDocumentRecord:
        raise NotImplementedError("TODO: implement CatalogDocumentRepository.update")

    def delete(self, entity_id: str) -> None:
        raise NotImplementedError("TODO: implement CatalogDocumentRepository.delete")

    def list(self, limit: int = 100, offset: int = 0) -> list[CatalogDocumentRecord]:
        raise NotImplementedError("TODO: implement CatalogDocumentRepository.list")

    def list_by_user(self, user_id: str) -> list[CatalogDocumentRecord]:
        """List documents uploaded by a specific user."""
        raise NotImplementedError("TODO: implement CatalogDocumentRepository.list_by_user")

    def delete_by_user(self, user_id: str) -> None:
        """Delete all document records owned by a user."""
        raise NotImplementedError("TODO: implement CatalogDocumentRepository.delete_by_user")