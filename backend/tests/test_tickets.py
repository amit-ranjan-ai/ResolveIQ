import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models
from app.core.config import settings
from app.core.jwt import create_access_token
from app.db.base import Base
from app.db.dependencies import get_db
from app.main import app
from app.models.organisation import Organisation
from app.models.organisation_membership import OrganisationMembership
from app.models.sla_policy import SLAPolicy
from app.models.team import Team
from app.models.team_membership import TeamMembership
from app.models.ticket import Ticket
from app.models.ticket_activity import TicketActivity
from app.models.ticket_sla import TicketSLA
from app.models.user import User


@pytest.fixture
def db_session_factory():
    test_engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(bind=test_engine)

    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
    )

    def override_get_db():
        db = TestingSessionLocal()

        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    yield TestingSessionLocal

    app.dependency_overrides.clear()
    test_engine.dispose()


@pytest.fixture
def client(db_session_factory):
    with TestClient(app) as test_client:
        yield test_client


def create_ticket_context(
    db_session_factory,
    role="OWNER",
    organisation_status="ACTIVE",
    requester_active=True,
):
    with db_session_factory() as db:
        organisation = Organisation(
            name="Test Organisation",
            slug=f"test-organisation-{uuid.uuid4().hex[:8]}",
            status=organisation_status,
        )

        db.add(organisation)
        db.flush()
        default_sla_policies = [
            ("P1", 15, 240),
            ("P2", 30, 480),
            ("P3", 240, 1440),
            ("P4", 480, 4320),
        ]

        for priority, response_minutes, resolution_minutes in default_sla_policies:
            db.add(
                SLAPolicy(
                    organisation_id=organisation.id,
                    priority=priority,
                    first_response_minutes=response_minutes,
                    resolution_minutes=resolution_minutes,
                )
            )

        db.flush()

        caller = User(
            full_name="Test Caller",
            email=f"caller-{uuid.uuid4()}@example.com",
            password_hash="test-password-hash",
        )

        db.add(caller)
        db.flush()

        caller_membership = OrganisationMembership(
            organisation_id=organisation.id,
            user_id=caller.id,
            role=role,
            is_active=True,
        )

        db.add(caller_membership)
        db.flush()

        if role == "REQUESTER":
            requester_membership = caller_membership
        else:
            requester = User(
                full_name="Test Requester",
                email=f"requester-{uuid.uuid4()}@example.com",
                password_hash="test-password-hash",
            )

            db.add(requester)
            db.flush()

            requester_membership = OrganisationMembership(
                organisation_id=organisation.id,
                user_id=requester.id,
                role="REQUESTER",
                is_active=requester_active,
            )

            db.add(requester_membership)

        db.commit()

        access_token = create_access_token(str(caller.id))

        return {
            "organisation_id": str(organisation.id),
            "caller_user_id": str(caller.id),
            "caller_membership_id": str(caller_membership.id),
            "requester_membership_id": str(requester_membership.id),
            "requester_user_id": str(requester_membership.user_id),
            "access_token": access_token,
        }


def create_ticket(client, context):
    client.headers.update({"Authorization": f"Bearer {context['access_token']}"})

    return client.post(
        f"/api/v1/organisations/{context['organisation_id']}/tickets",
        json={
            "requester_membership_id": context["requester_membership_id"],
            "subject": "Unable to access application",
            "description": "The application is not opening.",
            "impact": "HIGH",
            "urgency": "HIGH",
            "source": "WEB",
        },
    )


def test_create_ticket_without_authentication(client, db_session_factory):
    context = create_ticket_context(db_session_factory)

    response = client.post(
        f"/api/v1/organisations/{context['organisation_id']}/tickets",
        json={
            "requester_membership_id": context["requester_membership_id"],
            "subject": "Unable to access application",
            "description": "The application is not opening.",
            "impact": "HIGH",
            "urgency": "HIGH",
        },
    )

    assert response.status_code == 401


@pytest.mark.parametrize("role", ["OWNER", "ADMIN", "AGENT"])
def test_create_ticket_for_another_member(
    client,
    db_session_factory,
    role,
):
    context = create_ticket_context(
        db_session_factory,
        role=role,
    )

    response = create_ticket(client, context)

    assert response.status_code == 201
    assert (
        response.json()["requester_membership_id"]
        == (context["requester_membership_id"])
    )
    assert response.json()["priority"] == "P1"
    assert response.json()["status"] == "Open"


def test_requester_can_create_own_ticket(client, db_session_factory):
    context = create_ticket_context(
        db_session_factory,
        role="REQUESTER",
    )

    response = create_ticket(client, context)

    print("API ERROR:", response.text)

    assert response.status_code == 201
    assert (
        response.json()["requester_membership_id"] == (context["caller_membership_id"])
    )


def test_requester_cannot_create_ticket_for_another_member(
    client,
    db_session_factory,
):
    context = create_ticket_context(
        db_session_factory,
        role="REQUESTER",
    )

    with db_session_factory() as db:
        another_user = User(
            full_name="Another Requester",
            email=f"another-{uuid.uuid4()}@example.com",
            password_hash="test-password-hash",
        )

        db.add(another_user)
        db.flush()

        another_membership = OrganisationMembership(
            organisation_id=uuid.UUID(context["organisation_id"]),
            user_id=another_user.id,
            role="REQUESTER",
            is_active=True,
        )

        db.add(another_membership)
        db.commit()

        another_membership_id = str(another_membership.id)

    client.headers.update({"Authorization": f"Bearer {context['access_token']}"})

    response = client.post(
        f"/api/v1/organisations/{context['organisation_id']}/tickets",
        json={
            "requester_membership_id": another_membership_id,
            "subject": "Unable to access application",
            "description": "The application is not opening.",
            "impact": "HIGH",
            "urgency": "HIGH",
        },
    )

    assert response.status_code == 403


def test_reject_inactive_requester_membership(
    client,
    db_session_factory,
):
    context = create_ticket_context(
        db_session_factory,
        role="OWNER",
        requester_active=False,
    )

    response = create_ticket(client, context)

    assert response.status_code == 400


@pytest.mark.parametrize("organisation_status", ["INACTIVE", "SUSPENDED"])
def test_reject_ticket_for_inactive_organisation(
    client,
    db_session_factory,
    organisation_status,
):
    context = create_ticket_context(
        db_session_factory,
        role="OWNER",
        organisation_status=organisation_status,
    )

    response = create_ticket(client, context)

    assert response.status_code == 400


def test_calculate_ticket_priority():
    from app.api.v1.tickets import calculate_ticket_priority

    assert calculate_ticket_priority("HIGH", "HIGH") == "P1"
    assert calculate_ticket_priority("HIGH", "MEDIUM") == "P2"
    assert calculate_ticket_priority("MEDIUM", "MEDIUM") == "P3"
    assert calculate_ticket_priority("LOW", "LOW") == "P4"


def create_member(db, organisation_id, role):
    user = User(
        full_name=f"Test {role}",
        email=f"{role.lower()}-{uuid.uuid4()}@example.com",
        password_hash="test-password-hash",
    )
    db.add(user)
    db.flush()

    membership = OrganisationMembership(
        organisation_id=organisation_id,
        user_id=user.id,
        role=role,
        is_active=True,
    )
    db.add(membership)
    db.flush()

    return user, membership


