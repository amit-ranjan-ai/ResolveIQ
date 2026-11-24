import uuid
from datetime import UTC, datetime, timedelta

from app.models.ticket import Ticket
from app.models.ticket_sla import TicketSLA
from app.services.sla_monitoring import (
    evaluate_sla_target,
    monitor_ticket_sla,
)


def test_sla_status_is_on_track():
    now = datetime(2026, 11, 24, 12, 0, tzinfo=UTC)
    due_at = now + timedelta(minutes=100)

    status, remaining, breached = evaluate_sla_target(due_at, None, now, 120)

    assert status == "ON_TRACK"
    assert remaining == 6000
    assert breached is False


def test_sla_status_is_at_risk():
    now = datetime(2026, 11, 24, 12, 0, tzinfo=UTC)
    due_at = now + timedelta(minutes=20)

    status, remaining, breached = evaluate_sla_target(due_at, None, now, 120)

    assert status == "AT_RISK"
    assert remaining == 1200
    assert breached is False


def test_sla_status_is_breached_after_deadline():
    now = datetime(2026, 11, 24, 12, 0, tzinfo=UTC)
    due_at = now - timedelta(minutes=5)

    status, remaining, breached = evaluate_sla_target(due_at, None, now, 120)

    assert status == "BREACHED"
    assert remaining == -300
    assert breached is True


def test_sla_status_is_met_when_completed_before_deadline():
    now = datetime(2026, 11, 24, 12, 0, tzinfo=UTC)
    due_at = now + timedelta(minutes=30)
    completed_at = now

    status, remaining, breached = evaluate_sla_target(due_at, completed_at, now, 120)

    assert status == "MET"
    assert remaining == 1800
    assert breached is False


def test_sla_status_is_breached_when_completed_after_deadline():
    now = datetime(2026, 11, 24, 12, 0, tzinfo=UTC)
    due_at = now - timedelta(minutes=10)
    completed_at = now

    status, remaining, breached = evaluate_sla_target(due_at, completed_at, now, 120)

    assert status == "BREACHED"
    assert remaining == -600
    assert breached is True


def test_sla_status_is_breached_less_than_one_second_after_deadline():
    now = datetime(2026, 11, 24, 12, 0, 0, 500000, tzinfo=UTC)
    due_at = datetime(2026, 11, 24, 12, 0, 0, tzinfo=UTC)

    status, remaining, breached = evaluate_sla_target(due_at, None, now, 120)

    assert status == "BREACHED"
    assert remaining == -1
    assert breached is True


def test_monitor_ticket_sla_returns_correct_statuses():
    now = datetime(2026, 11, 24, 12, 0, tzinfo=UTC)

    ticket = Ticket(
        id=uuid.uuid4(),
        organisation_id=uuid.uuid4(),
        priority="P2",
        status="In Progress",
    )

    ticket_sla = TicketSLA(
        response_due_at=now + timedelta(minutes=5),
        resolution_due_at=now + timedelta(hours=4),
        first_response_minutes=30,
        resolution_minutes=480,
        first_responded_at=None,
        resolved_at=None,
    )

    result = monitor_ticket_sla(
        ticket=ticket,
        ticket_sla=ticket_sla,
        current_time=now,
    )

    assert result.response_status == "AT_RISK"
    assert result.resolution_status == "ON_TRACK"
    assert result.response_remaining_seconds == 300
    assert result.resolution_remaining_seconds == 14400
    assert result.response_breached is False
    assert result.resolution_breached is False
