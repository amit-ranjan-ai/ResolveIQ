import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.jwt import create_access_token
from app.db.dependencies import get_db
from app.main import app
from app.models.user import User


@pytest.fixture
def client():
    test_engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    User.__table__.create(bind=test_engine)

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


def create_test_user(client, email="test@example.com"):
    return client.post(
        "/api/v1/users/",
        json={
            "full_name": "Test User",
            "email": email,
            "password": "TestPassword123",
        },
    )


def get_auth_headers(user_id):
    token = create_access_token(user_id)

    return {
        "Authorization": f"Bearer {token}",
    }


def test_create_user(client):
    response = create_test_user(client)

    assert response.status_code == 201
    assert response.json()["full_name"] == "Test User"
    assert response.json()["email"] == "test@example.com"
    assert response.json()["is_active"] is True


def test_create_user_does_not_expose_password(client):
    response = create_test_user(client)

    assert response.status_code == 201
    assert "password" not in response.json()
    assert "password_hash" not in response.json()


def test_duplicate_user_email(client):
    first_response = create_test_user(client)
    second_response = create_test_user(client)

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_duplicate_user_email_case_insensitive(client):
    first_response = create_test_user(
        client,
        email="test@example.com",
    )

    second_response = create_test_user(
        client,
        email="TEST@example.com",
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_create_user_with_invalid_email(client):
    response = client.post(
        "/api/v1/users/",
        json={
            "full_name": "Test User",
            "email": "invalid-email",
            "password": "TestPassword123",
        },
    )

    assert response.status_code == 422


def test_get_current_user_profile(client):
    create_response = create_test_user(client)
    user_id = create_response.json()["id"]

    response = client.get(
        "/api/v1/users/me",
        headers=get_auth_headers(user_id),
    )

    assert response.status_code == 200
    assert response.json()["id"] == user_id
    assert response.json()["full_name"] == "Test User"


def test_get_current_user_without_token(client):
    response = client.get("/api/v1/users/me")

    assert response.status_code == 401


def test_get_current_user_with_invalid_token(client):
    response = client.get(
        "/api/v1/users/me",
        headers={
            "Authorization": "Bearer invalid-token",
        },
    )

    assert response.status_code == 401


def test_update_current_user_profile(client):
    create_response = create_test_user(client)
    user_id = create_response.json()["id"]

    response = client.patch(
        "/api/v1/users/me",
        headers=get_auth_headers(user_id),
        json={
            "full_name": "Updated Test User",
        },
    )

    assert response.status_code == 200
    assert response.json()["full_name"] == "Updated Test User"


def test_update_current_user_without_token(client):
    response = client.patch(
        "/api/v1/users/me",
        json={
            "full_name": "Updated Test User",
        },
    )

    assert response.status_code == 401
