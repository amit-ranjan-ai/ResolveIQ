import math
from datetime import UTC, datetime

from app.models.ticket import Ticket
from app.models.ticket_sla import TicketSLA
from app.schemas.ticket_sla import TicketSLAMonitorResponse

AT_RISK_THRESHOLD = 0.20


def normalize_datetime(value: datetime) -> datetime:
    """Ensure datetime values are timezone-aware UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)

    return value.astimezone(UTC)


def evaluate_sla_target(
    due_at: datetime,
    completed_at: datetime | None,
    current_time: datetime,
    target_minutes: int,
) -> tuple[str, int, bool]:
    """Calculate SLA status, remaining seconds and breach state."""

    due_at = normalize_datetime(due_at)
    current_time = normalize_datetime(current_time)

    if completed_at is not None:
        completed_at = normalize_datetime(completed_at)
        time_difference = (due_at - completed_at).total_seconds()
        remaining_seconds = math.floor(time_difference)

        if time_difference >= 0:
            return "MET", remaining_seconds, False

        return "BREACHED", remaining_seconds, True

    time_difference = (due_at - current_time).total_seconds()
    remaining_seconds = math.floor(time_difference)

    if time_difference < 0:
        return "BREACHED", remaining_seconds, True

    risk_threshold_seconds = target_minutes * 60 * AT_RISK_THRESHOLD

    if time_difference <= risk_threshold_seconds:
        return "AT_RISK", remaining_seconds, False

    return "ON_TRACK", remaining_seconds, False


def monitor_ticket_sla(
    ticket: Ticket,
    ticket_sla: TicketSLA,
    current_time: datetime | None = None,
) -> TicketSLAMonitorResponse:
    """Build the live SLA monitoring response for a ticket."""

    if current_time is None:
        current_time = datetime.now(UTC)

    response_status, response_remaining, response_breached = evaluate_sla_target(
        due_at=ticket_sla.response_due_at,
        completed_at=ticket_sla.first_responded_at,
        current_time=current_time,
        target_minutes=ticket_sla.first_response_minutes,
    )

    resolution_status, resolution_remaining, resolution_breached = evaluate_sla_target(
        due_at=ticket_sla.resolution_due_at,
        completed_at=ticket_sla.resolved_at,
        current_time=current_time,
        target_minutes=ticket_sla.resolution_minutes,
    )

    return TicketSLAMonitorResponse(
        ticket_id=ticket.id,
        organisation_id=ticket.organisation_id,
        ticket_priority=ticket.priority,
        ticket_status=ticket.status,
        response_due_at=ticket_sla.response_due_at,
        resolution_due_at=ticket_sla.resolution_due_at,
        first_responded_at=ticket_sla.first_responded_at,
        resolved_at=ticket_sla.resolved_at,
        response_status=response_status,
        resolution_status=resolution_status,
        response_remaining_seconds=response_remaining,
        resolution_remaining_seconds=resolution_remaining,
        response_breached=response_breached,
        resolution_breached=resolution_breached,
    )
