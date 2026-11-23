from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TeamCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=500)


class TeamUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None

    @field_validator("name", "is_active", mode="before")
    @classmethod
    def reject_null_values(cls, value):
        if value is None:
            raise ValueError("This field cannot be null.")

        return value


class TeamReplace(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: str | None
    is_active: bool


class TeamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organisation_id: UUID
    name: str
    description: str | None
    team_lead_membership_id: UUID | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TeamLeadUpdate(BaseModel):
    organisation_membership_id: UUID | None