def create_ticket_for_member(
    client,
    context,
    requester_membership_id=None,
    access_token=None,
):
    token = access_token or context["access_token"]

    client.headers.update({"Authorization": f"Bearer {token}"})

    return client.post(
        f"/api/v1/organisations/{context['organisation_id']}/tickets",
        json={
            "requester_membership_id": (
                requester_membership_id or context["requester_membership_id"]
            ),
            "subject": "Test ticket for retrieval",
            "description": "Testing ticket access permissions.",
            "impact": "HIGH",
            "urgency": "HIGH",
            "source": "WEB",
        },
    )


@pytest.mark.parametrize("role", ["OWNER", "ADMIN"])
def test_owner_and_admin_can_view_all_organisation_tickets(
    client,
    db_session_factory,
    role,
):
    context = create_ticket_context(db_session_factory, role=role)

    first = create_ticket_for_member(client, context)
    second = create_ticket_for_member(client, context)

    assert first.status_code == 201
    assert second.status_code == 201

    response = client.get(f"/api/v1/organisations/{context['organisation_id']}/tickets")

    assert response.status_code == 200

    returned_ids = {ticket["id"] for ticket in response.json()}
    assert first.json()["id"] in returned_ids
    assert second.json()["id"] in returned_ids


def test_agent_can_view_direct_and_team_assigned_tickets(
    client,
    db_session_factory,
):
    context = create_ticket_context(db_session_factory)

    with db_session_factory() as db:
        organisation_id = uuid.UUID(context["organisation_id"])

        # FIX: agent_user is needed below to create the access token.
        agent_user, agent_membership = create_member(db, organisation_id, "AGENT")
        _other_agent_user, other_agent_membership = create_member(
            db, organisation_id, "AGENT"
        )

        team = Team(
            organisation_id=organisation_id,
            name="Support Team",
        )
        db.add(team)
        db.flush()

        db.add_all(
            [
                TeamMembership(
                    organisation_id=organisation_id,
                    team_id=team.id,
                    organisation_membership_id=agent_membership.id,
                ),
                TeamMembership(
                    organisation_id=organisation_id,
                    team_id=team.id,
                    organisation_membership_id=other_agent_membership.id,
                ),
            ]
        )
        db.commit()

        agent_token = create_access_token(str(agent_user.id))
        team_id = team.id
        agent_membership_id = agent_membership.id
        other_agent_membership_id = other_agent_membership.id

    direct = create_ticket_for_member(client, context)
    team_ticket = create_ticket_for_member(client, context)

    assert direct.status_code == 201
    assert team_ticket.status_code == 201

    with db_session_factory() as db:
        direct_record = db.get(Ticket, uuid.UUID(direct.json()["id"]))
        direct_record.assigned_agent_membership_id = agent_membership_id

        team_record = db.get(Ticket, uuid.UUID(team_ticket.json()["id"]))
        team_record.assigned_team_id = team_id
        team_record.assigned_agent_membership_id = other_agent_membership_id

        db.commit()

    client.headers.update({"Authorization": f"Bearer {agent_token}"})

    response = client.get(f"/api/v1/organisations/{context['organisation_id']}/tickets")

    assert response.status_code == 200

    returned_ids = {ticket["id"] for ticket in response.json()}
    assert direct.json()["id"] in returned_ids
    assert team_ticket.json()["id"] in returned_ids


def test_agent_cannot_view_unassigned_or_unrelated_tickets(
    client,
    db_session_factory,
):
    context = create_ticket_context(db_session_factory)

    with db_session_factory() as db:
        organisation_id = uuid.UUID(context["organisation_id"])

        agent_user, agent_membership = create_member(
            db,
            organisation_id,
            "AGENT",
        )
        _other_agent_user, other_agent_membership = create_member(
            db, organisation_id, "AGENT"
        )

        team = Team(
            organisation_id=organisation_id,
            name="Agent Team",
        )
        unrelated_team = Team(
            organisation_id=organisation_id,
            name="Unrelated Team",
        )
        db.add_all([team, unrelated_team])
        db.flush()

        db.add(
            TeamMembership(
                organisation_id=organisation_id,
                team_id=team.id,
                organisation_membership_id=agent_membership.id,
            )
        )
        db.commit()

        agent_token = create_access_token(str(agent_user.id))
        other_agent_membership_id = other_agent_membership.id
        unrelated_team_id = unrelated_team.id

    unrelated = create_ticket_for_member(client, context)
    unassigned = create_ticket_for_member(client, context)

    assert unrelated.status_code == 201
    assert unassigned.status_code == 201

    with db_session_factory() as db:
        unrelated_record = db.get(Ticket, uuid.UUID(unrelated.json()["id"]))
        unrelated_record.assigned_agent_membership_id = other_agent_membership_id
        unrelated_record.assigned_team_id = unrelated_team_id
        db.commit()

    client.headers.update({"Authorization": f"Bearer {agent_token}"})

    response = client.get(f"/api/v1/organisations/{context['organisation_id']}/tickets")

    assert response.status_code == 200

    returned_ids = {ticket["id"] for ticket in response.json()}
    assert unrelated.json()["id"] not in returned_ids
    assert unassigned.json()["id"] not in returned_ids


def test_requester_can_view_only_own_tickets(
    client,
    db_session_factory,
):
    context = create_ticket_context(
        db_session_factory,
        role="REQUESTER",
    )

    own_ticket = create_ticket_for_member(client, context)
    assert own_ticket.status_code == 201

    with db_session_factory() as db:
        _another_user, another_membership = create_member(
            db,
            uuid.UUID(context["organisation_id"]),
            "REQUESTER",
        )
        owner_user, _owner_membership = create_member(
            db,
            uuid.UUID(context["organisation_id"]),
            "OWNER",
        )
        db.commit()

        another_membership_id = str(another_membership.id)
        owner_token = create_access_token(str(owner_user.id))

    client.headers.update({"Authorization": f"Bearer {owner_token}"})

    other_ticket = create_ticket_for_member(
        client,
        context,
        requester_membership_id=another_membership_id,
        access_token=owner_token,
    )
    assert other_ticket.status_code == 201

    client.headers.update({"Authorization": f"Bearer {context['access_token']}"})

    response = client.get(f"/api/v1/organisations/{context['organisation_id']}/tickets")

    assert response.status_code == 200

    returned_ids = {ticket["id"] for ticket in response.json()}
    assert own_ticket.json()["id"] in returned_ids
    assert other_ticket.json()["id"] not in returned_ids

    detail_response = client.get(f"/api/v1/tickets/{other_ticket.json()['id']}")
    assert detail_response.status_code == 404


def test_user_cannot_view_another_organisation_tickets(
    client,
    db_session_factory,
):
    first_context = create_ticket_context(db_session_factory)
    second_context = create_ticket_context(db_session_factory)

    second_ticket = create_ticket_for_member(client, second_context)
    assert second_ticket.status_code == 201

    client.headers.update({"Authorization": f"Bearer {first_context['access_token']}"})

    list_response = client.get(
        f"/api/v1/organisations/{second_context['organisation_id']}/tickets"
    )

    detail_response = client.get(f"/api/v1/tickets/{second_ticket.json()['id']}")

    assert list_response.status_code == 403
    assert detail_response.status_code == 403


