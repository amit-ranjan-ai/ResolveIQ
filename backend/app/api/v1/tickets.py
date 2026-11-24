from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.authorization import (
    check_membership_roles,
    require_organisation_roles,
)
from app.core.dependencies import get_current_user
from app.db.dependencies import get_db
from app.models.category import Category
from app.models.organisation import Organisation
from app.models.organisation_membership import OrganisationMembership
from app.models.team import Team
from app.models.team_membership import TeamMembership
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.ticket import (
    TicketAssignmentUpdate,
    TicketCreate,
    TicketResponse,
    TicketUpdate,
)
from app.services.ticket_activity import record_ticket_activity

router = APIRouter(
    tags=["Tickets"],
)


def get_active_organisation(
    organisation_id: UUID,
    db: Session,
) -> Organisation:
    organisation = db.get(Organisation, organisation_id)

    if organisation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organisation not found.",
        )

    if organisation.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tickets cannot be created for an inactive or suspended organisation.",
        )

    return organisation


def get_active_requester_membership(
    organisation_id: UUID,
    membership_id: UUID,
    db: Session,
) -> OrganisationMembership:
    membership = db.get(OrganisationMembership, membership_id)

    if membership is None or membership.organisation_id != organisation_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requester membership not found in this organisation.",
        )

    if not membership.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive organisation members cannot create tickets.",
        )

    user = db.get(User, membership.user_id)

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The requester user account is inactive.",
        )

    return membership


def validate_ticket_category(
    organisation_id: UUID,
    category_id: UUID | None,
    db: Session,
) -> None:
    if category_id is None:
        return

    category = db.get(Category, category_id)

    if category is None or category.organisation_id != organisation_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found in this organisation.",
        )

    if not category.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive categories cannot be assigned to tickets.",
        )


def calculate_ticket_priority(
    impact: str,
    urgency: str,
) -> str:
    priority_matrix = {
        ("HIGH", "HIGH"): "P1",
        ("HIGH", "MEDIUM"): "P2",
        ("HIGH", "LOW"): "P2",
        ("MEDIUM", "HIGH"): "P2",
        ("MEDIUM", "MEDIUM"): "P3",
        ("MEDIUM", "LOW"): "P3",
        ("LOW", "HIGH"): "P3",
        ("LOW", "MEDIUM"): "P4",
        ("LOW", "LOW"): "P4",
    }

    return priority_matrix[(impact, urgency)]


def generate_ticket_number() -> str:
    return f"RIQ-{uuid4().hex[:8].upper()}"


def validate_ticket_assignment(
    organisation_id: UUID,
    assigned_team_id: UUID | None,
    assigned_agent_membership_id: UUID | None,
    db: Session,
) -> None:
    team = None

    if assigned_team_id is not None:
        team = db.get(Team, assigned_team_id)

        if team is None or team.organisation_id != organisation_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team not found in this organisation.",
            )

        if not team.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tickets cannot be assigned to an inactive team.",
            )

    if assigned_agent_membership_id is not None:
        agent_membership = db.get(
            OrganisationMembership,
            assigned_agent_membership_id,
        )

        if (
            agent_membership is None
            or agent_membership.organisation_id != organisation_id
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent membership not found in this organisation.",
            )

        if not agent_membership.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive members cannot be assigned tickets.",
            )

        if agent_membership.role != "AGENT":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tickets can only be assigned to AGENT members.",
            )

        agent_user = db.get(User, agent_membership.user_id)

        if agent_user is None or not agent_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user accounts cannot be assigned tickets.",
            )

        if team is not None:
            team_membership = db.scalar(
                select(TeamMembership.id).where(
                    TeamMembership.organisation_id == organisation_id,
                    TeamMembership.team_id == team.id,
                    TeamMembership.organisation_membership_id == agent_membership.id,
                )
            )

            if team_membership is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="The assigned agent must belong to the selected team.",
                )


