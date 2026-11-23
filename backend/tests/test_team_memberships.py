import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models
from app.db.base import Base
from app.db.dependencies import get_db
from app.main import app
from app.models.organisation import Organisation
from app.models.organisation_membership import OrganisationMembership
from app.models.team import Team
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


def create_test_context(
    db_session_factory,
    organisation_status="ACTIVE",
    membership_active=True,
    team_active=True,
):
    with db_session_factory() as db:
        organisation = Organisation(
            name="Test Organisation",
            slug="test-organisation",
            status=organisation_status,
        )

        db.add(organisation)
        db.flush()

        user = User(
            full_name="Test Agent",
            email="agent@example.com",
            password_hash="test-password-hash",
        )

        db.add(user)
        db.flush()

        organisation_membership = OrganisationMembership(
            organisation_id=organisation.id,
            user_id=user.id,
            role="AGENT",
            is_active=membership_active,
        )

        db.add(organisation_membership)

        team = Team(
            organisation_id=organisation.id,
            name="Support Team",
            is_active=team_active,
        )

        db.add(team)
        db.commit()

        return {
            "organisation_id": organisation.id,
            "organisation_membership_id": organisation_membership.id,
            "team_id": team.id,
        }


def test_add_team_member(client, db_session_factory):
    context = create_test_context(db_session_factory)

    response = client.post(
        f"/api/v1/teams/{context['team_id']}/members",
        json={"organisation_membership_id": str(context["organisation_membership_id"])},
    )

    assert response.status_code == 201
    assert response.json()["team_id"] == str(context["team_id"])
    assert response.json()["organisation_membership_id"] == str(
        context["organisation_membership_id"]
    )


def test_add_duplicate_team_member(client, db_session_factory):
    context = create_test_context(db_session_factory)

    payload = {"organisation_membership_id": str(context["organisation_membership_id"])}

    first_response = client.post(
        f"/api/v1/teams/{context['team_id']}/members",
        json=payload,
    )

    second_response = client.post(
        f"/api/v1/teams/{context['team_id']}/members",
        json=payload,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_get_team_members(client, db_session_factory):
    context = create_test_context(db_session_factory)

    client.post(
        f"/api/v1/teams/{context['team_id']}/members",
        json={"organisation_membership_id": str(context["organisation_membership_id"])},
    )

    response = client.get(f"/api/v1/teams/{context['team_id']}/members")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["organisation_membership_id"] == str(
        context["organisation_membership_id"]
    )


def test_remove_team_member(client, db_session_factory):
    context = create_test_context(db_session_factory)

    client.post(
        f"/api/v1/teams/{context['team_id']}/members",
        json={"organisation_membership_id": str(context["organisation_membership_id"])},
    )

    response = client.delete(
        f"/api/v1/teams/{context['team_id']}/members/"
        f"{context['organisation_membership_id']}"
    )

    assert response.status_code == 204

    list_response = client.get(f"/api/v1/teams/{context['team_id']}/members")

    assert list_response.status_code == 200
    assert list_response.json() == []


def test_add_inactive_organisation_member(client, db_session_factory):
    context = create_test_context(
        db_session_factory,
        membership_active=False,
    )

    response = client.post(
        f"/api/v1/teams/{context['team_id']}/members",
        json={"organisation_membership_id": str(context["organisation_membership_id"])},
    )

    assert response.status_code == 400


def test_add_member_to_inactive_team(client, db_session_factory):
    context = create_test_context(
        db_session_factory,
        team_active=False,
    )

    response = client.post(
        f"/api/v1/teams/{context['team_id']}/members",
        json={"organisation_membership_id": str(context["organisation_membership_id"])},
    )

    assert response.status_code == 400


@pytest.mark.parametrize(
    "organisation_status",
    ["INACTIVE", "SUSPENDED"],
)
def test_add_member_to_inactive_organisation(
    client,
    db_session_factory,
    organisation_status,
):
    context = create_test_context(
        db_session_factory,
        organisation_status=organisation_status,
    )

    response = client.post(
        f"/api/v1/teams/{context['team_id']}/members",
        json={"organisation_membership_id": str(context["organisation_membership_id"])},
    )

    assert response.status_code == 400


def test_add_member_from_another_organisation(
    client,
    db_session_factory,
):
    context = create_test_context(db_session_factory)

    other_context = create_test_context_for_other_organisation(db_session_factory)

    response = client.post(
        f"/api/v1/teams/{context['team_id']}/members",
        json={
            "organisation_membership_id": str(
                other_context["organisation_membership_id"]
            )
        },
    )

    assert response.status_code == 404


def create_test_context_for_other_organisation(db_session_factory):
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
            email="another-agent@example.com",
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


def test_remove_member_from_inactive_organisation(
    client,
    db_session_factory,
):
    context = create_test_context(db_session_factory)

    client.post(
        f"/api/v1/teams/{context['team_id']}/members",
        json={"organisation_membership_id": str(context["organisation_membership_id"])},
    )

    with db_session_factory() as db:
        organisation = db.get(
            Organisation,
            context["organisation_id"],
        )
        organisation.status = "INACTIVE"
        db.commit()

    response = client.delete(
        f"/api/v1/teams/{context['team_id']}/members/"
        f"{context['organisation_membership_id']}"
    )

    assert response.status_code == 400
