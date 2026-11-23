import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TeamMembership(Base):
    __tablename__ = "team_memberships"

    __table_args__ = (
        ForeignKeyConstraint(
            ["organisation_id", "team_id"],
            ["teams.organisation_id", "teams.id"],
            name="fk_team_memberships_organisation_team",
        ),
        ForeignKeyConstraint(
            ["organisation_id", "organisation_membership_id"],
            [
                "organisation_memberships.organisation_id",
                "organisation_memberships.id",
            ],
            name="fk_team_memberships_organisation_member",
        ),
        UniqueConstraint(
            "team_id",
            "organisation_membership_id",
            name="uq_team_memberships_team_member",
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

    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    organisation_membership_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
