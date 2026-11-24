from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.core.ticket_access import get_accessible_ticket
from app.db.dependencies import get_db
from app.models.ticket_sla import TicketSLA
from app.models.user import User
from app.schemas.ticket_sla import TicketSLAMonitorResponse
from app.services.sla_monitoring import monitor_ticket_sla

router = APIRouter(tags=["Ticket SLA"])


@router.get(
    "/tickets/{ticket_id}/sla",
    response_model=TicketSLAMonitorResponse,
)
def get_ticket_sla(
    ticket_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Get live SLA monitoring information for a ticket."""

    ticket, _ = get_accessible_ticket(
        ticket_id,
        current_user,
        db,
    )

    ticket_sla = db.scalar(
        select(TicketSLA).where(
            TicketSLA.organisation_id == ticket.organisation_id,
            TicketSLA.ticket_id == ticket.id,
        )
    )

    if ticket_sla is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SLA tracking not found for this ticket.",
        )

    return monitor_ticket_sla(ticket, ticket_sla)
