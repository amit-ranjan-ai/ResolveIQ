from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)

OrganisationStatus = Literal["ACTIVE", "INACTIVE", "SUSPENDED"]


class OrganisationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    slug: str = Field(min_length=2, max_length=100)
    email: EmailStr | None = None
    status: OrganisationStatus = "ACTIVE"


class OrganisationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    email: str | None
    status: OrganisationStatus
    created_at: datetime
    updated_at: datetime


class OrganisationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    slug: str | None = Field(default=None, min_length=2, max_length=100)
    email: EmailStr | None = None
    status: OrganisationStatus | None = None

    @field_validator("name", "slug", "status", mode="before")
    @classmethod
    def reject_null_values(cls, value):
        if value is None:
            raise ValueError("This field cannot be null.")

        return value


class OrganisationReplace(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    slug: str = Field(min_length=2, max_length=100)
    email: EmailStr | None
    status: OrganisationStatus
