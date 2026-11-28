from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.authorization import require_organisation_roles
from app.db.dependencies import get_db
from app.models.organisation import Organisation
from app.models.organisation_membership import OrganisationMembership
from app.schemas.ai import (
    TicketClassificationRequest,
    TicketClassificationResponse,
)
from app.services.ai.classification_service import classify_ticket

router = APIRouter(tags=["AI Classification"])


@router.post(
    "/organisations/{organisation_id}/ai/classify-ticket",
    response_model=TicketClassificationResponse,
    summary="Classify a new ticket",
    description=(
        "Generates explainable suggestions for ticket category, impact, "
        "urgency, priority, and assignment team. "
        "Confidence scores are heuristic indicators, not calibrated "
        "probabilities. The API does not create or modify tickets, "
        "and all suggestions require human review."
    ),
)
def classify_new_ticket(
    organisation_id: UUID,
    ticket_data: TicketClassificationRequest,
    db: Annotated[Session, Depends(get_db)],
    current_membership: Annotated[
        OrganisationMembership,
        Depends(
            require_organisation_roles(
                "OWNER",
                "ADMIN",
                "AGENT",
                "REQUESTER",
            )
        ),
    ],
):
    organisation = db.get(Organisation, organisation_id)

    if organisation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organisation not found.",
        )

    if organisation.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="AI classification is unavailable for an inactive or suspended organisation.",
        )
    result = classify_ticket(
        db=db,
        organisation_id=organisation_id,
        subject=ticket_data.subject,
        description=ticket_data.description,
    )

    return {
        "category": result["category"],
        "impact": result["impact"],
        "urgency": result["urgency"],
        "priority": result["priority"],
        "team": result["team"],
        "confidence_type": "heuristic",
        "requires_human_review": result["requires_human_review"],
        "overall_confidence": result["overall_confidence"],
        "fields_requiring_review": result["fields_requiring_review"],
    }
