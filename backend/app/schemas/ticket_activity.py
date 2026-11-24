from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TicketActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organisation_id: UUID
    ticket_id: UUID
    actor_membership_id: UUID
    activity_type: str
    description: str
    old_value: str | None
    new_value: str | None
    extra_data: dict[str, Any] | None
    created_at: datetime
