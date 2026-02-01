from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import uuid

from app.models.user import User
from app.schemas.auth import UserCreate
from app.utils.security import get_password_hash, verify_password


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email address"""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Get a user by ID"""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user"""
        hashed_password = get_password_hash(user_data.password)
        
        user = User(
            email=user_data.email,
            hashed_password=hashed_password,
            name=user_data.name,
            date_of_birth=user_data.date_of_birth,
        )
        
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate a user by email and password"""
        user = await self.get_user_by_email(email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user
