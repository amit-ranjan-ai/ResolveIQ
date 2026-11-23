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


def create_team_context(
    db_session_factory,
    role="AGENT",
    organisation_status="ACTIVE",
    membership_active=True,
    team_active=True,
    add_to_team=True,
):
    with db_session_factory() as db:
        organisation = Organisation(
            name="Test Organisation",
            slug="test-organisation",
            status=organisation_status,
        )

        db.add(organisation)
        db.flush()

        # Create an OWNER who will make the API request.
        owner_user = User(
            full_name="Test Owner",
            email=f"owner-{uuid.uuid4()}@example.com",
            password_hash="test-password-hash",
        )

        db.add(owner_user)
        db.flush()

        owner_membership = OrganisationMembership(
            organisation_id=organisation.id,
            user_id=owner_user.id,
            role="OWNER",
            is_active=True,
        )

        db.add(owner_membership)
        db.flush()

        access_token = create_access_token(str(owner_user.id))

        # Create the person being assigned as Team Lead.
        user = User(
            full_name="Test Agent",
            email=f"agent-{uuid.uuid4()}@example.com",
            password_hash="test-password-hash",
        )

        db.add(user)
        db.flush()

        organisation_membership = OrganisationMembership(
            organisation_id=organisation.id,
            user_id=user.id,
            role=role,
            is_active=membership_active,
        )

        db.add(organisation_membership)
        db.flush()

        team = Team(
            organisation_id=organisation.id,
            name="Support Team",
            is_active=team_active,
        )

        db.add(team)
        db.flush()

        if add_to_team:
            team_membership = TeamMembership(
                organisation_id=organisation.id,
                team_id=team.id,
                organisation_membership_id=organisation_membership.id,
            )

            db.add(team_membership)

        db.commit()

        return {
            "organisation_id": organisation.id,
            "organisation_membership_id": organisation_membership.id,
            "team_id": team.id,
            "access_token": access_token,
        }


def assign_team_lead(client, context):
    client.headers.update({"Authorization": f"Bearer {context['access_token']}"})

    return client.patch(
        f"/api/v1/teams/{context['team_id']}/lead",
        json={"organisation_membership_id": str(context["organisation_membership_id"])},
    )


@pytest.mark.parametrize("role", ["OWNER", "ADMIN", "AGENT"])
def test_assign_eligible_team_lead(
    client,
    db_session_factory,
    role,
):
    context = create_team_context(
        db_session_factory,
        role=role,
    )

    response = assign_team_lead(client, context)

    assert response.status_code == 200
    assert response.json()["team_lead_membership_id"] == str(
        context["organisation_membership_id"]
    )


def test_reject_requester_as_team_lead(client, db_session_factory):
    context = create_team_context(
        db_session_factory,
        role="REQUESTER",
    )

    response = assign_team_lead(client, context)

    assert response.status_code == 400


def test_reject_inactive_organisation_membership(
    client,
    db_session_factory,
):
    context = create_team_context(
        db_session_factory,
        membership_active=False,
    )

    response = assign_team_lead(client, context)

    assert response.status_code == 400


def test_reject_member_not_in_team(client, db_session_factory):
    context = create_team_context(
        db_session_factory,
        add_to_team=False,
    )

    response = assign_team_lead(client, context)

    assert response.status_code == 400


def test_reject_inactive_organisation(client, db_session_factory):
    context = create_team_context(
        db_session_factory,
        organisation_status="INACTIVE",
    )

    response = assign_team_lead(client, context)

    assert response.status_code == 400


def test_reject_suspended_organisation(client, db_session_factory):
    context = create_team_context(
        db_session_factory,
        organisation_status="SUSPENDED",
    )

    response = assign_team_lead(client, context)

    assert response.status_code == 400


def test_reject_inactive_team(client, db_session_factory):
    context = create_team_context(
        db_session_factory,
        team_active=False,
    )

    response = assign_team_lead(client, context)

    assert response.status_code == 400


def test_remove_team_lead(client, db_session_factory):
    context = create_team_context(db_session_factory)

    assign_response = assign_team_lead(client, context)

    assert assign_response.status_code == 200

    response = client.patch(
        f"/api/v1/teams/{context['team_id']}/lead",
        json={
            "organisation_membership_id": None,
        },
    )

    assert response.status_code == 200
    assert response.json()["team_lead_membership_id"] is None


def test_reject_member_from_another_organisation(
    client,
    db_session_factory,
):
    context = create_team_context(db_session_factory)

    other_context = create_team_context_for_another_organisation(db_session_factory)

    client.headers.update({"Authorization": f"Bearer {context['access_token']}"})

    response = client.patch(
        f"/api/v1/teams/{context['team_id']}/lead",
        json={
            "organisation_membership_id": str(
                other_context["organisation_membership_id"]
            )
        },
    )

    assert response.status_code == 404


def create_team_context_for_another_organisation(db_session_factory):
    with db_session_factory() as db:
        organisation = Organisation(
            name="Another Organisation",
            slug="another-organisation",
            status="ACTIVE",
        )

        db.add(organisation)
        db.flush()

        user = User(
            full_name="Another Agent",
            email=f"another-agent-{uuid.uuid4()}@example.com",
            password_hash="test-password-hash",
        )

        db.add(user)
        db.flush()

        membership = OrganisationMembership(
            organisation_id=organisation.id,
            user_id=user.id,
            role="AGENT",
            is_active=True,
        )

        db.add(membership)
        db.commit()

        return {
            "organisation_membership_id": membership.id,
        }
