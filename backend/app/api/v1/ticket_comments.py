from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.core.ticket_access import get_accessible_ticket
from app.db.dependencies import get_db
from app.models.ticket_comment import TicketComment
from app.models.ticket_sla import TicketSLA
from app.models.user import User
from app.schemas.ticket_comment import (
    TicketCommentCreate,
    TicketCommentResponse,
)
from app.services.ticket_activity import record_ticket_activity

router = APIRouter(tags=["Ticket Comments"])


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

    # Record the first public response from support staff.
    if membership.role in ("OWNER", "ADMIN", "AGENT") and not comment_data.is_internal:
        ticket_sla = db.scalar(
            select(TicketSLA).where(
                TicketSLA.organisation_id == ticket.organisation_id,
                TicketSLA.ticket_id == ticket.id,
            )
        )

        if ticket_sla is not None and ticket_sla.first_responded_at is None:
            ticket_sla.first_responded_at = datetime.now(UTC)

    activity_type = (
        "INTERNAL_NOTE_ADDED" if comment_data.is_internal else "COMMENT_ADDED"
    )

    description = (
        "An internal note was added."
        if comment_data.is_internal
        else "A comment was added."
    )

    record_ticket_activity(
        db=db,
        organisation_id=ticket.organisation_id,
        ticket_id=ticket.id,
        actor_membership_id=membership.id,
        activity_type=activity_type,
        description=description,
    )

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
