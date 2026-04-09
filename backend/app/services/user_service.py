"""
UserService: create/upsert/retrieve user records.
"""
from datetime import datetime
from typing import Optional

from app.data.repositories.user_repository import SQLUserRepository
from app.data.models.user import User


class UserService:
    def __init__(self, user_repo: SQLUserRepository) -> None:
        self.user_repo = user_repo

    def upsert_user(
        self,
        clerk_user_id: str,
        email: str,
        name: Optional[str],
        requesting_clerk_id: str,
    ) -> User:
        """Create or update a user. Raises 403 if requesting_clerk_id doesn't match."""
        from fastapi import HTTPException

        if requesting_clerk_id != clerk_user_id:
            raise HTTPException(
                status_code=403,
                detail="Cannot create user for different clerk_user_id",
            )

        existing = self.user_repo.get_by_clerk_id(clerk_user_id)
        if existing:
            if email != existing.email or name != existing.name:
                existing.email = email
                existing.name = name
                existing.updated_at = (
                    datetime.now(datetime.UTC)  # type: ignore
                    if hasattr(datetime, "UTC")
                    else datetime.utcnow()
                )
                return self.user_repo.update(existing)
            return existing

        return self.user_repo.create(clerk_user_id=clerk_user_id, email=email, name=name)

    def get_by_clerk_id(self, clerk_user_id: str) -> Optional[User]:
        return self.user_repo.get_by_clerk_id(clerk_user_id)

    def require_by_clerk_id(self, clerk_user_id: str) -> User:
        """Return user or raise 404."""
        from fastapi import HTTPException

        user = self.user_repo.get_by_clerk_id(clerk_user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    def update_profile_facts(self, clerk_user_id: str, facts: dict) -> None:
        import json

        user = self.user_repo.get_by_clerk_id(clerk_user_id)
        if user:
            user.profile_facts = json.dumps(facts)
            self.user_repo.update(user)
