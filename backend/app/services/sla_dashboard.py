from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ticket import Ticket
from app.models.ticket_sla import TicketSLA
from app.schemas.sla_dashboard import (
    SLADashboardResponse,
    SLAPriorityBreakdown,
    SLATargetSummary,
)
from app.services.sla_monitoring import monitor_ticket_sla

PRIORITIES = ("P1", "P2", "P3", "P4")

STATUSES = ("ON_TRACK", "AT_RISK", "BREACHED", "MET")


def calculate_compliance_percent(summary: SLATargetSummary) -> float:
    """Calculate compliance using completed SLA targets only."""

    completed_targets = summary.met + summary.breached

    if completed_targets == 0:
        return 0.0

    return round((summary.met / completed_targets) * 100, 2)


def build_sla_dashboard(
    organisation_id: UUID,
    db: Session,
    current_time: datetime | None = None,
) -> SLADashboardResponse:
    """Build live SLA dashboard analytics for an organisation."""

    if current_time is None:
        current_time = datetime.now(UTC)

    statement = (
        select(Ticket, TicketSLA)
        .join(
            TicketSLA,
            (TicketSLA.ticket_id == Ticket.id)
            & (TicketSLA.organisation_id == Ticket.organisation_id),
        )
        .where(TicketSLA.organisation_id == organisation_id)
    )

    results = db.execute(statement).all()

    response_summary = SLATargetSummary()
    resolution_summary = SLATargetSummary()

    priority_breakdown = {
        priority: SLAPriorityBreakdown(
            response=SLATargetSummary(),
            resolution=SLATargetSummary(),
        )
        for priority in PRIORITIES
    }

    for ticket, ticket_sla in results:
        monitoring = monitor_ticket_sla(
            ticket=ticket,
            ticket_sla=ticket_sla,
            current_time=current_time,
        )

        priority_summary = priority_breakdown[ticket.priority]

        for status in STATUSES:
            attribute = status.lower()

            if monitoring.response_status == status:
                setattr(
                    response_summary,
                    attribute,
                    getattr(response_summary, attribute) + 1,
                )
                setattr(
                    priority_summary.response,
                    attribute,
                    getattr(priority_summary.response, attribute) + 1,
                )

            if monitoring.resolution_status == status:
                setattr(
                    resolution_summary,
                    attribute,
                    getattr(resolution_summary, attribute) + 1,
                )
                setattr(
                    priority_summary.resolution,
                    attribute,
                    getattr(priority_summary.resolution, attribute) + 1,
                )

        response_summary.total += 1
        resolution_summary.total += 1

        priority_summary.response.total += 1
        priority_summary.resolution.total += 1

    return SLADashboardResponse(
        organisation_id=str(organisation_id),
        total_tickets=len(results),
        response_compliance_percent=calculate_compliance_percent(response_summary),
        resolution_compliance_percent=calculate_compliance_percent(resolution_summary),
        response=response_summary,
        resolution=resolution_summary,
        priority_breakdown=priority_breakdown,
    )
