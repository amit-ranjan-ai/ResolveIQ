from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OrganisationMembershipCreate(BaseModel):
    user_id: UUID
    role: Literal["OWNER", "ADMIN", "AGENT", "REQUESTER"]


class OrganisationMembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organisation_id: UUID
    user_id: UUID
    role: str
    is_active: bool
