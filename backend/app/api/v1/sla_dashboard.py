from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.authorization import check_membership_roles
from app.core.dependencies import get_current_user
from app.db.dependencies import get_db
from app.models.user import User
from app.schemas.sla_dashboard import SLADashboardResponse
from app.services.sla_dashboard import build_sla_dashboard

router = APIRouter(tags=["SLA Dashboard"])


@router.get(
    "/organisations/{organisation_id}/sla-dashboard",
    response_model=SLADashboardResponse,
)
def get_sla_dashboard(
    organisation_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> SLADashboardResponse:
    """Get organisation-wide SLA analytics."""

    check_membership_roles(
        organisation_id=organisation_id,
        current_user=current_user,
        db=db,
        allowed_roles=("OWNER", "ADMIN"),
    )

    return build_sla_dashboard(
        organisation_id=organisation_id,
        db=db,
    )
