import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SLAPolicy(Base):
    __tablename__ = "sla_policies"

    __table_args__ = (
        UniqueConstraint(
            "organisation_id",
            "priority",
            name="uq_sla_policies_organisation_priority",
        ),
        UniqueConstraint(
            "organisation_id",
            "id",
            name="uq_sla_policies_organisation_id",
        ),
        CheckConstraint(
            "priority IN ('P1', 'P2', 'P3', 'P4')",
            name="ck_sla_policies_priority",
        ),
        CheckConstraint(
            "first_response_minutes > 0",
            name="ck_sla_policies_first_response_minutes",
        ),
        CheckConstraint(
            "resolution_minutes > 0",
            name="ck_sla_policies_resolution_minutes",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organisations.id"),
        nullable=False,
    )

    priority: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    first_response_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    resolution_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
