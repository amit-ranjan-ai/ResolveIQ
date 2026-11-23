from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.authorization import check_membership_roles
from app.core.dependencies import get_current_user
from app.db.dependencies import get_db
from app.models.organisation_membership import OrganisationMembership
from app.models.team_membership import TeamMembership
from app.models.ticket import Ticket
from app.models.ticket_comment import TicketComment
from app.models.user import User
from app.schemas.ticket_comment import (
    TicketCommentCreate,
    TicketCommentResponse,
)

router = APIRouter(tags=["Ticket Comments"])


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


@router.post(
    "/tickets/{ticket_id}/comments",
    response_model=TicketCommentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_ticket_comment(
    ticket_id: UUID,
    comment_data: TicketCommentCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Create a public comment or an internal note."""

    ticket, membership = get_accessible_ticket(
        ticket_id,
        current_user,
        db,
    )

    if membership.role == "REQUESTER" and comment_data.is_internal:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requesters cannot create internal notes.",
        )

    comment = TicketComment(
        organisation_id=ticket.organisation_id,
        ticket_id=ticket.id,
        author_membership_id=membership.id,
        message=comment_data.message,
        is_internal=comment_data.is_internal,
    )

    db.add(comment)
    db.commit()
    db.refresh(comment)

    return comment


@router.get(
    "/tickets/{ticket_id}/comments",
    response_model=list[TicketCommentResponse],
)
def get_ticket_comments(
    ticket_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Get comments for a ticket."""

    ticket, membership = get_accessible_ticket(
        ticket_id,
        current_user,
        db,
    )

    query = select(TicketComment).where(
        TicketComment.organisation_id == ticket.organisation_id,
        TicketComment.ticket_id == ticket.id,
    )

    if membership.role == "REQUESTER":
        query = query.where(
            TicketComment.is_internal.is_(False),
        )

    query = query.order_by(TicketComment.created_at.asc())

    return list(db.scalars(query).all())
