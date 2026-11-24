from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.organisation_membership import OrganisationMembership
from app.models.team import Team
from app.models.team_membership import TeamMembership
from app.models.ticket import Ticket
from app.models.ticket_escalation import TicketEscalation
from app.models.ticket_sla import TicketSLA
from app.services.sla_monitoring import monitor_ticket_sla


def get_escalation_recipient(
    ticket: Ticket,
    db: Session,
) -> OrganisationMembership | None:
    """Find the best eligible recipient for a ticket escalation."""

    # 1. Try the assigned team's lead.
    if ticket.assigned_team_id is not None:
        team = db.scalar(
            select(Team).where(
                Team.id == ticket.assigned_team_id,
                Team.organisation_id == ticket.organisation_id,
                Team.is_active.is_(True),
            )
        )

        if team is not None and team.team_lead_membership_id is not None:
            team_lead = db.scalar(
                select(OrganisationMembership).where(
                    OrganisationMembership.id == team.team_lead_membership_id,
                    OrganisationMembership.organisation_id == ticket.organisation_id,
                    OrganisationMembership.is_active.is_(True),
                    OrganisationMembership.role.in_(("OWNER", "ADMIN", "AGENT")),
                )
            )

            if team_lead is not None:
                team_membership = db.scalar(
                    select(TeamMembership).where(
                        TeamMembership.organisation_id == ticket.organisation_id,
                        TeamMembership.team_id == team.id,
                        TeamMembership.organisation_membership_id == team_lead.id,
                    )
                )

                if team_membership is not None:
                    return team_lead

    # 2. Try the assigned agent.
    if ticket.assigned_agent_membership_id is not None:
        assigned_agent = db.scalar(
            select(OrganisationMembership).where(
                OrganisationMembership.id == ticket.assigned_agent_membership_id,
                OrganisationMembership.organisation_id == ticket.organisation_id,
                OrganisationMembership.is_active.is_(True),
                OrganisationMembership.role == "AGENT",
            )
        )

        if assigned_agent is not None:
            return assigned_agent

    # 3. Fall back to an active OWNER, then ADMIN.
    for role in ("OWNER", "ADMIN"):
        administrator = db.scalar(
            select(OrganisationMembership)
            .where(
                OrganisationMembership.organisation_id == ticket.organisation_id,
                OrganisationMembership.is_active.is_(True),
                OrganisationMembership.role == role,
            )
            .order_by(OrganisationMembership.created_at.asc())
        )

        if administrator is not None:
            return administrator

    return None


def get_escalation_targets(
    ticket: Ticket,
    ticket_sla: TicketSLA,
    current_time: datetime,
) -> list[tuple[str, str]]:
    """Return SLA targets that need escalation."""

    monitoring = monitor_ticket_sla(
        ticket=ticket,
        ticket_sla=ticket_sla,
        current_time=current_time,
    )

    targets = []

    if monitoring.response_status in ("AT_RISK", "BREACHED"):
        targets.append(("RESPONSE", monitoring.response_status))

    if monitoring.resolution_status in ("AT_RISK", "BREACHED"):
        targets.append(("RESOLUTION", monitoring.resolution_status))

    return targets


def create_ticket_escalations(
    ticket: Ticket,
    ticket_sla: TicketSLA,
    db: Session,
    current_time: datetime | None = None,
) -> int:
    """Create missing escalation records for a ticket."""

    if current_time is None:
        current_time = datetime.now(UTC)

    targets = get_escalation_targets(
        ticket=ticket,
        ticket_sla=ticket_sla,
        current_time=current_time,
    )

    if not targets:
        return 0

    recipient = get_escalation_recipient(ticket, db)

    if recipient is None:
        return 0

    created_count = 0

    for target_type, escalation_level in targets:
        existing = db.scalar(
            select(TicketEscalation).where(
                TicketEscalation.organisation_id == ticket.organisation_id,
                TicketEscalation.ticket_id == ticket.id,
                TicketEscalation.target_type == target_type,
                TicketEscalation.escalation_level == escalation_level,
            )
        )

        if existing is not None:
            continue

        reason = (
            f"{target_type.title()} SLA for ticket {ticket.ticket_number} "
            f"is {escalation_level.replace('_', ' ').lower()}. "
            f"Ticket priority: {ticket.priority}."
        )

        escalation = TicketEscalation(
            organisation_id=ticket.organisation_id,
            ticket_id=ticket.id,
            recipient_membership_id=recipient.id,
            target_type=target_type,
            escalation_level=escalation_level,
            reason=reason,
            status="PENDING",
        )

        try:
            with db.begin_nested():
                db.add(escalation)
                db.flush()

            created_count += 1

        except IntegrityError:
            existing = db.scalar(
                select(TicketEscalation).where(
                    TicketEscalation.organisation_id == ticket.organisation_id,
                    TicketEscalation.ticket_id == ticket.id,
                    TicketEscalation.target_type == target_type,
                    TicketEscalation.escalation_level == escalation_level,
                )
            )

            if existing is None:
                raise

    return created_count


def process_sla_escalations(
    db: Session,
    current_time: datetime | None = None,
) -> int:
    """Process SLA escalations for all tickets."""

    if current_time is None:
        current_time = datetime.now(UTC)

    ticket_records = db.execute(
        select(Ticket, TicketSLA).join(
            TicketSLA,
            (TicketSLA.ticket_id == Ticket.id)
            & (TicketSLA.organisation_id == Ticket.organisation_id),
        )
    ).all()

    total_created = 0

    try:
        for ticket, ticket_sla in ticket_records:
            created = create_ticket_escalations(
                ticket=ticket,
                ticket_sla=ticket_sla,
                db=db,
                current_time=current_time,
            )

            total_created += created

        db.commit()

    except Exception:
        db.rollback()
        raise

    return total_created
