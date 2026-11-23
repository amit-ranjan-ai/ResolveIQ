from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.authorization import check_membership_roles
from app.models.organisation_membership import OrganisationMembership
from app.models.team_membership import TeamMembership
from app.models.ticket import Ticket
from app.models.user import User


def get_accessible_ticket(
    ticket_id: UUID,
    current_user: User,
    db: Session,
) -> tuple[Ticket, OrganisationMembership]:
    """Get a ticket and verify the current user's access."""

    ticket = db.get(Ticket, ticket_id)

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found.",
        )

    membership = check_membership_roles(
        ticket.organisation_id,
        current_user,
        db,
        ("OWNER", "ADMIN", "AGENT", "REQUESTER"),
    )

    if membership.role == "REQUESTER":
        if ticket.requester_membership_id != membership.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found.",
            )

    elif membership.role == "AGENT":
        is_assigned_agent = ticket.assigned_agent_membership_id == membership.id

        is_team_member = False

        if ticket.assigned_team_id is not None:
            is_team_member = (
                db.scalar(
                    select(TeamMembership.id).where(
                        TeamMembership.organisation_id == ticket.organisation_id,
                        TeamMembership.team_id == ticket.assigned_team_id,
                        TeamMembership.organisation_membership_id == membership.id,
                    )
                )
                is not None
            )

        if not is_assigned_agent and not is_team_member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found.",
            )

    return ticket, membership