def test_owner_can_update_ticket_and_recalculate_priority(
    client,
    db_session_factory,
):
    context = create_ticket_context(db_session_factory)
    created = create_ticket(client, context)

    assert created.status_code == 201

    response = client.patch(
        f"/api/v1/tickets/{created.json()['id']}",
        json={
            "subject": "Updated application access issue",
            "impact": "LOW",
            "urgency": "LOW",
        },
    )

    assert response.status_code == 200
    assert response.json()["subject"] == "Updated application access issue"
    assert response.json()["impact"] == "LOW"
    assert response.json()["urgency"] == "LOW"
    assert response.json()["priority"] == "P4"


def test_agent_can_update_assigned_ticket_details(
    client,
    db_session_factory,
):
    context = create_ticket_context(db_session_factory)
    created = create_ticket(client, context)

    assert created.status_code == 201

    with db_session_factory() as db:
        organisation_id = uuid.UUID(context["organisation_id"])
        agent_user, agent_membership = create_member(
            db,
            organisation_id,
            "AGENT",
        )

        ticket = db.get(Ticket, uuid.UUID(created.json()["id"]))
        ticket.assigned_agent_membership_id = agent_membership.id
        db.commit()

        agent_token = create_access_token(str(agent_user.id))

    client.headers.update({"Authorization": f"Bearer {agent_token}"})

    response = client.patch(
        f"/api/v1/tickets/{created.json()['id']}",
        json={"subject": "Agent updated this ticket"},
    )

    assert response.status_code == 200
    assert response.json()["subject"] == "Agent updated this ticket"


def test_agent_cannot_change_ticket_assignments(
    client,
    db_session_factory,
):
    context = create_ticket_context(db_session_factory)
    created = create_ticket(client, context)

    assert created.status_code == 201

    with db_session_factory() as db:
        organisation_id = uuid.UUID(context["organisation_id"])

        agent_user, agent_membership = create_member(
            db,
            organisation_id,
            "AGENT",
        )

        _other_agent_user, other_agent_membership = create_member(
            db,
            organisation_id,
            "AGENT",
        )

        ticket = db.get(Ticket, uuid.UUID(created.json()["id"]))
        ticket.assigned_agent_membership_id = agent_membership.id
        db.commit()

        agent_token = create_access_token(str(agent_user.id))
        other_agent_membership_id = str(other_agent_membership.id)

    client.headers.update({"Authorization": f"Bearer {agent_token}"})

    response = client.patch(
        f"/api/v1/tickets/{created.json()['id']}",
        json={
            "assigned_agent_membership_id": other_agent_membership_id,
        },
    )

    assert response.status_code == 403


def test_requester_cannot_update_ticket(
    client,
    db_session_factory,
):
    context = create_ticket_context(
        db_session_factory,
        role="REQUESTER",
    )
    created = create_ticket(client, context)

    assert created.status_code == 201

    response = client.patch(
        f"/api/v1/tickets/{created.json()['id']}",
        json={"subject": "Requester trying to update ticket"},
    )

    assert response.status_code == 403


def test_agent_cannot_update_unassigned_ticket(
    client,
    db_session_factory,
):
    context = create_ticket_context(db_session_factory)
    created = create_ticket(client, context)

    assert created.status_code == 201

    with db_session_factory() as db:
        agent_user, _agent_membership = create_member(
            db,
            uuid.UUID(context["organisation_id"]),
            "AGENT",
        )
        db.commit()

        agent_token = create_access_token(str(agent_user.id))

    client.headers.update({"Authorization": f"Bearer {agent_token}"})

    response = client.patch(
        f"/api/v1/tickets/{created.json()['id']}",
        json={"subject": "Unauthorized update"},
    )

    assert response.status_code == 404


def test_update_ticket_rejects_empty_payload(
    client,
    db_session_factory,
):
    context = create_ticket_context(db_session_factory)
    created = create_ticket(client, context)

    assert created.status_code == 201

    response = client.patch(
        f"/api/v1/tickets/{created.json()['id']}",
        json={},
    )

    assert response.status_code == 400


@pytest.mark.parametrize("role", ["OWNER", "ADMIN"])
def test_owner_and_admin_can_assign_team_and_agent(
    client,
    db_session_factory,
    role,
):
    context = create_ticket_context(db_session_factory, role=role)
    created = create_ticket(client, context)

    assert created.status_code == 201

    with db_session_factory() as db:
        organisation_id = uuid.UUID(context["organisation_id"])

        _agent_user, agent_membership = create_member(
            db,
            organisation_id,
            "AGENT",
        )

        team = Team(
            organisation_id=organisation_id,
            name="Assignment Support Team",
        )
        db.add(team)
        db.flush()

        db.add(
            TeamMembership(
                organisation_id=organisation_id,
                team_id=team.id,
                organisation_membership_id=agent_membership.id,
            )
        )
        db.commit()

        team_id = str(team.id)
        agent_membership_id = str(agent_membership.id)

    response = client.patch(
        f"/api/v1/tickets/{created.json()['id']}/assignment",
        json={
            "assigned_team_id": team_id,
            "assigned_agent_membership_id": agent_membership_id,
        },
    )

    assert response.status_code == 200
    assert response.json()["assigned_team_id"] == team_id
    assert response.json()["assigned_agent_membership_id"] == agent_membership_id


@pytest.mark.parametrize("role", ["AGENT", "REQUESTER"])
def test_agent_and_requester_cannot_change_ticket_assignments(
    client,
    db_session_factory,
    role,
):
    context = create_ticket_context(db_session_factory, role=role)
    created = create_ticket(client, context)

    assert created.status_code == 201

    response = client.patch(
        f"/api/v1/tickets/{created.json()['id']}/assignment",
        json={"assigned_team_id": None},
    )

    assert response.status_code == 403


def test_assignment_rejects_agent_not_in_selected_team(
    client,
    db_session_factory,
):
    context = create_ticket_context(db_session_factory)
    created = create_ticket(client, context)

    assert created.status_code == 201

    with db_session_factory() as db:
        organisation_id = uuid.UUID(context["organisation_id"])

        # FIX: the user object is not used in this test.
        _agent_user, agent_membership = create_member(
            db,
            organisation_id,
            "AGENT",
        )

        team = Team(
            organisation_id=organisation_id,
            name="Different Support Team",
        )
        db.add(team)
        db.commit()

        team_id = str(team.id)
        agent_membership_id = str(agent_membership.id)

    response = client.patch(
        f"/api/v1/tickets/{created.json()['id']}/assignment",
        json={
            "assigned_team_id": team_id,
            "assigned_agent_membership_id": agent_membership_id,
        },
    )

    assert response.status_code == 400


def test_assignment_rejects_requester_as_agent(
    client,
    db_session_factory,
):
    context = create_ticket_context(db_session_factory)
    created = create_ticket(client, context)

    assert created.status_code == 201

    response = client.patch(
        f"/api/v1/tickets/{created.json()['id']}/assignment",
        json={
            "assigned_agent_membership_id": context["requester_membership_id"],
        },
    )

    assert response.status_code == 400


