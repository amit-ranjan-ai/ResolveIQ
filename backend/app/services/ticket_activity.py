from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.ticket_activity import TicketActivity


def record_ticket_activity(
    db: Session,
    organisation_id: UUID,
    ticket_id: UUID,
    actor_membership_id: UUID,
    activity_type: str,
    description: str,
    old_value: str | None = None,
    new_value: str | None = None,
    extra_data: dict[str, Any] | None = None,
) -> TicketActivity:
    """Create a ticket activity record."""

    activity = TicketActivity(
        organisation_id=organisation_id,
        ticket_id=ticket_id,
        actor_membership_id=actor_membership_id,
        activity_type=activity_type,
        description=description,
        old_value=old_value,
        new_value=new_value,
        extra_data=extra_data,
    )

    db.add(activity)

    return activity