@router.post(
    "/organisations/{organisation_id}/tickets",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Organisation, membership, or category is inactive."},
        401: {"description": "Authentication is required."},
        403: {"description": "User does not have permission to create this ticket."},
        404: {"description": "Organisation, membership, or category not found."},
        409: {
            "description": "Ticket could not be created because of a database conflict."
        },
    },
)
def create_ticket(
    organisation_id: UUID,
    ticket_data: TicketCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
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
    get_active_organisation(organisation_id, db)

    requester_membership = get_active_requester_membership(
        organisation_id,
        ticket_data.requester_membership_id,
        db,
    )

    if (
        current_membership.role == "REQUESTER"
        and requester_membership.user_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requesters can only create tickets for themselves.",
        )

    validate_ticket_category(
        organisation_id,
        ticket_data.category_id,
        db,
    )

    priority = calculate_ticket_priority(
        ticket_data.impact,
        ticket_data.urgency,
    )

    ticket = Ticket(
        organisation_id=organisation_id,
        ticket_number=generate_ticket_number(),
        status="Open",
        priority=priority,
        **ticket_data.model_dump(),
    )

    try:
        db.add(ticket)
        db.flush()

        record_ticket_activity(
            db=db,
            organisation_id=ticket.organisation_id,
            ticket_id=ticket.id,
            actor_membership_id=current_membership.id,
            activity_type="TICKET_CREATED",
            description=f"Ticket {ticket.ticket_number} was created.",
            extra_data={
                "ticket_number": ticket.ticket_number,
                "subject": ticket.subject,
            },
        )

        db.commit()
        db.refresh(ticket)

    except IntegrityError as error:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ticket could not be created because of a database conflict.",
        ) from error

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ticket could not be created because of a database conflict.",
        ) from error

    return ticket


@router.get(
    "/organisations/{organisation_id}/tickets",
    response_model=list[TicketResponse],
)
def get_organisation_tickets(
    organisation_id: UUID,
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
    query = select(Ticket).where(
        Ticket.organisation_id == organisation_id,
    )

    if current_membership.role == "REQUESTER":
        query = query.where(
            Ticket.requester_membership_id == current_membership.id,
        )

    elif current_membership.role == "AGENT":
        team_ids = select(TeamMembership.team_id).where(
            TeamMembership.organisation_membership_id == current_membership.id,
        )

        query = query.where(
            or_(
                Ticket.assigned_agent_membership_id == current_membership.id,
                Ticket.assigned_team_id.in_(team_ids),
            )
        )

    query = query.order_by(Ticket.created_at.desc())

    return db.scalars(query).all()


@router.get(
    "/tickets/{ticket_id}",
    response_model=TicketResponse,
    responses={
        401: {"description": "Authentication is required."},
        403: {"description": "User does not have permission."},
        404: {"description": "Ticket not found or not accessible."},
    },
)
def get_ticket(
    ticket_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    ticket = db.get(Ticket, ticket_id)

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found.",
        )

    current_membership = check_membership_roles(
        ticket.organisation_id,
        current_user,
        db,
        ("OWNER", "ADMIN", "AGENT", "REQUESTER"),
    )

    if current_membership.role == "REQUESTER":
        if ticket.requester_membership_id != current_membership.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found.",
            )

    elif current_membership.role == "AGENT":
        is_assigned_agent = ticket.assigned_agent_membership_id == current_membership.id

        is_team_ticket = False

        if ticket.assigned_team_id is not None:
            team_membership = db.scalar(
                select(TeamMembership.id).where(
                    TeamMembership.team_id == ticket.assigned_team_id,
                    TeamMembership.organisation_membership_id == current_membership.id,
                )
            )

            is_team_ticket = team_membership is not None

        if not is_assigned_agent and not is_team_ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found.",
            )

    return ticket


