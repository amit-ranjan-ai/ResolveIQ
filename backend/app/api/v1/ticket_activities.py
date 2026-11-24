from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.core.ticket_access import get_accessible_ticket
from app.db.dependencies import get_db
from app.models.ticket_activity import TicketActivity
from app.models.user import User
from app.schemas.ticket_activity import TicketActivityResponse

router = APIRouter(tags=["Ticket Activities"])


@router.get(
    "/tickets/{ticket_id}/activities",
    response_model=list[TicketActivityResponse],
)
def get_ticket_activities(
    ticket_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Get activity history for a ticket."""

    ticket, membership = get_accessible_ticket(
        ticket_id,
        current_user,
        db,
    )

    query = select(TicketActivity).where(
        TicketActivity.organisation_id == ticket.organisation_id,
        TicketActivity.ticket_id == ticket.id,
    )

    if membership.role == "REQUESTER":
        query = query.where(
            TicketActivity.activity_type != "INTERNAL_NOTE_ADDED",
        )

    query = query.order_by(TicketActivity.created_at.desc())

    return list(db.scalars(query).all())
