from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.models.organisation import Organisation
from app.schemas.organisation import (
    OrganisationCreate,
    OrganisationReplace,
    OrganisationResponse,
    OrganisationUpdate,
)

router = APIRouter(
    prefix="/organisations",
    tags=["Organisations"],
)


@router.post(
    "/",
    response_model=OrganisationResponse,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"description": "An organisation with this slug already exists."}},
)
def create_organisation(
    organisation_data: OrganisationCreate,
    db: Annotated[Session, Depends(get_db)],
):
    organisation = Organisation(**organisation_data.model_dump())

    try:
        db.add(organisation)
        db.commit()
        db.refresh(organisation)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An organisation with this slug already exists.",
        ) from error

    return organisation


@router.get(
    "/",
    response_model=list[OrganisationResponse],
)
def get_organisations(
    db: Annotated[Session, Depends(get_db)],
):
    statement = select(Organisation).order_by(Organisation.created_at.desc())
    organisations = db.scalars(statement).all()

    return organisations


@router.get(
    "/{organisation_id}",
    response_model=OrganisationResponse,
    responses={404: {"description": "Organisation not found."}},
)
def get_organisation_by_id(
    organisation_id: UUID,
    db: Annotated[Session, Depends(get_db)],
):
    organisation = db.get(Organisation, organisation_id)

    if organisation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organisation not found.",
        )

    return organisation


@router.put(
    "/{organisation_id}",
    response_model=OrganisationResponse,
    responses={
        400: {"description": "At least one field must be provided for update."},
        404: {"description": "Organisation not found."},
        409: {"description": "An organisation with this slug already exists."},
    },
)
def update_organisation(
    organisation_id: UUID,
    organisation_data: OrganisationReplace,
    db: Annotated[Session, Depends(get_db)],
):
    organisation = db.get(Organisation, organisation_id)

    if organisation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organisation not found.",
        )

    update_data = organisation_data.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided for update.",
        )

    for field, value in update_data.items():
        setattr(organisation, field, value)

    try:
        db.commit()
        db.refresh(organisation)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An organisation with this slug already exists.",
        ) from error

    return organisation


@router.patch(
    "/{organisation_id}",
    response_model=OrganisationResponse,
    responses={
        400: {"description": "At least one field must be provided for update."},
        404: {"description": "Organisation not found."},
        409: {"description": "An organisation with this slug already exists."},
    },
)
def partially_update_organisation(
    organisation_id: UUID,
    organisation_data: OrganisationUpdate,
    db: Annotated[Session, Depends(get_db)],
):
    organisation = db.get(Organisation, organisation_id)

    if organisation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organisation not found.",
        )

    update_data = organisation_data.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided for update.",
        )

    for field, value in update_data.items():
        setattr(organisation, field, value)

    try:
        db.commit()
        db.refresh(organisation)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An organisation with this slug already exists.",
        ) from error

    return organisation
