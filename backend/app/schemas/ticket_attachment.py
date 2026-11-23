from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TicketAttachmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organisation_id: UUID
    ticket_id: UUID
    uploaded_by_membership_id: UUID
    original_filename: str
    content_type: str
    file_size: int
    created_at: datetime
