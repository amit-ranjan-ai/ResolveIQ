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
from app.models.organisation_membership import OrganisationMembership
from app.models.user import User


@pytest.fixture
def client():
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

    with TestClient(app) as test_client:
        test_client.testing_session_local = TestingSessionLocal
        yield test_client

    app.dependency_overrides.clear()
    test_engine.dispose()


def authenticate_as_owner(client, organisation_id):
    db = client.testing_session_local()

    try:
        user = User(
            full_name="Test Owner",
            email=f"owner-{uuid.uuid4()}@example.com",
            password_hash="test-password-hash",
        )

        db.add(user)
        db.flush()

        membership = OrganisationMembership(
            organisation_id=uuid.UUID(organisation_id),
            user_id=user.id,
            role="OWNER",
            is_active=True,
        )

        db.add(membership)
        db.commit()

        token = create_access_token(str(user.id))

        client.headers.update({"Authorization": f"Bearer {token}"})

    finally:
        db.close()


def create_organisation(client, name="Test Organisation", status="ACTIVE"):
    response = client.post(
        "/api/v1/organisations/",
        json={
            "name": name,
            "slug": name.lower().replace(" ", "-"),
            "status": status,
        },
    )

    assert response.status_code == 201

    organisation = response.json()
    authenticate_as_owner(client, organisation["id"])

    return organisation


