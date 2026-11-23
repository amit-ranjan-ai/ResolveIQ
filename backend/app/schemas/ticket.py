from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

ImpactLevel = Literal["LOW", "MEDIUM", "HIGH"]
UrgencyLevel = Literal["LOW", "MEDIUM", "HIGH"]
PriorityLevel = Literal["P1", "P2", "P3", "P4"]


class TicketCreate(BaseModel):
    requester_membership_id: UUID
    category_id: UUID | None = None

    subject: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=5)

    impact: ImpactLevel
    urgency: UrgencyLevel

    source: Literal["WEB", "EMAIL", "PHONE", "API"] = "WEB"


class TicketUpdate(BaseModel):
    subject: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, min_length=5)

    category_id: UUID | None = None
    assigned_team_id: UUID | None = None
    assigned_agent_membership_id: UUID | None = None

    impact: ImpactLevel | None = None
    urgency: UrgencyLevel | None = None

    @field_validator(
        "subject",
        "description",
        "impact",
        "urgency",
        mode="before",
    )
    @classmethod
    def reject_null_values(cls, value):
        if value is None:
            raise ValueError("This field cannot be null.")

        return value


class TicketAssignmentUpdate(BaseModel):
    assigned_team_id: UUID | None = None
    assigned_agent_membership_id: UUID | None = None


class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organisation_id: UUID
    ticket_number: str

    requester_membership_id: UUID
    category_id: UUID | None

    assigned_team_id: UUID | None
    assigned_agent_membership_id: UUID | None

    subject: str
    description: str

    status: str
    priority: PriorityLevel
    impact: ImpactLevel
    urgency: UrgencyLevel

    source: str

    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    closed_at: datetime | None
