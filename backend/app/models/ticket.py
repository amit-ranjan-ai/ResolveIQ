import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Ticket(Base):
    __tablename__ = "tickets"

    __table_args__ = (
        UniqueConstraint(
            "organisation_id",
            "ticket_number",
            name="uq_tickets_organisation_ticket_number",
        ),
        UniqueConstraint(
            "organisation_id",
            "id",
            name="uq_tickets_organisation_id",
        ),
        CheckConstraint(
            "status IN ('Open', 'Assigned', 'In Progress', "
            "'Pending', 'Resolved', 'Closed', 'Reopened')",
            name="ck_tickets_status",
        ),
        CheckConstraint(
            "priority IN ('P1', 'P2', 'P3', 'P4')",
            name="ck_tickets_priority",
        ),
        CheckConstraint(
            "impact IN ('LOW', 'MEDIUM', 'HIGH')",
            name="ck_tickets_impact",
        ),
        CheckConstraint(
            "urgency IN ('LOW', 'MEDIUM', 'HIGH')",
            name="ck_tickets_urgency",
        ),
        ForeignKeyConstraint(
            ["organisation_id", "requester_membership_id"],
            [
                "organisation_memberships.organisation_id",
                "organisation_memberships.id",
            ],
            name="fk_tickets_organisation_requester",
        ),
        ForeignKeyConstraint(
            ["organisation_id", "assigned_agent_membership_id"],
            [
                "organisation_memberships.organisation_id",
                "organisation_memberships.id",
            ],
            name="fk_tickets_organisation_assigned_agent",
        ),
        ForeignKeyConstraint(
            ["organisation_id", "category_id"],
            ["categories.organisation_id", "categories.id"],
            name="fk_tickets_organisation_category",
        ),
        ForeignKeyConstraint(
            ["organisation_id", "assigned_team_id"],
            ["teams.organisation_id", "teams.id"],
            name="fk_tickets_organisation_team",
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

    ticket_number: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    requester_membership_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    assigned_team_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    assigned_agent_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    subject: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    priority: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    impact: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    urgency: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    source: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="WEB",
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

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
