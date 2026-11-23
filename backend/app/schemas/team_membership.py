from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TeamMembershipCreate(BaseModel):
    organisation_membership_id: UUID


class TeamMembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organisation_id: UUID
    team_id: UUID
    organisation_membership_id: UUID
    created_at: datetime
