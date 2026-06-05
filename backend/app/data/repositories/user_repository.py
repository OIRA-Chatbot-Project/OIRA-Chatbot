from typing import Optional
from sqlalchemy.orm import Session

from app.data.models.user import User


class SQLUserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_clerk_id(self, clerk_user_id: str) -> Optional[User]:
        return self.db.query(User).filter(User.clerk_user_id == clerk_user_id).first()

    def get_by_internal_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def create(self, clerk_user_id: str, email: str, name: Optional[str]) -> User:
        user = User(clerk_user_id=clerk_user_id, email=email, name=name)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update(self, user: User) -> User:
        self.db.commit()
        self.db.refresh(user)
        return user
