import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TicketSLA(Base):
    __tablename__ = "ticket_slas"

    __table_args__ = (
        UniqueConstraint(
            "ticket_id",
            name="uq_ticket_slas_ticket_id",
        ),
        CheckConstraint(
            "first_response_minutes > 0",
            name="ck_ticket_slas_first_response_minutes",
        ),
        CheckConstraint(
            "resolution_minutes > 0",
            name="ck_ticket_slas_resolution_minutes",
        ),
        ForeignKeyConstraint(
            ["organisation_id", "ticket_id"],
            ["tickets.organisation_id", "tickets.id"],
            name="fk_ticket_slas_organisation_ticket",
        ),
        ForeignKeyConstraint(
            ["organisation_id", "sla_policy_id"],
            ["sla_policies.organisation_id", "sla_policies.id"],
            name="fk_ticket_slas_organisation_policy",
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

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    sla_policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
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

    response_due_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    resolution_due_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    first_responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    response_breached: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    resolution_breached: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
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
