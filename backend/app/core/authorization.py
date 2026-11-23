from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.dependencies import get_db
from app.models.organisation_membership import OrganisationMembership
from app.models.team import Team
from app.models.user import User


def check_membership_roles(
    organisation_id: UUID,
    current_user: User,
    db: Session,
    allowed_roles: tuple[str, ...],
) -> OrganisationMembership:
    """Check whether the user has an active organisation membership."""

    membership = db.scalar(
        select(OrganisationMembership).where(
            OrganisationMembership.organisation_id == organisation_id,
            OrganisationMembership.user_id == current_user.id,
            OrganisationMembership.is_active.is_(True),
        )
    )

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have an active membership in this organisation.",
        )

    if membership.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action.",
        )

    return membership


def require_organisation_roles(*allowed_roles: str):
    """Require an allowed role in an organisation."""

    def check_organisation_role(
        organisation_id: UUID,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_db)],
    ) -> OrganisationMembership:
        return check_membership_roles(
            organisation_id,
            current_user,
            db,
            allowed_roles,
        )

    return check_organisation_role


def require_team_roles(*allowed_roles: str):
    """Require an allowed role in the organisation that owns a team."""

    def check_team_role(
        team_id: UUID,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_db)],
    ) -> OrganisationMembership:
        team = db.get(Team, team_id)

        if team is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team not found.",
            )

        return check_membership_roles(
            team.organisation_id,
            current_user,
            db,
            allowed_roles,
        )

    return check_team_role