def test_assignment_rejects_inactive_team(
    client,
    db_session_factory,
):
    context = create_ticket_context(db_session_factory)
    created = create_ticket(client, context)

    assert created.status_code == 201

    with db_session_factory() as db:
        team = Team(
            organisation_id=uuid.UUID(context["organisation_id"]),
            name="Inactive Support Team",
            is_active=False,
        )
        db.add(team)
        db.commit()

        team_id = str(team.id)

    response = client.patch(
        f"/api/v1/tickets/{created.json()['id']}/assignment",
        json={"assigned_team_id": team_id},
    )

    assert response.status_code == 400


def test_assignment_can_clear_team_and_agent(
    client,
    db_session_factory,
):
    context = create_ticket_context(db_session_factory)
    created = create_ticket(client, context)

    assert created.status_code == 201

    with db_session_factory() as db:
        organisation_id = uuid.UUID(context["organisation_id"])

        _agent_user, agent_membership = create_member(
            db,
            organisation_id,
            "AGENT",
        )

        team = Team(
            organisation_id=organisation_id,
            name="Team To Clear",
        )
        db.add(team)
        db.flush()

        db.add(
            TeamMembership(
                organisation_id=organisation_id,
                team_id=team.id,
                organisation_membership_id=agent_membership.id,
            )
        )

        ticket = db.get(Ticket, uuid.UUID(created.json()["id"]))
        ticket.assigned_team_id = team.id
        ticket.assigned_agent_membership_id = agent_membership.id
        db.commit()

    response = client.patch(
        f"/api/v1/tickets/{created.json()['id']}/assignment",
        json={
            "assigned_team_id": None,
            "assigned_agent_membership_id": None,
        },
    )

    assert response.status_code == 200
    assert response.json()["assigned_team_id"] is None
    assert response.json()["assigned_agent_membership_id"] is None


def test_assignment_rejects_empty_payload(
    client,
    db_session_factory,
):
    context = create_ticket_context(db_session_factory)
    created = create_ticket(client, context)

    assert created.status_code == 201

    response = client.patch(
        f"/api/v1/tickets/{created.json()['id']}/assignment",
        json={},
    )

    assert response.status_code == 400


def test_owner_can_create_and_view_ticket_comments(
    client,
    db_session_factory,
):
    context = create_ticket_context(db_session_factory)
    created = create_ticket(client, context)

    assert created.status_code == 201

    ticket_id = created.json()["id"]

    public_response = client.post(
        f"/api/v1/tickets/{ticket_id}/comments",
        json={
            "message": "We are investigating this issue.",
            "is_internal": False,
        },
    )

    assert public_response.status_code == 201
    assert public_response.json()["message"] == ("We are investigating this issue.")
    assert public_response.json()["is_internal"] is False

    internal_response = client.post(
        f"/api/v1/tickets/{ticket_id}/comments",
        json={
            "message": "Internal investigation note.",
            "is_internal": True,
        },
    )

    assert internal_response.status_code == 201
    assert internal_response.json()["is_internal"] is True

    list_response = client.get(f"/api/v1/tickets/{ticket_id}/comments")

    assert list_response.status_code == 200
    assert len(list_response.json()) == 2
    assert list_response.json()[0]["message"] == ("We are investigating this issue.")


def test_public_support_comment_records_first_sla_response(
    client,
    db_session_factory,
):
    context = create_ticket_context(db_session_factory)
    created = create_ticket(client, context)

    assert created.status_code == 201

    ticket_id = uuid.UUID(created.json()["id"])

    response = client.post(
        f"/api/v1/tickets/{ticket_id}/comments",
        json={
            "message": "We are investigating this issue.",
            "is_internal": False,
        },
    )

    assert response.status_code == 201

    with db_session_factory() as db:
        ticket_sla = db.scalar(
            select(TicketSLA).where(
                TicketSLA.ticket_id == ticket_id,
            )
        )

        assert ticket_sla is not None
        assert ticket_sla.first_responded_at is not None


def test_internal_note_does_not_record_first_sla_response(
    client,
    db_session_factory,
):
    context = create_ticket_context(db_session_factory)
    created = create_ticket(client, context)

    assert created.status_code == 201

    ticket_id = uuid.UUID(created.json()["id"])

    response = client.post(
        f"/api/v1/tickets/{ticket_id}/comments",
        json={
            "message": "Internal investigation note.",
            "is_internal": True,
        },
    )

    assert response.status_code == 201

    with db_session_factory() as db:
        ticket_sla = db.scalar(
            select(TicketSLA).where(
                TicketSLA.ticket_id == ticket_id,
            )
        )

        assert ticket_sla is not None
        assert ticket_sla.first_responded_at is None


def test_requester_comment_does_not_record_first_sla_response(
    client,
    db_session_factory,
):
    context = create_ticket_context(
        db_session_factory,
        role="REQUESTER",
    )
    created = create_ticket(client, context)

    assert created.status_code == 201

    ticket_id = uuid.UUID(created.json()["id"])

    response = client.post(
        f"/api/v1/tickets/{ticket_id}/comments",
        json={
            "message": "I am still experiencing this issue.",
            "is_internal": False,
        },
    )

    assert response.status_code == 201

    with db_session_factory() as db:
        ticket_sla = db.scalar(
            select(TicketSLA).where(
                TicketSLA.ticket_id == ticket_id,
            )
        )

        assert ticket_sla is not None
        assert ticket_sla.first_responded_at is None


def test_second_support_comment_does_not_overwrite_first_response(
    client,
    db_session_factory,
):
    context = create_ticket_context(db_session_factory)
    created = create_ticket(client, context)

    assert created.status_code == 201

    ticket_id = uuid.UUID(created.json()["id"])

    first_response = client.post(
        f"/api/v1/tickets/{ticket_id}/comments",
        json={
            "message": "First support response.",
            "is_internal": False,
        },
    )

    assert first_response.status_code == 201

    with db_session_factory() as db:
        ticket_sla = db.scalar(
            select(TicketSLA).where(
                TicketSLA.ticket_id == ticket_id,
            )
        )
        original_timestamp = ticket_sla.first_responded_at

    second_response = client.post(
        f"/api/v1/tickets/{ticket_id}/comments",
        json={
            "message": "Second support response.",
            "is_internal": False,
        },
    )

    assert second_response.status_code == 201

    with db_session_factory() as db:
        ticket_sla = db.scalar(
            select(TicketSLA).where(
                TicketSLA.ticket_id == ticket_id,
            )
        )

        assert ticket_sla.first_responded_at == original_timestamp


def test_requester_can_only_view_public_ticket_comments(
    client,
    db_session_factory,
):
    context = create_ticket_context(
        db_session_factory,
        role="REQUESTER",
    )

    created = create_ticket(client, context)
    assert created.status_code == 201

    ticket_id = created.json()["id"]

    public_response = client.post(
        f"/api/v1/tickets/{ticket_id}/comments",
        json={
            "message": "I am still experiencing this issue.",
            "is_internal": False,
        },
    )

    assert public_response.status_code == 201

    internal_response = client.post(
        f"/api/v1/tickets/{ticket_id}/comments",
        json={
            "message": "This should not be allowed.",
            "is_internal": True,
        },
    )

    assert internal_response.status_code == 403

    list_response = client.get(f"/api/v1/tickets/{ticket_id}/comments")

    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["message"] == ("I am still experiencing this issue.")
    assert list_response.json()[0]["is_internal"] is False