@router.patch(
    "/tickets/{ticket_id}",
    response_model=TicketResponse,
    responses={
        400: {"description": "Invalid ticket update or inactive organisation."},
        401: {"description": "Authentication is required."},
        403: {"description": "User does not have permission to update this ticket."},
        404: {"description": "Ticket not found or not accessible."},
        409: {"description": "Ticket update caused a database conflict."},
    },
)
def update_ticket(
    ticket_id: UUID,
    ticket_data: TicketUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    ticket = db.get(Ticket, ticket_id)

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found.",
        )

    current_membership = check_membership_roles(
        ticket.organisation_id,
        current_user,
        db,
        ("OWNER", "ADMIN", "AGENT", "REQUESTER"),
    )

    if current_membership.role == "REQUESTER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requesters cannot update tickets.",
        )

    if current_membership.role == "AGENT":
        is_assigned_agent = ticket.assigned_agent_membership_id == current_membership.id

        is_team_ticket = False

        if ticket.assigned_team_id is not None:
            team_membership = db.scalar(
                select(TeamMembership.id).where(
                    TeamMembership.team_id == ticket.assigned_team_id,
                    TeamMembership.organisation_membership_id == current_membership.id,
                )
            )

            is_team_ticket = team_membership is not None

        if not is_assigned_agent and not is_team_ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found.",
            )

    get_active_organisation(ticket.organisation_id, db)

    old_status = ticket.status
    old_priority = ticket.priority

    updates = ticket_data.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided for an update.",
        )

    assignment_fields = {
        "assigned_team_id",
        "assigned_agent_membership_id",
    }

    if current_membership.role == "AGENT" and assignment_fields.intersection(updates):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only OWNER and ADMIN members can change ticket assignments.",
        )

    if "category_id" in updates:
        validate_ticket_category(
            ticket.organisation_id,
            updates["category_id"],
            db,
        )

    if assignment_fields.intersection(updates):
        final_team_id = updates.get(
            "assigned_team_id",
            ticket.assigned_team_id,
        )

        final_agent_id = updates.get(
            "assigned_agent_membership_id",
            ticket.assigned_agent_membership_id,
        )

        validate_ticket_assignment(
            ticket.organisation_id,
            final_team_id,
            final_agent_id,
            db,
        )

    for field, value in updates.items():
        setattr(ticket, field, value)

    if "impact" in updates or "urgency" in updates:
        ticket.priority = calculate_ticket_priority(
            ticket.impact,
            ticket.urgency,
        )

    if "status" in updates and ticket.status != old_status:
        if ticket.status == "Resolved":
            ticket.resolved_at = datetime.now(UTC)
            ticket.closed_at = None

        elif ticket.status == "Closed":
            ticket.closed_at = datetime.now(UTC)

        else:
            ticket.resolved_at = None
            ticket.closed_at = None

    try:
        if ticket.status != old_status:
            record_ticket_activity(
                db=db,
                organisation_id=ticket.organisation_id,
                ticket_id=ticket.id,
                actor_membership_id=current_membership.id,
                activity_type="STATUS_CHANGED",
                description=f"Ticket status changed from {old_status} to {ticket.status}.",
                old_value=str(old_status),
                new_value=str(ticket.status),
            )

        if ticket.priority != old_priority:
            record_ticket_activity(
                db=db,
                organisation_id=ticket.organisation_id,
                ticket_id=ticket.id,
                actor_membership_id=current_membership.id,
                activity_type="PRIORITY_CHANGED",
                description=f"Ticket priority changed from {old_priority} to {ticket.priority}.",
                old_value=str(old_priority),
                new_value=str(ticket.priority),
            )
        db.commit()
        db.refresh(ticket)

    except IntegrityError as error:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ticket could not be updated because of a database conflict.",
        ) from error

    return ticket


@router.patch(
    "/tickets/{ticket_id}/assignment",
    response_model=TicketResponse,
    responses={
        400: {"description": "Invalid team or agent assignment."},
        401: {"description": "Authentication is required."},
        403: {"description": "Only OWNER and ADMIN can change assignments."},
        404: {"description": "Ticket, team, or agent membership not found."},
        409: {"description": "Assignment caused a database conflict."},
    },
)
def update_ticket_assignment(
    ticket_id: UUID,
    assignment_data: TicketAssignmentUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    ticket = db.get(Ticket, ticket_id)

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found.",
        )

    current_membership = check_membership_roles(
        ticket.organisation_id,
        current_user,
        db,
        ("OWNER", "ADMIN"),
    )

    if current_membership.role not in ("OWNER", "ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only OWNER and ADMIN can change ticket assignments.",
        )

    get_active_organisation(ticket.organisation_id, db)
    old_team_id = ticket.assigned_team_id
    old_agent_id = ticket.assigned_agent_membership_id

    updates = assignment_data.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one assignment field must be provided.",
        )

    final_team_id = updates.get(
        "assigned_team_id",
        ticket.assigned_team_id,
    )

    final_agent_id = updates.get(
        "assigned_agent_membership_id",
        ticket.assigned_agent_membership_id,
    )

    validate_ticket_assignment(
        ticket.organisation_id,
        final_team_id,
        final_agent_id,
        db,
    )

    for field, value in updates.items():
        setattr(ticket, field, value)

    try:
        if (
            ticket.assigned_team_id != old_team_id
            or ticket.assigned_agent_membership_id != old_agent_id
        ):
            record_ticket_activity(
                db=db,
                organisation_id=ticket.organisation_id,
                ticket_id=ticket.id,
                actor_membership_id=current_membership.id,
                activity_type="ASSIGNMENT_CHANGED",
                description="Ticket assignment was updated.",
            )
        db.commit()
        db.refresh(ticket)

    except IntegrityError as error:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ticket assignment could not be updated.",
        ) from error

    return ticket
