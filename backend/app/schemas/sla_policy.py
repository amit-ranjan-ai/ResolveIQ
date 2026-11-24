from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

SLAPriority = Literal["P1", "P2", "P3", "P4"]


class SLAPolicyUpdate(BaseModel):
    first_response_minutes: int = Field(gt=0)
    resolution_minutes: int = Field(gt=0)


class SLAPolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organisation_id: UUID
    priority: SLAPriority
    first_response_minutes: int
    resolution_minutes: int
    created_at: datetime
    updated_at: datetime
