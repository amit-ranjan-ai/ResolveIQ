from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.models.organisation import Organisation
from app.models.organisation_membership import OrganisationMembership
from app.models.team import Team
from app.models.team_membership import TeamMembership
from app.schemas.team_membership import (
    TeamMembershipCreate,
    TeamMembershipResponse,
)

router = APIRouter(
    tags=["Team Memberships"],
)


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
            detail="Team memberships cannot be modified for an inactive or suspended organisation.",
        )

    return organisation


@router.post(
    "/teams/{team_id}/members",
    response_model=TeamMembershipResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Team or organisation membership is inactive."},
        404: {"description": "Team or organisation membership not found."},
        409: {"description": "Member already belongs to this team."},
    },
)
def add_team_member(
    team_id: UUID,
    member_data: TeamMembershipCreate,
    db: Annotated[Session, Depends(get_db)],
):
    team = get_team_or_404(team_id, db)

    get_active_organisation(team.organisation_id, db)

    if not team.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Members cannot be added to an inactive team.",
        )

    statement = select(OrganisationMembership).where(
        OrganisationMembership.id == member_data.organisation_membership_id,
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
            detail="Inactive organisation members cannot be added to a team.",
        )

    team_membership = TeamMembership(
        organisation_id=team.organisation_id,
        team_id=team.id,
        organisation_membership_id=organisation_membership.id,
    )

    try:
        db.add(team_membership)
        db.commit()
        db.refresh(team_membership)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This member already belongs to this team.",
        ) from error

    return team_membership


@router.get(
    "/teams/{team_id}/members",
    response_model=list[TeamMembershipResponse],
    responses={
        404: {"description": "Team not found."},
    },
)
def get_team_members(
    team_id: UUID,
    db: Annotated[Session, Depends(get_db)],
):
    team = get_team_or_404(team_id, db)

    statement = (
        select(TeamMembership)
        .where(TeamMembership.team_id == team.id)
        .order_by(TeamMembership.created_at.desc())
    )

    return db.scalars(statement).all()


@router.delete(
    "/teams/{team_id}/members/{organisation_membership_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        400: {"description": "Organisation is not active."},
        404: {"description": "Team or team membership not found."},
    },
)
def remove_team_member(
    team_id: UUID,
    organisation_membership_id: UUID,
    db: Annotated[Session, Depends(get_db)],
):
    team = get_team_or_404(team_id, db)

    get_active_organisation(team.organisation_id, db)

    statement = select(TeamMembership).where(
        TeamMembership.team_id == team.id,
        TeamMembership.organisation_membership_id == organisation_membership_id,
    )

    team_membership = db.scalar(statement)

    if team_membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team membership not found.",
        )

    db.delete(team_membership)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
