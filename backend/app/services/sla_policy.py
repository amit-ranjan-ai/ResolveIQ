from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.sla_policy import SLAPolicy
from app.schemas.sla_policy import SLAPolicyUpdate


def get_sla_policies(
    organisation_id: UUID,
    db: Session,
) -> list[SLAPolicy]:
    """Get all SLA policies for an organisation."""

    statement = (
        select(SLAPolicy)
        .where(SLAPolicy.organisation_id == organisation_id)
        .order_by(SLAPolicy.priority)
    )

    return list(db.scalars(statement).all())


def update_sla_policy(
    organisation_id: UUID,
    priority: str,
    policy_data: SLAPolicyUpdate,
    db: Session,
) -> SLAPolicy:
    """Update an organisation's SLA policy without changing existing ticket deadlines."""

    policy = db.scalar(
        select(SLAPolicy).where(
            SLAPolicy.organisation_id == organisation_id,
            SLAPolicy.priority == priority,
        )
    )

    if policy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SLA policy not found.",
        )

    policy.first_response_minutes = policy_data.first_response_minutes
    policy.resolution_minutes = policy_data.resolution_minutes

    db.commit()
    db.refresh(policy)

    return policy
