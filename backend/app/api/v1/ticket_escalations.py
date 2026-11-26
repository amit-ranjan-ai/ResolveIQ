from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.authorization import check_membership_roles
from app.core.dependencies import get_current_user
from app.core.ticket_access import get_accessible_ticket
from app.db.dependencies import get_db
from app.models.organisation_membership import OrganisationMembership
from app.models.ticket_escalation import TicketEscalation
from app.models.user import User
from app.schemas.ticket_escalation import TicketEscalationResponse

router = APIRouter(tags=["Ticket Escalations"])


def get_manageable_escalation(
    escalation_id: UUID,
    current_user: User,
    db: Session,
) -> tuple[TicketEscalation, OrganisationMembership]:
    """Get an escalation and verify management permissions."""

    escalation = db.get(TicketEscalation, escalation_id)

    if escalation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Escalation not found.",
        )

    membership = check_membership_roles(
        organisation_id=escalation.organisation_id,
        current_user=current_user,
        db=db,
        allowed_roles=("OWNER", "ADMIN", "AGENT"),
    )

    if (
        membership.role == "AGENT"
        and escalation.recipient_membership_id != membership.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only manage escalations assigned to you.",
        )

    return escalation, membership


@router.get(
    "/organisations/{organisation_id}/ticket-escalations",
    response_model=list[TicketEscalationResponse],
)
def list_organisation_escalations(
    organisation_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[TicketEscalationResponse]:
    """List escalations for an organisation."""

    membership = check_membership_roles(
        organisation_id=organisation_id,
        current_user=current_user,
        db=db,
        allowed_roles=("OWNER", "ADMIN", "AGENT"),
    )

    query = select(TicketEscalation).where(
        TicketEscalation.organisation_id == organisation_id,
    )

    if membership.role == "AGENT":
        query = query.where(
            TicketEscalation.recipient_membership_id == membership.id,
        )

    query = query.order_by(TicketEscalation.created_at.desc())

    return list(db.scalars(query).all())


@router.get(
    "/tickets/{ticket_id}/escalations",
    response_model=list[TicketEscalationResponse],
)
def list_ticket_escalations(
    ticket_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[TicketEscalationResponse]:
    """List escalations for an accessible ticket."""

    ticket, membership = get_accessible_ticket(
        ticket_id,
        current_user,
        db,
    )

    if membership.role == "REQUESTER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view ticket escalations.",
        )

    query = select(TicketEscalation).where(
        TicketEscalation.organisation_id == ticket.organisation_id,
        TicketEscalation.ticket_id == ticket.id,
    )

    if membership.role == "AGENT":
        query = query.where(
            TicketEscalation.recipient_membership_id == membership.id,
        )

    query = query.order_by(TicketEscalation.created_at.desc())

    return list(db.scalars(query).all())


@router.patch(
    "/ticket-escalations/{escalation_id}/acknowledge",
    response_model=TicketEscalationResponse,
)
def acknowledge_escalation(
    escalation_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TicketEscalation:
    """Acknowledge a pending escalation."""

    escalation, _ = get_manageable_escalation(
        escalation_id,
        current_user,
        db,
    )

    if escalation.status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending escalations can be acknowledged.",
        )

    escalation.status = "ACKNOWLEDGED"
    escalation.acknowledged_at = datetime.now(UTC)

    db.commit()
    db.refresh(escalation)

    return escalation


@router.patch(
    "/ticket-escalations/{escalation_id}/resolve",
    response_model=TicketEscalationResponse,
)
def resolve_escalation(
    escalation_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TicketEscalation:
    """Resolve a pending or acknowledged escalation."""

    escalation, _ = get_manageable_escalation(
        escalation_id,
        current_user,
        db,
    )

    if escalation.status == "RESOLVED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Escalation is already resolved.",
        )

    escalation.status = "RESOLVED"
    escalation.resolved_at = datetime.now(UTC)

    db.commit()
    db.refresh(escalation)

    return escalation