def test_agent_can_comment_on_assigned_ticket(
    client,
    db_session_factory,
):
    context = create_ticket_context(db_session_factory)
    created = create_ticket(client, context)

    assert created.status_code == 201

    ticket_id = created.json()["id"]

    with db_session_factory() as db:
        agent_user, agent_membership = create_member(
            db,
            uuid.UUID(context["organisation_id"]),
            "AGENT",
        )

        ticket = db.get(Ticket, uuid.UUID(ticket_id))
        ticket.assigned_agent_membership_id = agent_membership.id

        db.commit()

        agent_token = create_access_token(str(agent_user.id))

    client.headers.update({"Authorization": f"Bearer {agent_token}"})

    create_response = client.post(
        f"/api/v1/tickets/{ticket_id}/comments",
        json={
            "message": "I am investigating this ticket.",
            "is_internal": False,
        },
    )

    assert create_response.status_code == 201

    internal_response = client.post(
        f"/api/v1/tickets/{ticket_id}/comments",
        json={
            "message": "Internal technical investigation.",
            "is_internal": True,
        },
    )

    assert internal_response.status_code == 201

    list_response = client.get(f"/api/v1/tickets/{ticket_id}/comments")

    assert list_response.status_code == 200
    assert len(list_response.json()) == 2


def test_agent_cannot_comment_on_unassigned_ticket(
    client,
    db_session_factory,
):
    context = create_ticket_context(db_session_factory)
    created = create_ticket(client, context)

    assert created.status_code == 201

    ticket_id = created.json()["id"]

    with db_session_factory() as db:
        agent_user, _agent_membership = create_member(
            db,
            uuid.UUID(context["organisation_id"]),
            "AGENT",
        )

        db.commit()

        agent_token = create_access_token(str(agent_user.id))

    client.headers.update({"Authorization": f"Bearer {agent_token}"})

    response = client.post(
        f"/api/v1/tickets/{ticket_id}/comments",
        json={
            "message": "Unauthorized comment.",
            "is_internal": False,
        },
    )

    assert response.status_code == 404

    list_response = client.get(f"/api/v1/tickets/{ticket_id}/comments")

    assert list_response.status_code == 404


def test_ticket_comments_require_authentication(
    client,
    db_session_factory,
):
    context = create_ticket_context(db_session_factory)
    created = create_ticket(client, context)

    assert created.status_code == 201

    ticket_id = created.json()["id"]

    client.headers.pop("Authorization", None)

    create_response = client.post(
        f"/api/v1/tickets/{ticket_id}/comments",
        json={
            "message": "Unauthenticated comment.",
            "is_internal": False,
        },
    )

    list_response = client.get(f"/api/v1/tickets/{ticket_id}/comments")

    assert create_response.status_code == 401
    assert list_response.status_code == 401