def test_create_team(client):
    organisation = create_organisation(client)

    response = client.post(
        f"/api/v1/organisations/{organisation['id']}/teams",
        json={
            "name": "Support Team",
            "description": "Handles customer support tickets.",
        },
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Support Team"
    assert response.json()["organisation_id"] == organisation["id"]
    assert response.json()["is_active"] is True


def test_create_team_with_duplicate_name(client):
    organisation = create_organisation(client)

    url = f"/api/v1/organisations/{organisation['id']}/teams"
    team_data = {
        "name": "Support Team",
        "description": "Customer support.",
    }

    first_response = client.post(url, json=team_data)
    second_response = client.post(url, json=team_data)

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_create_team_for_nonexistent_organisation(client):
    create_organisation(client)

    response = client.post(
        f"/api/v1/organisations/{uuid.uuid4()}/teams",
        json={"name": "Support Team"},
    )

    assert response.status_code == 403


def test_create_team_for_inactive_organisation(client):
    organisation = create_organisation(
        client,
        status="INACTIVE",
    )

    response = client.post(
        f"/api/v1/organisations/{organisation['id']}/teams",
        json={"name": "Support Team"},
    )

    assert response.status_code == 400


def test_create_team_for_suspended_organisation(client):
    organisation = create_organisation(
        client,
        status="SUSPENDED",
    )

    response = client.post(
        f"/api/v1/organisations/{organisation['id']}/teams",
        json={"name": "Support Team"},
    )

    assert response.status_code == 400


def test_get_organisation_teams(client):
    organisation = create_organisation(client)
    url = f"/api/v1/organisations/{organisation['id']}/teams"

    client.post(url, json={"name": "Support Team"})
    client.post(url, json={"name": "Development Team"})

    response = client.get(url)

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_organisation_teams_includes_inactive_teams(client):
    organisation = create_organisation(client)
    url = f"/api/v1/organisations/{organisation['id']}/teams"

    team = client.post(
        url,
        json={"name": "Support Team"},
    ).json()

    client.patch(
        f"/api/v1/teams/{team['id']}",
        json={"is_active": False},
    )

    response = client.get(url)

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["is_active"] is False


def test_get_team_by_id(client):
    organisation = create_organisation(client)

    team = client.post(
        f"/api/v1/organisations/{organisation['id']}/teams",
        json={"name": "Support Team"},
    ).json()

    response = client.get(f"/api/v1/teams/{team['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == team["id"]
    assert response.json()["name"] == "Support Team"


def test_get_nonexistent_team(client):
    create_organisation(client)

    response = client.get(f"/api/v1/teams/{uuid.uuid4()}")

    assert response.status_code == 404


def test_replace_team(client):
    organisation = create_organisation(client)

    team = client.post(
        f"/api/v1/organisations/{organisation['id']}/teams",
        json={"name": "Support Team", "description": "Old description"},
    ).json()

    response = client.put(
        f"/api/v1/teams/{team['id']}",
        json={
            "name": "Customer Support",
            "description": "Updated description",
            "is_active": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Customer Support"
    assert response.json()["description"] == "Updated description"


def test_patch_team(client):
    organisation = create_organisation(client)

    team = client.post(
        f"/api/v1/organisations/{organisation['id']}/teams",
        json={"name": "Support Team"},
    ).json()

    response = client.patch(
        f"/api/v1/teams/{team['id']}",
        json={"name": "Updated Support Team"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Support Team"


def test_patch_team_deactivate(client):
    organisation = create_organisation(client)

    team = client.post(
        f"/api/v1/organisations/{organisation['id']}/teams",
        json={"name": "Support Team"},
    ).json()

    response = client.patch(
        f"/api/v1/teams/{team['id']}",
        json={"is_active": False},
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_patch_team_with_empty_data(client):
    organisation = create_organisation(client)

    team = client.post(
        f"/api/v1/organisations/{organisation['id']}/teams",
        json={"name": "Support Team"},
    ).json()

    response = client.patch(
        f"/api/v1/teams/{team['id']}",
        json={},
    )

    assert response.status_code == 400


def test_patch_team_with_null_name(client):
    organisation = create_organisation(client)

    team = client.post(
        f"/api/v1/organisations/{organisation['id']}/teams",
        json={"name": "Support Team"},
    ).json()

    response = client.patch(
        f"/api/v1/teams/{team['id']}",
        json={"name": None},
    )

    assert response.status_code == 422


def test_replace_team_for_inactive_organisation(client):
    organisation = create_organisation(client)

    team = client.post(
        f"/api/v1/organisations/{organisation['id']}/teams",
        json={"name": "Support Team"},
    ).json()

    client.patch(
        f"/api/v1/organisations/{organisation['id']}",
        json={"status": "INACTIVE"},
    )

    response = client.put(
        f"/api/v1/teams/{team['id']}",
        json={
            "name": "Updated Support",
            "description": None,
            "is_active": True,
        },
    )

    assert response.status_code == 400


def test_replace_team_with_duplicate_name(client):
    organisation = create_organisation(client)
    url = f"/api/v1/organisations/{organisation['id']}/teams"

    client.post(url, json={"name": "Support Team"})

    second_team = client.post(
        url,
        json={"name": "Development Team"},
    ).json()

    response = client.put(
        f"/api/v1/teams/{second_team['id']}",
        json={
            "name": "Support Team",
            "description": None,
            "is_active": True,
        },
    )

    assert response.status_code == 409


def test_patch_team_with_duplicate_name(client):
    organisation = create_organisation(client)
    url = f"/api/v1/organisations/{organisation['id']}/teams"

    client.post(url, json={"name": "Support Team"})

    second_team = client.post(
        url,
        json={"name": "Development Team"},
    ).json()

    response = client.patch(
        f"/api/v1/teams/{second_team['id']}",
        json={"name": "Support Team"},
    )

    assert response.status_code == 409


def test_replace_nonexistent_team(client):
    import uuid

    response = client.put(
        f"/api/v1/teams/{uuid.uuid4()}",
        json={
            "name": "Support Team",
            "description": None,
            "is_active": True,
        },
    )

    assert response.status_code == 404


def test_patch_nonexistent_team(client):
    create_organisation(client)

    response = client.patch(
        f"/api/v1/teams/{uuid.uuid4()}",
        json={"name": "Updated Team"},
    )

    assert response.status_code == 404
