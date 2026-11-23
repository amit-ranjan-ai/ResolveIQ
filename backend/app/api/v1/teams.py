from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.authorization import (
    require_organisation_roles,
    require_team_roles,
)
from app.db.dependencies import get_db
from app.models.organisation import Organisation
from app.models.organisation_membership import OrganisationMembership
from app.models.team import Team
from app.models.team_membership import TeamMembership
from app.schemas.team import (
    TeamCreate,
    TeamLeadUpdate,
    TeamReplace,
    TeamResponse,
    TeamUpdate,
)

router = APIRouter(
    tags=["Teams"],
)


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
            detail="Teams cannot be modified for an inactive or suspended organisation.",
        )

    return organisation


def get_team_or_404(
    team_id: UUID,
    db: Session,
) -> Team:
    team = db.get(Team, team_id)

    if team is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found.",
        )

    return team


@router.post(
    "/organisations/{organisation_id}/teams",
    response_model=TeamResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Organisation is not active."},
        404: {"description": "Organisation not found."},
        409: {"description": "A team with this name already exists."},
    },
)
def create_team(
    organisation_id: UUID,
    team_data: TeamCreate,
    db: Annotated[Session, Depends(get_db)],
    current_membership: Annotated[
        OrganisationMembership,
        Depends(require_organisation_roles("OWNER", "ADMIN")),
    ],
):
    get_active_organisation(organisation_id, db)

    team = Team(
        organisation_id=organisation_id,
        **team_data.model_dump(),
    )

    try:
        db.add(team)
        db.commit()
        db.refresh(team)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A team with this name already exists in this organisation.",
        ) from error

    return team


@router.get(
    "/organisations/{organisation_id}/teams",
    response_model=list[TeamResponse],
)
def get_organisation_teams(
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
        select(Team)
        .where(Team.organisation_id == organisation_id)
        .order_by(Team.created_at.desc())
    )

    return db.scalars(statement).all()


@router.get(
    "/teams/{team_id}",
    response_model=TeamResponse,
    responses={
        404: {"description": "Team not found."},
    },
)
def get_team(
    team_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_membership: Annotated[
        OrganisationMembership,
        Depends(
            require_team_roles(
                "OWNER",
                "ADMIN",
                "AGENT",
                "REQUESTER",
            )
        ),
    ],
):
    return get_team_or_404(team_id, db)


@router.put(
    "/teams/{team_id}",
    response_model=TeamResponse,
    responses={
        400: {"description": "Organisation is not active."},
        404: {"description": "Team or organisation not found."},
        409: {"description": "A team with this name already exists."},
    },
)
def replace_team(
    team_id: UUID,
    team_data: TeamReplace,
    db: Annotated[Session, Depends(get_db)],
):
    team = get_team_or_404(team_id, db)
    get_active_organisation(team.organisation_id, db)

    for field, value in team_data.model_dump().items():
        setattr(team, field, value)

    try:
        db.commit()
        db.refresh(team)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A team with this name already exists in this organisation.",
        ) from error

    return team


@router.patch(
    "/teams/{team_id}",
    response_model=TeamResponse,
    responses={
        400: {"description": "Organisation is not active or no fields provided."},
        404: {"description": "Team or organisation not found."},
        409: {"description": "A team with this name already exists."},
    },
)
def update_team(
    team_id: UUID,
    team_data: TeamUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_membership: Annotated[
        OrganisationMembership,
        Depends(
            require_team_roles(
                "OWNER",
                "ADMIN",
            )
        ),
    ],
):
    team = get_team_or_404(team_id, db)
    get_active_organisation(team.organisation_id, db)

    update_data = team_data.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided for update.",
        )

    for field, value in update_data.items():
        setattr(team, field, value)

    try:
        db.commit()
        db.refresh(team)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A team with this name already exists in this organisation.",
        ) from error

    return team


@router.patch(
    "/teams/{team_id}/lead",
    response_model=TeamResponse,
    responses={
        400: {
            "description": "Organisation, team, or membership is inactive or role is ineligible."
        },
        404: {"description": "Team or organisation membership not found."},
    },
)
def update_team_lead(
    team_id: UUID,
    lead_data: TeamLeadUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_membership: Annotated[
        OrganisationMembership,
        Depends(
            require_team_roles(
                "OWNER",
                "ADMIN",
            )
        ),
    ],
):
    team = get_team_or_404(team_id, db)

    get_active_organisation(team.organisation_id, db)

    if not team.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A Team Lead cannot be assigned to an inactive team.",
        )

    # A null membership ID removes the current Team Lead.
    if lead_data.organisation_membership_id is None:
        team.team_lead_membership_id = None

        db.commit()
        db.refresh(team)

        return team

    # Find an active organisation membership.
    statement = select(OrganisationMembership).where(
        OrganisationMembership.id == lead_data.organisation_membership_id,
        OrganisationMembership.organisation_id == team.organisation_id,
    )

    organisation_membership = db.scalar(statement)

    if organisation_membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organisation membership not found in this organisation.",
        )

    if not organisation_membership.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive organisation members cannot become Team Leads.",
        )

    # Only OWNER, ADMIN, and AGENT can become Team Leads.
    if organisation_membership.role not in {"OWNER", "ADMIN", "AGENT"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only OWNER, ADMIN, or AGENT members can become Team Leads.",
        )

    # The person must already belong to this specific team.
    team_membership_statement = select(TeamMembership).where(
        TeamMembership.team_id == team.id,
        TeamMembership.organisation_membership_id == organisation_membership.id,
        TeamMembership.organisation_id == team.organisation_id,
    )

    team_membership = db.scalar(team_membership_statement)

    if team_membership is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The selected member must belong to this team before becoming Team Lead.",
        )

    team.team_lead_membership_id = organisation_membership.id

    try:
        db.commit()
        db.refresh(team)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The selected Team Lead could not be assigned.",
        ) from error

    return team
