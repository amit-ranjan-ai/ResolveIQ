from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

SLATargetStatus = Literal[
    "ON_TRACK",
    "AT_RISK",
    "BREACHED",
    "MET",
]


class TicketSLAMonitorResponse(BaseModel):
    ticket_id: UUID
    organisation_id: UUID

    ticket_priority: Literal["P1", "P2", "P3", "P4"]
    ticket_status: str

    response_due_at: datetime
    resolution_due_at: datetime

    first_responded_at: datetime | None
    resolved_at: datetime | None

    response_status: SLATargetStatus
    resolution_status: SLATargetStatus

    response_remaining_seconds: int
    resolution_remaining_seconds: int

    response_breached: bool
    resolution_breached: bool
