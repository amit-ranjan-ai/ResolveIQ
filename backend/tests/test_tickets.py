import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models
from app.core.jwt import create_access_token
from app.db.base import Base
from app.db.dependencies import get_db
from app.main import app
from app.models.organisation import Organisation
from app.models.organisation_membership import OrganisationMembership
from app.models.team import Team
from app.models.team_membership import TeamMembership
from app.models.ticket import Ticket
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
