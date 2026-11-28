from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.authorization import require_organisation_roles
from app.db.dependencies import get_db
from app.models.category import Category
from app.models.organisation import Organisation
from app.models.organisation_membership import OrganisationMembership
from app.schemas.category import (
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
)

router = APIRouter(tags=["Categories"])


def get_active_organisation(
    organisation_id: UUID,
    db: Session,
) -> Organisation:
    organisation = db.get(Organisation, organisation_id)

    if organisation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organisation not found.",
        )

    if organisation.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Categories cannot be modified for an inactive or suspended organisation.",
        )

    return organisation


def get_category_or_404(
    category_id: UUID,
    db: Session,
) -> Category:
    category = db.get(Category, category_id)

    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found.",
        )

    return category


@router.post(
    "/organisations/{organisation_id}/categories",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_category(
    organisation_id: UUID,
    category_data: CategoryCreate,
    db: Annotated[Session, Depends(get_db)],
    current_membership: Annotated[
        OrganisationMembership,
        Depends(require_organisation_roles("OWNER", "ADMIN")),
    ],
):
    get_active_organisation(organisation_id, db)

    category = Category(
        organisation_id=organisation_id,
        **category_data.model_dump(),
    )

    try:
        db.add(category)
        db.commit()
        db.refresh(category)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A category with this name already exists in this organisation.",
        ) from error

    return category


@router.get(
    "/organisations/{organisation_id}/categories",
    response_model=list[CategoryResponse],
)
def get_organisation_categories(
    organisation_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_membership: Annotated[
        OrganisationMembership,
        Depends(
            require_organisation_roles(
                "OWNER",
                "ADMIN",
                "AGENT",
                "REQUESTER",
            )
        ),
    ],
):
    organisation = db.get(Organisation, organisation_id)

    if organisation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organisation not found.",
        )

    statement = (
        select(Category)
        .where(Category.organisation_id == organisation_id)
        .order_by(Category.created_at.desc())
    )

    return db.scalars(statement).all()


@router.patch(
    "/organisations/{organisation_id}/categories/{category_id}",
    response_model=CategoryResponse,
)
def update_category(
    organisation_id: UUID,
    category_id: UUID,
    category_data: CategoryUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_membership: Annotated[
        OrganisationMembership,
        Depends(require_organisation_roles("OWNER", "ADMIN")),
    ],
):
    get_active_organisation(organisation_id, db)

    category = get_category_or_404(category_id, db)

    if category.organisation_id != organisation_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found in this organisation.",
        )

    update_data = category_data.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided for update.",
        )

    for field, value in update_data.items():
        setattr(category, field, value)

    try:
        db.commit()
        db.refresh(category)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A category with this name already exists in this organisation.",
        ) from error

    return category
