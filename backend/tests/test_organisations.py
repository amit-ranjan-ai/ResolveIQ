import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.dependencies import get_db
from app.main import app
from app.models.organisation import Organisation


@pytest.fixture
def client():
    test_engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Organisation.__table__.create(bind=test_engine)

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
        yield test_client

    app.dependency_overrides.clear()
    test_engine.dispose()


def test_create_organisation(client):
    response = client.post(
        "/api/v1/organisations/",
        json={
            "name": "Test Organisation",
            "slug": "test-organisation",
            "email": "test@example.com",
            "status": "ACTIVE",
        },
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Test Organisation"
    assert response.json()["slug"] == "test-organisation"


def test_duplicate_organisation_slug(client):
    organisation_data = {
        "name": "Test Organisation",
        "slug": "duplicate-test",
        "email": "test@example.com",
        "status": "ACTIVE",
    }

    first_response = client.post(
        "/api/v1/organisations/",
        json=organisation_data,
    )

    second_response = client.post(
        "/api/v1/organisations/",
        json=organisation_data,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_get_all_organisations(client):
    client.post(
        "/api/v1/organisations/",
        json={
            "name": "Organisation One",
            "slug": "organisation-one",
            "email": "one@example.com",
            "status": "ACTIVE",
        },
    )

    response = client.get("/api/v1/organisations/")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Organisation One"


def test_get_organisation_by_id(client):
    create_response = client.post(
        "/api/v1/organisations/",
        json={
            "name": "Organisation Two",
            "slug": "organisation-two",
            "email": "two@example.com",
            "status": "ACTIVE",
        },
    )

    organisation_id = create_response.json()["id"]

    response = client.get(f"/api/v1/organisations/{organisation_id}")

    assert response.status_code == 200
    assert response.json()["id"] == organisation_id
    assert response.json()["name"] == "Organisation Two"


def test_get_nonexistent_organisation(client):
    response = client.get("/api/v1/organisations/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
    assert response.json()["detail"] == "Organisation not found."


def test_put_update_organisation(client):
    create_response = client.post(
        "/api/v1/organisations/",
        json={
            "name": "Original Organisation",
            "slug": "original-organisation",
            "email": "original@example.com",
            "status": "ACTIVE",
        },
    )

    organisation_id = create_response.json()["id"]

    response = client.put(
        f"/api/v1/organisations/{organisation_id}",
        json={
            "name": "Updated Organisation",
            "slug": "updated-organisation",
            "email": "updated@example.com",
            "status": "INACTIVE",
        },
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Organisation"
    assert response.json()["slug"] == "updated-organisation"
    assert response.json()["status"] == "INACTIVE"


def test_patch_update_organisation_status(client):
    create_response = client.post(
        "/api/v1/organisations/",
        json={
            "name": "Patch Organisation",
            "slug": "patch-organisation",
            "email": "patch@example.com",
            "status": "ACTIVE",
        },
    )

    organisation_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/organisations/{organisation_id}",
        json={
            "status": "SUSPENDED",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "SUSPENDED"
    assert response.json()["name"] == "Patch Organisation"


def test_patch_invalid_organisation_status(client):
    create_response = client.post(
        "/api/v1/organisations/",
        json={
            "name": "Invalid Status Organisation",
            "slug": "invalid-status-organisation",
            "email": "invalid@example.com",
            "status": "ACTIVE",
        },
    )

    organisation_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/organisations/{organisation_id}",
        json={
            "status": "DELETED",
        },
    )

    assert response.status_code == 422


def test_put_nonexistent_organisation(client):
    response = client.put(
        "/api/v1/organisations/00000000-0000-0000-0000-000000000000",
        json={
            "name": "Missing Organisation",
            "slug": "missing-organisation",
            "email": "missing@example.com",
            "status": "ACTIVE",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Organisation not found."


def test_patch_nonexistent_organisation(client):
    response = client.patch(
        "/api/v1/organisations/00000000-0000-0000-0000-000000000000",
        json={
            "status": "INACTIVE",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Organisation not found."


def test_patch_empty_data(client):
    create_response = client.post(
        "/api/v1/organisations/",
        json={
            "name": "Empty Patch Organisation",
            "slug": "empty-patch-organisation",
            "email": "empty@example.com",
            "status": "ACTIVE",
        },
    )

    organisation_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/organisations/{organisation_id}",
        json={},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "At least one field must be provided for update."
    )


def test_put_duplicate_organisation_slug(client):
    first = client.post(
        "/api/v1/organisations/",
        json={
            "name": "Organisation One",
            "slug": "organisation-one",
            "email": "one@example.com",
            "status": "ACTIVE",
        },
    )

    second = client.post(
        "/api/v1/organisations/",
        json={
            "name": "Organisation Two",
            "slug": "organisation-two",
            "email": "two@example.com",
            "status": "ACTIVE",
        },
    )

    response = client.put(
        f"/api/v1/organisations/{second.json()['id']}",
        json={
            "name": "Updated Organisation",
            "slug": "organisation-one",
            "email": "updated@example.com",
            "status": "ACTIVE",
        },
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert response.status_code == 409


def test_patch_duplicate_organisation_slug(client):
    client.post(
        "/api/v1/organisations/",
        json={
            "name": "Organisation One",
            "slug": "organisation-one",
            "email": "one@example.com",
            "status": "ACTIVE",
        },
    )

    second = client.post(
        "/api/v1/organisations/",
        json={
            "name": "Organisation Two",
            "slug": "organisation-two",
            "email": "two@example.com",
            "status": "ACTIVE",
        },
    )

    response = client.patch(
        f"/api/v1/organisations/{second.json()['id']}",
        json={
            "slug": "organisation-one",
        },
    )

    assert response.status_code == 409


def test_create_organisation_with_short_name(client):
    response = client.post(
        "/api/v1/organisations/",
        json={
            "name": "A",
            "slug": "short-name-org",
            "email": "test@example.com",
            "status": "ACTIVE",
        },
    )

    assert response.status_code == 422


def test_create_organisation_with_invalid_email(client):
    response = client.post(
        "/api/v1/organisations/",
        json={
            "name": "Invalid Email Organisation",
            "slug": "invalid-email-org",
            "email": "not-an-email",
            "status": "ACTIVE",
        },
    )

    assert response.status_code == 422


def test_create_organisation_with_invalid_status(client):
    response = client.post(
        "/api/v1/organisations/",
        json={
            "name": "Invalid Status Organisation",
            "slug": "invalid-status-org",
            "email": "test@example.com",
            "status": "DELETED",
        },
    )

    assert response.status_code == 422


def test_patch_rejects_null_name(client):
    create_response = client.post(
        "/api/v1/organisations/",
        json={
            "name": "Null Test Organisation",
            "slug": "null-test-organisation",
            "email": "null@example.com",
            "status": "ACTIVE",
        },
    )

    organisation_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/organisations/{organisation_id}",
        json={"name": None},
    )

    assert response.status_code == 422


def test_patch_allows_null_email(client):
    create_response = client.post(
        "/api/v1/organisations/",
        json={
            "name": "Email Null Organisation",
            "slug": "email-null-organisation",
            "email": "email@example.com",
            "status": "ACTIVE",
        },
    )

    organisation_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/organisations/{organisation_id}",
        json={"email": None},
    )

    assert response.status_code == 200
    assert response.json()["email"] is None


def test_put_rejects_missing_required_fields(client):
    create_response = client.post(
        "/api/v1/organisations/",
        json={
            "name": "PUT Validation Organisation",
            "slug": "put-validation-organisation",
            "email": "put@example.com",
            "status": "ACTIVE",
        },
    )

    organisation_id = create_response.json()["id"]

    response = client.put(
        f"/api/v1/organisations/{organisation_id}",
        json={
            "status": "INACTIVE",
        },
    )

    assert response.status_code == 422


def test_failed_patch_preserves_existing_organisation(client):
    client.post(
        "/api/v1/organisations/",
        json={
            "name": "Original Organisation",
            "slug": "original-data",
            "email": "original@example.com",
            "status": "ACTIVE",
        },
    )

    second = client.post(
        "/api/v1/organisations/",
        json={
            "name": "Second Organisation",
            "slug": "second-data",
            "email": "second@example.com",
            "status": "ACTIVE",
        },
    )

    organisation_id = second.json()["id"]

    failed_response = client.patch(
        f"/api/v1/organisations/{organisation_id}",
        json={"slug": "original-data"},
    )

    check_response = client.get(f"/api/v1/organisations/{organisation_id}")

    assert failed_response.status_code == 409
    assert check_response.status_code == 200
    assert check_response.json()["name"] == "Second Organisation"
    assert check_response.json()["slug"] == "second-data"
    assert check_response.json()["status"] == "ACTIVE"
