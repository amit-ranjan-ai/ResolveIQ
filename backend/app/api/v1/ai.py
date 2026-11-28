from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.authorization import require_organisation_roles
from app.core.dependencies import get_current_user
from app.core.ticket_access import get_accessible_ticket
from app.db.dependencies import get_db
from app.models.organisation import Organisation
from app.models.organisation_membership import OrganisationMembership
from app.models.ticket_comment import TicketComment
from app.models.user import User
from app.schemas.ai import (
    TicketClassificationRequest,
    TicketClassificationResponse,
    TicketReplySuggestionResponse,
)
from app.services.ai.classification_service import classify_ticket
from app.services.ai.reply_service import (
    OllamaServiceError,
    generate_ticket_reply,
)

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


@router.post(
    "/tickets/{ticket_id}/ai/suggest-reply",
    response_model=TicketReplySuggestionResponse,
    summary="Generate an AI-suggested ticket reply",
    description=(
        "Generates a customer-facing reply draft using the local Ollama model. "
        "Only public ticket comments are used as context. "
        "The generated reply is not saved or sent automatically "
        "and must be reviewed by a human."
    ),
)
def suggest_ticket_reply(
    ticket_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    ticket, membership = get_accessible_ticket(
        ticket_id,
        current_user,
        db,
    )

    if membership.role not in ("OWNER", "ADMIN", "AGENT"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only support staff can generate suggested replies.",
        )

    public_comments = db.scalars(
        select(TicketComment)
        .where(
            TicketComment.organisation_id == ticket.organisation_id,
            TicketComment.ticket_id == ticket.id,
            TicketComment.is_internal.is_(False),
        )
        .order_by(TicketComment.created_at.asc())
    ).all()

    try:
        result = generate_ticket_reply(
            ticket=ticket,
            public_comments=public_comments,
        )
    except OllamaServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return {
        "ticket_id": ticket.id,
        "ticket_number": ticket.ticket_number,
        "suggested_reply": result["suggested_reply"],
        "model": result["model"],
        "context_comment_count": result["context_comment_count"],
        "requires_human_review": True,
    }
