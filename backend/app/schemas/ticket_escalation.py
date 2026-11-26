from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TicketEscalationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organisation_id: UUID
    ticket_id: UUID
    recipient_membership_id: UUID
    target_type: str
    escalation_level: str
    reason: str
    status: str
    created_at: datetime
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    updated_at: datetime
