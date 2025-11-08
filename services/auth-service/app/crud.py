"""
CRUD operations for user management.
"""

from sqlalchemy.orm import Session
from typing import Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.models.database import User
from shared.schemas.common import UserCreate, UserUpdate
from .auth import get_password_hash


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email address."""
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    """Get user by ID."""
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, user_data: UserCreate) -> User:
    """
    Create a new user.

    Args:
        db: Database session
        user_data: User creation data with plain password

    Returns:
        Created user object
    """
    # Hash password
    hashed_password = get_password_hash(user_data.password)

    # Create user object
    db_user = User(
        email=user_data.email,
        password_hash=hashed_password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        role=user_data.role,
        is_active=True
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


def update_user(db: Session, user: User, user_data: UserUpdate) -> User:
    """
    Update user information.

    Args:
        db: Database session
        user: User object to update
        user_data: Update data (only provided fields will be updated)

    Returns:
        Updated user object
    """
    # Update only provided fields
    if user_data.first_name is not None:
        user.first_name = user_data.first_name

    if user_data.last_name is not None:
        user.last_name = user_data.last_name

    if user_data.role is not None:
        user.role = user_data.role

    if user_data.is_active is not None:
        user.is_active = user_data.is_active

    db.commit()
    db.refresh(user)

    return user


def delete_user(db: Session, user_id: str) -> bool:
    """
    Delete a user (soft delete by setting is_active=False).

    Args:
        db: Database session
        user_id: User ID to delete

    Returns:
        True if deleted successfully, False if user not found
    """
    user = get_user_by_id(db, user_id)

    if not user:
        return False

    user.is_active = False
    db.commit()

    return True


def list_users(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    role: Optional[str] = None,
    is_active: Optional[bool] = None
) -> list[User]:
    """
    List users with optional filtering.

    Args:
        db: Database session
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        role: Optional role filter
        is_active: Optional active status filter

    Returns:
        List of user objects
    """
    query = db.query(User)

    if role:
        query = query.filter(User.role == role)

    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    return query.offset(skip).limit(limit).all()
