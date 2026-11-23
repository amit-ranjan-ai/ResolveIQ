from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.core.security import hash_password
from app.db.dependencies import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"description": "Email address is already registered."},
    },
)
def create_user(
    user_data: UserCreate,
    db: Annotated[Session, Depends(get_db)],
):
    normalized_email = str(user_data.email).strip().lower()

    existing_user = db.scalar(
        select(User).where(
            func.lower(User.email) == normalized_email,
        )
    )

    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This email address is already registered.",
        )

    user = User(
        full_name=user_data.full_name.strip(),
        email=normalized_email,
        password_hash=hash_password(user_data.password),
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)

    except IntegrityError as error:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This email address is already registered.",
        ) from error

    return user


@router.get(
    "/me",
    response_model=UserResponse,
)
def get_current_user_profile(
    current_user: Annotated[User, Depends(get_current_user)],
):
    return current_user


@router.patch(
    "/me",
    response_model=UserResponse,
)
def update_current_user_profile(
    user_data: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    current_user.full_name = user_data.full_name

    db.commit()
    db.refresh(current_user)

    return current_user