def test_upload_list_and_download_ticket_attachment(
    client,
    db_session_factory,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(settings, "UPLOAD_DIRECTORY", tmp_path)

    context = create_ticket_context(db_session_factory, role="OWNER")
    ticket_response = create_ticket(client, context)
    assert ticket_response.status_code == 201
    ticket_id = ticket_response.json()["id"]

    file_content = b"ResolveIQ attachment test"

    upload_response = client.post(
        f"/api/v1/tickets/{ticket_id}/attachments",
        headers={"Authorization": f"Bearer {context['access_token']}"},
        files={
            "file": (
                "evidence.txt",
                file_content,
                "text/plain",
            )
        },
    )
    assert upload_response.status_code == 201

    attachment = upload_response.json()

    assert attachment["original_filename"] == "evidence.txt"
    assert attachment["file_size"] == len(file_content)
    assert "storage_path" not in attachment
    assert "stored_filename" not in attachment

    attachment_id = attachment["id"]

    list_response = client.get(
        f"/api/v1/tickets/{ticket_id}/attachments",
        headers={"Authorization": f"Bearer {context['access_token']}"},
    )

    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["id"] == attachment_id

    download_response = client.get(
        f"/api/v1/attachments/{attachment_id}/download",
        headers={"Authorization": f"Bearer {context['access_token']}"},
    )

    assert download_response.status_code == 200
    assert download_response.content == file_content


def test_upload_rejects_invalid_file_type(
    client,
    db_session_factory,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(settings, "UPLOAD_DIRECTORY", tmp_path)

    context = create_ticket_context(db_session_factory, role="OWNER")
    ticket_response = create_ticket(client, context)
    ticket_id = ticket_response.json()["id"]

    response = client.post(
        f"/api/v1/tickets/{ticket_id}/attachments",
        headers={"Authorization": f"Bearer {context['access_token']}"},
        files={
            "file": (
                "malicious.exe",
                b"Invalid executable content",
                "application/octet-stream",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "File type is not allowed."
    assert list(tmp_path.iterdir()) == []


def test_upload_rejects_oversized_file(
    client,
    db_session_factory,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(settings, "UPLOAD_DIRECTORY", tmp_path)
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE", 8)

    context = create_ticket_context(db_session_factory, role="OWNER")
    ticket_response = create_ticket(client, context)
    ticket_id = ticket_response.json()["id"]

    response = client.post(
        f"/api/v1/tickets/{ticket_id}/attachments",
        headers={"Authorization": f"Bearer {context['access_token']}"},
        files={
            "file": (
                "large.txt",
                b"123456789",
                "text/plain",
            )
        },
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "File size cannot exceed 10 MB."
    assert list(tmp_path.iterdir()) == []


def test_ticket_attachments_require_authentication(
    client,
    db_session_factory,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(settings, "UPLOAD_DIRECTORY", tmp_path)

    context = create_ticket_context(db_session_factory, role="OWNER")
    ticket_response = create_ticket(client, context)
    ticket_id = ticket_response.json()["id"]

    upload_response = client.post(
        f"/api/v1/tickets/{ticket_id}/attachments",
        headers={"Authorization": f"Bearer {context['access_token']}"},
        files={
            "file": (
                "evidence.txt",
                b"Authentication test",
                "text/plain",
            )
        },
    )

    assert upload_response.status_code == 201

    attachment_id = upload_response.json()["id"]
    client.headers.pop("Authorization", None)

    upload_unauthenticated = client.post(
        f"/api/v1/tickets/{ticket_id}/attachments",
        files={"file": ("test.txt", b"test", "text/plain")},
    )

    list_unauthenticated = client.get(f"/api/v1/tickets/{ticket_id}/attachments")

    download_unauthenticated = client.get(
        f"/api/v1/attachments/{attachment_id}/download"
    )

    assert upload_unauthenticated.status_code == 401
    assert list_unauthenticated.status_code == 401
    assert download_unauthenticated.status_code == 401


def test_requester_cannot_access_another_requesters_attachments(
    client,
    db_session_factory,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(settings, "UPLOAD_DIRECTORY", tmp_path)

    context = create_ticket_context(
        db_session_factory,
        role="REQUESTER",
    )

    ticket_response = create_ticket(client, context)
    assert ticket_response.status_code == 201

    ticket_id = ticket_response.json()["id"]

    upload_response = client.post(
        f"/api/v1/tickets/{ticket_id}/attachments",
        files={
            "file": (
                "private.txt",
                b"Private requester attachment",
                "text/plain",
            )
        },
    )

    assert upload_response.status_code == 201

    attachment_id = upload_response.json()["id"]

    with db_session_factory() as db:
        another_user, _another_membership = create_member(
            db,
            uuid.UUID(context["organisation_id"]),
            "REQUESTER",
        )
        db.commit()

        another_token = create_access_token(str(another_user.id))

    client.headers.update({"Authorization": f"Bearer {another_token}"})

    list_response = client.get(f"/api/v1/tickets/{ticket_id}/attachments")

    download_response = client.get(f"/api/v1/attachments/{attachment_id}/download")

    assert list_response.status_code == 404
    assert download_response.status_code == 404


def test_agent_cannot_access_unrelated_ticket_attachments(
    client,
    db_session_factory,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(settings, "UPLOAD_DIRECTORY", tmp_path)

    context = create_ticket_context(db_session_factory, role="OWNER")
    ticket_response = create_ticket(client, context)

    assert ticket_response.status_code == 201
    ticket_id = ticket_response.json()["id"]

    upload_response = client.post(
        f"/api/v1/tickets/{ticket_id}/attachments",
        files={
            "file": (
                "restricted.txt",
                b"Restricted attachment",
                "text/plain",
            )
        },
    )

    assert upload_response.status_code == 201
    attachment_id = upload_response.json()["id"]

    with db_session_factory() as db:
        agent_user, _agent_membership = create_member(
            db,
            uuid.UUID(context["organisation_id"]),
            "AGENT",
        )
        db.commit()

        agent_token = create_access_token(str(agent_user.id))

    client.headers.update({"Authorization": f"Bearer {agent_token}"})

    list_response = client.get(f"/api/v1/tickets/{ticket_id}/attachments")

    download_response = client.get(f"/api/v1/attachments/{attachment_id}/download")

    assert list_response.status_code == 404
    assert download_response.status_code == 404


@pytest.mark.parametrize("role", ["OWNER", "ADMIN"])
def test_owner_and_admin_can_access_ticket_attachments(
    client,
    db_session_factory,
    monkeypatch,
    tmp_path,
    role,
):
    monkeypatch.setattr(settings, "UPLOAD_DIRECTORY", tmp_path)

    context = create_ticket_context(db_session_factory, role=role)
    ticket_response = create_ticket(client, context)

    assert ticket_response.status_code == 201
    ticket_id = ticket_response.json()["id"]

    file_content = b"Organisation attachment access test"

    upload_response = client.post(
        f"/api/v1/tickets/{ticket_id}/attachments",
        files={
            "file": (
                "organisation-file.txt",
                file_content,
                "text/plain",
            )
        },
    )

    assert upload_response.status_code == 201
    attachment_id = upload_response.json()["id"]

    list_response = client.get(f"/api/v1/tickets/{ticket_id}/attachments")

    download_response = client.get(f"/api/v1/attachments/{attachment_id}/download")

    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    assert download_response.status_code == 200
    assert download_response.content == file_content


def test_ticket_creation_records_activity(
    client,
    db_session_factory,
):
    context = create_ticket_context(
        db_session_factory,
        role="OWNER",
    )

    response = create_ticket(client, context)

    assert response.status_code == 201

    ticket_data = response.json()
    ticket_id = uuid.UUID(ticket_data["id"])

    with db_session_factory() as db:
        activities = db.scalars(
            select(TicketActivity).where(
                TicketActivity.ticket_id == ticket_id,
            )
        ).all()

        assert len(activities) == 1

        activity = activities[0]

        assert activity.activity_type == "TICKET_CREATED"
        assert activity.organisation_id == uuid.UUID(context["organisation_id"])
        assert activity.actor_membership_id == uuid.UUID(
            context["caller_membership_id"]
        )
        assert activity.description == (
            f"Ticket {ticket_data['ticket_number']} was created."
        )
        assert activity.extra_data["ticket_number"] == (ticket_data["ticket_number"])


def test_get_ticket_activities(
    client,
    db_session_factory,
):
    context = create_ticket_context(
        db_session_factory,
        role="OWNER",
    )

    ticket_response = create_ticket(client, context)

    assert ticket_response.status_code == 201

    ticket_id = ticket_response.json()["id"]

    response = client.get(
        f"/api/v1/tickets/{ticket_id}/activities",
    )

    assert response.status_code == 200

    activities = response.json()

    assert len(activities) == 1
    assert activities[0]["activity_type"] == "TICKET_CREATED"
    assert activities[0]["description"] == (
        f"Ticket {ticket_response.json()['ticket_number']} was created."
    )


def test_requester_can_view_own_ticket_activities(
    client,
    db_session_factory,
):
    context = create_ticket_context(
        db_session_factory,
        role="REQUESTER",
    )

    ticket_response = create_ticket(client, context)

    assert ticket_response.status_code == 201

    ticket_id = ticket_response.json()["id"]

    response = client.get(
        f"/api/v1/tickets/{ticket_id}/activities",
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["activity_type"] == "TICKET_CREATED"


def test_unauthenticated_user_cannot_view_ticket_activities(
    client,
    db_session_factory,
):
    context = create_ticket_context(
        db_session_factory,
    )

    ticket_response = create_ticket(client, context)

    assert ticket_response.status_code == 201

    client.headers.clear()

    response = client.get(
        f"/api/v1/tickets/{ticket_response.json()['id']}/activities",
    )

    assert response.status_code == 401


def test_public_comment_records_ticket_activity(
    client,
    db_session_factory,
):
    context = create_ticket_context(
        db_session_factory,
        role="OWNER",
    )

    ticket_response = create_ticket(client, context)
    assert ticket_response.status_code == 201

    ticket_id = ticket_response.json()["id"]

    comment_response = client.post(
        f"/api/v1/tickets/{ticket_id}/comments",
        json={
            "message": "Testing public comment activity.",
            "is_internal": False,
        },
    )

    assert comment_response.status_code == 201

    response = client.get(
        f"/api/v1/tickets/{ticket_id}/activities",
    )

    assert response.status_code == 200

    activity_types = [activity["activity_type"] for activity in response.json()]

    assert "TICKET_CREATED" in activity_types
    assert "COMMENT_ADDED" in activity_types


def test_internal_note_records_ticket_activity(
    client,
    db_session_factory,
):
    context = create_ticket_context(
        db_session_factory,
        role="OWNER",
    )

    ticket_response = create_ticket(client, context)
    assert ticket_response.status_code == 201

    ticket_id = ticket_response.json()["id"]

    comment_response = client.post(
        f"/api/v1/tickets/{ticket_id}/comments",
        json={
            "message": "Testing internal note activity.",
            "is_internal": True,
        },
    )

    assert comment_response.status_code == 201

    response = client.get(
        f"/api/v1/tickets/{ticket_id}/activities",
    )

    assert response.status_code == 200

    activity_types = [activity["activity_type"] for activity in response.json()]

    assert "INTERNAL_NOTE_ADDED" in activity_types


def test_requester_cannot_view_internal_note_activity(
    client,
    db_session_factory,
):
    context = create_ticket_context(
        db_session_factory,
        role="OWNER",
    )

    ticket_response = create_ticket(client, context)
    assert ticket_response.status_code == 201

    ticket_id = ticket_response.json()["id"]

    internal_note_response = client.post(
        f"/api/v1/tickets/{ticket_id}/comments",
        json={
            "message": "Confidential internal note.",
            "is_internal": True,
        },
    )

    assert internal_note_response.status_code == 201

    requester_context = create_ticket_context(
        db_session_factory,
        role="REQUESTER",
    )

    client.headers.update(
        {"Authorization": (f"Bearer {requester_context['access_token']}")}
    )

    response = client.get(
        f"/api/v1/tickets/{ticket_id}/activities",
    )

    assert response.status_code == 403


def test_requester_can_view_public_but_not_internal_note_activities(
    client,
    db_session_factory,
):
    context = create_ticket_context(
        db_session_factory,
        role="OWNER",
    )

    ticket_response = create_ticket(client, context)
    assert ticket_response.status_code == 201

    ticket_id = ticket_response.json()["id"]

    # Create a public comment.
    public_response = client.post(
        f"/api/v1/tickets/{ticket_id}/comments",
        json={
            "message": "Public update.",
            "is_internal": False,
        },
    )
    assert public_response.status_code == 201

    # Create an internal note.
    internal_response = client.post(
        f"/api/v1/tickets/{ticket_id}/comments",
        json={
            "message": "Confidential internal note.",
            "is_internal": True,
        },
    )
    assert internal_response.status_code == 201

    # Authenticate as the actual ticket requester.
    with db_session_factory() as db:
        requester = db.get(
            OrganisationMembership,
            uuid.UUID(context["requester_membership_id"]),
        )
        requester_user_id = str(requester.user_id)

    requester_token = create_access_token(requester_user_id)

    client.headers.update({"Authorization": f"Bearer {requester_token}"})

    response = client.get(
        f"/api/v1/tickets/{ticket_id}/activities",
    )

    assert response.status_code == 200

    activities = response.json()

    activity_types = [activity["activity_type"] for activity in activities]

    assert "TICKET_CREATED" in activity_types
    assert "COMMENT_ADDED" in activity_types
    assert "INTERNAL_NOTE_ADDED" not in activity_types

    descriptions = [activity["description"] for activity in activities]

    assert "Confidential internal note." not in descriptions


def test_attachment_upload_records_ticket_activity(
    client,
    db_session_factory,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(settings, "UPLOAD_DIRECTORY", tmp_path)

    context = create_ticket_context(db_session_factory, role="OWNER")
    ticket_response = create_ticket(client, context)
    assert ticket_response.status_code == 201

    ticket_id = ticket_response.json()["id"]

    upload_response = client.post(
        f"/api/v1/tickets/{ticket_id}/attachments",
        headers={"Authorization": f"Bearer {context['access_token']}"},
        files={
            "file": (
                "evidence.txt",
                b"ResolveIQ attachment test",
                "text/plain",
            )
        },
    )

    assert upload_response.status_code == 201

    activity_response = client.get(
        f"/api/v1/tickets/{ticket_id}/activities",
        headers={"Authorization": f"Bearer {context['access_token']}"},
    )

    assert activity_response.status_code == 200

    activities = activity_response.json()

    attachment_activity = next(
        (
            activity
            for activity in activities
            if activity["activity_type"] == "ATTACHMENT_UPLOADED"
        ),
        None,
    )

    assert attachment_activity is not None
    assert attachment_activity["description"] == "An attachment was uploaded."
    assert attachment_activity["extra_data"]["filename"] == "evidence.txt"
    assert attachment_activity["extra_data"]["file_size"] == len(
        b"ResolveIQ attachment test"
    )


def test_priority_change_records_ticket_activity(
    client,
    db_session_factory,
):
    context = create_ticket_context(db_session_factory)
    created = create_ticket(client, context)

    assert created.status_code == 201

    ticket_id = created.json()["id"]

    response = client.patch(
        f"/api/v1/tickets/{ticket_id}",
        json={"impact": "LOW"},
    )

    assert response.status_code == 200

    activity_response = client.get(
        f"/api/v1/tickets/{ticket_id}/activities",
    )

    assert activity_response.status_code == 200

    activities = activity_response.json()

    priority_activity = next(
        (
            activity
            for activity in activities
            if activity["activity_type"] == "PRIORITY_CHANGED"
        ),
        None,
    )

    assert priority_activity is not None
    assert priority_activity["old_value"] != priority_activity["new_value"]


def test_assignment_change_records_ticket_activity(
    client,
    db_session_factory,
):
    context = create_ticket_context(db_session_factory, role="OWNER")
    created = create_ticket(client, context)

    assert created.status_code == 201
    ticket_id = created.json()["id"]

    with db_session_factory() as db:
        organisation_id = uuid.UUID(context["organisation_id"])

        _agent_user, agent_membership = create_member(
            db,
            organisation_id,
            "AGENT",
        )

        team = Team(
            organisation_id=organisation_id,
            name="Activity Test Team",
        )
        db.add(team)
        db.flush()

        db.add(
            TeamMembership(
                organisation_id=organisation_id,
                team_id=team.id,
                organisation_membership_id=agent_membership.id,
            )
        )
        db.commit()

        team_id = str(team.id)
        agent_membership_id = str(agent_membership.id)

    response = client.patch(
        f"/api/v1/tickets/{ticket_id}/assignment",
        headers={"Authorization": f"Bearer {context['access_token']}"},
        json={
            "assigned_team_id": team_id,
            "assigned_agent_membership_id": agent_membership_id,
        },
    )

    assert response.status_code == 200

    activity_response = client.get(
        f"/api/v1/tickets/{ticket_id}/activities",
        headers={"Authorization": f"Bearer {context['access_token']}"},
    )

    assert activity_response.status_code == 200

    activities = activity_response.json()

    assignment_activity = next(
        (
            activity
            for activity in activities
            if activity["activity_type"] == "ASSIGNMENT_CHANGED"
        ),
        None,
    )

    assert assignment_activity is not None
    assert assignment_activity["description"] == ("Ticket assignment was updated.")


def test_status_change_records_ticket_activity(
    client,
    db_session_factory,
):
    context = create_ticket_context(db_session_factory)
    created = create_ticket(client, context)

    assert created.status_code == 201

    ticket_id = created.json()["id"]

    response = client.patch(
        f"/api/v1/tickets/{ticket_id}",
        headers={"Authorization": f"Bearer {context['access_token']}"},
        json={"status": "In Progress"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "In Progress"

    activity_response = client.get(
        f"/api/v1/tickets/{ticket_id}/activities",
        headers={"Authorization": f"Bearer {context['access_token']}"},
    )

    assert activity_response.status_code == 200

    activities = activity_response.json()

    status_activity = next(
        (
            activity
            for activity in activities
            if activity["activity_type"] == "STATUS_CHANGED"
        ),
        None,
    )

    assert status_activity is not None
    assert status_activity["old_value"] == "Open"
    assert status_activity["new_value"] == "In Progress"


def test_resolving_ticket_sets_resolved_at(
    client,
    db_session_factory,
):
    context = create_ticket_context(db_session_factory)
    created = create_ticket(client, context)

    assert created.status_code == 201

    ticket_id = created.json()["id"]

    response = client.patch(
        f"/api/v1/tickets/{ticket_id}",
        headers={"Authorization": f"Bearer {context['access_token']}"},
        json={"status": "Resolved"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "Resolved"
    assert response.json()["resolved_at"] is not None
    assert response.json()["closed_at"] is None

    with db_session_factory() as db:
        ticket_sla = db.scalar(
            select(TicketSLA).where(TicketSLA.ticket_id == uuid.UUID(ticket_id))
        )

        assert ticket_sla is not None
        assert ticket_sla.resolved_at is not None


def test_closing_ticket_sets_closed_at(
    client,
    db_session_factory,
):
    context = create_ticket_context(db_session_factory)
    created = create_ticket(client, context)

    assert created.status_code == 201

    ticket_id = created.json()["id"]

    response = client.patch(
        f"/api/v1/tickets/{ticket_id}",
        headers={"Authorization": f"Bearer {context['access_token']}"},
        json={"status": "Closed"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "Closed"
    assert response.json()["closed_at"] is not None
    assert response.json()["resolved_at"] is None

    with db_session_factory() as db:
        ticket_sla = db.scalar(
            select(TicketSLA).where(TicketSLA.ticket_id == uuid.UUID(ticket_id))
        )

        assert ticket_sla is not None
        assert ticket_sla.resolved_at is not None


def test_reopening_ticket_clears_resolution_timestamps(
    client,
    db_session_factory,
):
    context = create_ticket_context(db_session_factory)
    created = create_ticket(client, context)

    assert created.status_code == 201

    ticket_id = created.json()["id"]
    headers = {"Authorization": f"Bearer {context['access_token']}"}

    resolved_response = client.patch(
        f"/api/v1/tickets/{ticket_id}",
        headers=headers,
        json={"status": "Resolved"},
    )

    assert resolved_response.status_code == 200
    assert resolved_response.json()["resolved_at"] is not None

    reopened_response = client.patch(
        f"/api/v1/tickets/{ticket_id}",
        headers=headers,
        json={"status": "Reopened"},
    )

    assert reopened_response.status_code == 200
    assert reopened_response.json()["status"] == "Reopened"
    assert reopened_response.json()["resolved_at"] is None
    assert reopened_response.json()["closed_at"] is None

    with db_session_factory() as db:
        ticket_sla = db.scalar(
            select(TicketSLA).where(TicketSLA.ticket_id == uuid.UUID(ticket_id))
        )

        assert ticket_sla is not None
        assert ticket_sla.resolved_at is None


def test_get_ticket_sla_monitoring(client, db_session_factory):
    context = create_ticket_context(db_session_factory)

    ticket_response = create_ticket(client, context)

    assert ticket_response.status_code == 201

    ticket_id = ticket_response.json()["id"]

    response = client.get(f"/api/v1/tickets/{ticket_id}/sla")

    assert response.status_code == 200

    data = response.json()

    assert data["ticket_id"] == ticket_id
    assert data["organisation_id"] == context["organisation_id"]
    assert data["ticket_priority"] == "P1"
    assert data["response_status"] == "ON_TRACK"
    assert data["resolution_status"] == "ON_TRACK"
    assert data["response_breached"] is False
    assert data["resolution_breached"] is False


def test_user_cannot_access_another_organisations_ticket_sla(
    client,
    db_session_factory,
):
    first_context = create_ticket_context(db_session_factory)
    first_ticket = create_ticket(client, first_context)

    assert first_ticket.status_code == 201
    ticket_id = first_ticket.json()["id"]

    second_context = create_ticket_context(db_session_factory)

    client.headers.update({"Authorization": f"Bearer {second_context['access_token']}"})

    response = client.get(f"/api/v1/tickets/{ticket_id}/sla")

    assert response.status_code == 403


def test_owner_can_list_sla_policies(client, db_session_factory):
    context = create_ticket_context(db_session_factory)

    response = client.get(
        f"/api/v1/organisations/{context['organisation_id']}/sla-policies",
        headers={"Authorization": f"Bearer {context['access_token']}"},
    )

    assert response.status_code == 200
    assert len(response.json()) == 4

    priorities = [policy["priority"] for policy in response.json()]
    assert priorities == ["P1", "P2", "P3", "P4"]


def test_admin_can_update_sla_policy(client, db_session_factory):
    context = create_ticket_context(db_session_factory, role="ADMIN")

    response = client.patch(
        f"/api/v1/organisations/{context['organisation_id']}/sla-policies/P1",
        headers={"Authorization": f"Bearer {context['access_token']}"},
        json={
            "first_response_minutes": 10,
            "resolution_minutes": 120,
        },
    )

    assert response.status_code == 200
    assert response.json()["priority"] == "P1"
    assert response.json()["first_response_minutes"] == 10
    assert response.json()["resolution_minutes"] == 120


@pytest.mark.parametrize("role", ["AGENT", "REQUESTER"])
def test_agent_and_requester_cannot_manage_sla_policies(
    client,
    db_session_factory,
    role,
):
    context = create_ticket_context(db_session_factory, role=role)

    response = client.get(
        f"/api/v1/organisations/{context['organisation_id']}/sla-policies",
        headers={"Authorization": f"Bearer {context['access_token']}"},
    )

    assert response.status_code == 403


@pytest.mark.parametrize(
    "response_minutes,resolution_minutes",
    [
        (0, 60),
        (60, 0),
        (-5, 60),
        (60, -10),
    ],
)
def test_sla_policy_rejects_non_positive_targets(
    client,
    db_session_factory,
    response_minutes,
    resolution_minutes,
):
    context = create_ticket_context(db_session_factory)

    response = client.patch(
        f"/api/v1/organisations/{context['organisation_id']}/sla-policies/P1",
        headers={"Authorization": f"Bearer {context['access_token']}"},
        json={
            "first_response_minutes": response_minutes,
            "resolution_minutes": resolution_minutes,
        },
    )

    assert response.status_code == 422


def test_updating_sla_policy_does_not_change_existing_ticket_deadlines(
    client,
    db_session_factory,
):
    context = create_ticket_context(db_session_factory)

    ticket_response = create_ticket(client, context)
    assert ticket_response.status_code == 201

    ticket_id = ticket_response.json()["id"]

    with db_session_factory() as db:
        ticket_sla = db.scalar(
            select(TicketSLA).where(TicketSLA.ticket_id == uuid.UUID(ticket_id))
        )

        original_response_due_at = ticket_sla.response_due_at
        original_resolution_due_at = ticket_sla.resolution_due_at

    update_response = client.patch(
        f"/api/v1/organisations/{context['organisation_id']}/sla-policies/P1",
        json={
            "first_response_minutes": 5,
            "resolution_minutes": 60,
        },
    )

    assert update_response.status_code == 200

    with db_session_factory() as db:
        updated_ticket_sla = db.scalar(
            select(TicketSLA).where(TicketSLA.ticket_id == uuid.UUID(ticket_id))
        )

        assert updated_ticket_sla.response_due_at == original_response_due_at
        assert updated_ticket_sla.resolution_due_at == original_resolution_due_at
