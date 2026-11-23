from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TicketCommentCreate(BaseModel):
    message: str = Field(min_length=1, max_length=10000)
    is_internal: bool = False


class TicketCommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organisation_id: UUID
    ticket_id: UUID
    author_membership_id: UUID
    message: str
    is_internal: bool
    created_at: datetime
    updated_at: datetime
