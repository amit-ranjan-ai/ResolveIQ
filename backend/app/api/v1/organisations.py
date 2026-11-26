from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.authorization import require_organisation_roles
from app.core.dependencies import get_current_user
from app.db.dependencies import get_db
from app.models.organisation import Organisation
from app.models.organisation_membership import OrganisationMembership
from app.models.sla_policy import SLAPolicy
from app.models.user import User
from app.schemas.organisation import (
    OrganisationCreate,
    OrganisationReplace,
    OrganisationResponse,
    OrganisationUpdate,
)
from app.schemas.organisation_membership import (
    OrganisationMembershipCreate,
    OrganisationMembershipResponse,
)

router = APIRouter(
    prefix="/organisations",
    tags=["Organisations"],
)


@router.get(
    "/{organisation_id}/my-membership",
    response_model=OrganisationMembershipResponse,
    responses={
        404: {"description": "Active organisation membership not found."},
    },
)
def get_my_organisation_membership(
    organisation_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    statement = select(OrganisationMembership).where(
        OrganisationMembership.organisation_id == organisation_id,
        OrganisationMembership.user_id == current_user.id,
        OrganisationMembership.is_active.is_(True),
    )

    membership = db.scalar(statement)

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active organisation membership not found.",
        )

    return membership


@router.post(
    "/{organisation_id}/members",
    response_model=OrganisationMembershipResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        403: {"description": "Insufficient organisation permissions."},
        404: {"description": "Organisation or user not found."},
        409: {"description": "Membership already exists."},
    },
)
def create_organisation_membership(
    organisation_id: UUID,
    membership_data: OrganisationMembershipCreate,
    current_membership: Annotated[
        OrganisationMembership,
        Depends(require_organisation_roles("OWNER", "ADMIN")),
    ],
    db: Annotated[Session, Depends(get_db)],
):
    organisation = db.get(Organisation, organisation_id)

    if organisation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organisation not found.",
        )

    if membership_data.role == "OWNER" and current_membership.role != "OWNER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only an OWNER can assign the OWNER role.",
        )

    user = db.get(User, membership_data.user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add an inactive user to an organisation.",
        )

    existing_membership = db.scalar(
        select(OrganisationMembership).where(
            OrganisationMembership.organisation_id == organisation_id,
            OrganisationMembership.user_id == membership_data.user_id,
        )
    )

    if existing_membership is not None:
        if existing_membership.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already a member of this organisation.",
            )

        existing_membership.role = membership_data.role
        existing_membership.is_active = True

        try:
            db.commit()
            db.refresh(existing_membership)
        except IntegrityError as error:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Could not reactivate organisation membership.",
            ) from error

        return existing_membership

    membership = OrganisationMembership(
        organisation_id=organisation_id,
        user_id=membership_data.user_id,
        role=membership_data.role,
        is_active=True,
    )

    try:
        db.add(membership)
        db.commit()
        db.refresh(membership)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not create organisation membership.",
        ) from error

    return membership


@router.get(
    "/{organisation_id}/members",
    response_model=list[OrganisationMembershipResponse],
    responses={
        403: {"description": "Insufficient organisation permissions."},
        404: {"description": "Organisation not found."},
    },
)
def get_organisation_members(
    organisation_id: UUID,
    current_membership: Annotated[
        OrganisationMembership,
        Depends(require_organisation_roles("OWNER", "ADMIN")),
    ],
    db: Annotated[Session, Depends(get_db)],
):
    organisation = db.get(Organisation, organisation_id)

    if organisation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organisation not found.",
        )

    statement = (
        select(OrganisationMembership)
        .where(
            OrganisationMembership.organisation_id == organisation_id,
        )
        .order_by(OrganisationMembership.created_at.desc())
    )

    return db.scalars(statement).all()


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

    default_sla_policies = [
        {
            "priority": "P1",
            "first_response_minutes": 15,
            "resolution_minutes": 240,
        },
        {
            "priority": "P2",
            "first_response_minutes": 30,
            "resolution_minutes": 480,
        },
        {
            "priority": "P3",
            "first_response_minutes": 240,
            "resolution_minutes": 1440,
        },
        {
            "priority": "P4",
            "first_response_minutes": 480,
            "resolution_minutes": 4320,
        },
    ]

    try:
        db.add(organisation)
        db.flush()

        for policy_data in default_sla_policies:
            db.add(
                SLAPolicy(
                    organisation_id=organisation.id,
                    **policy_data,
                )
            )

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
