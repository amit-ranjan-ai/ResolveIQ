from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.authorization import check_membership_roles
from app.core.dependencies import get_current_user
from app.db.dependencies import get_db
from app.models.user import User
from app.schemas.sla_policy import (
    SLAPolicyResponse,
    SLAPolicyUpdate,
    SLAPriority,
)
from app.services.sla_policy import get_sla_policies, update_sla_policy

router = APIRouter(tags=["SLA Policies"])


@router.get(
    "/organisations/{organisation_id}/sla-policies",
    response_model=list[SLAPolicyResponse],
)
def list_sla_policies(
    organisation_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[SLAPolicyResponse]:
    """List all SLA policies for an organisation."""

    check_membership_roles(
        organisation_id=organisation_id,
        current_user=current_user,
        db=db,
        allowed_roles=("OWNER", "ADMIN"),
    )

    return get_sla_policies(organisation_id, db)


@router.patch(
    "/organisations/{organisation_id}/sla-policies/{priority}",
    response_model=SLAPolicyResponse,
)
def update_organisation_sla_policy(
    organisation_id: UUID,
    priority: SLAPriority,
    policy_data: SLAPolicyUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> SLAPolicyResponse:
    """Update response and resolution targets for an SLA priority."""

    check_membership_roles(
        organisation_id=organisation_id,
        current_user=current_user,
        db=db,
        allowed_roles=("OWNER", "ADMIN"),
    )

    return update_sla_policy(
        organisation_id=organisation_id,
        priority=priority,
        policy_data=policy_data,
        db=db,
    )
