import asyncio
import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.websockets import WebSocketDisconnect

import app.models
from app.core.jwt import create_access_token
from app.db.base import Base
from app.db.dependencies import get_db
from app.main import app
from app.models.notification import Notification
from app.models.organisation import Organisation
from app.models.organisation_membership import OrganisationMembership
from app.models.user import User
from app.services.websocket_manager import ConnectionManager, manager


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
        test_client.testing_session_local = db_session_factory
        yield test_client


def create_notification_context(db_session_factory):
    with db_session_factory() as db:
        organisation = Organisation(
            name="Notification Test Organisation",
            slug=f"notification-test-{uuid.uuid4().hex[:8]}",
            status="ACTIVE",
        )
        db.add(organisation)
        db.flush()

        user = User(
            full_name="Notification Test User",
            email=f"notification-{uuid.uuid4()}@example.com",
            password_hash="test-password-hash",
        )
        db.add(user)
        db.flush()

        membership = OrganisationMembership(
            organisation_id=organisation.id,
            user_id=user.id,
            role="OWNER",
            is_active=True,
        )
        db.add(membership)
        db.commit()

        return {
            "organisation_id": str(organisation.id),
            "user_id": str(user.id),
            "membership_id": str(membership.id),
            "access_token": create_access_token(str(user.id)),
        }


def add_notification(db_session_factory, context, title="Test notification"):
    with db_session_factory() as db:
        notification = Notification(
            organisation_id=uuid.UUID(context["organisation_id"]),
            recipient_membership_id=uuid.UUID(context["membership_id"]),
            notification_type="TICKET_ASSIGNED",
            title=title,
            message="This is a test notification.",
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)

        return str(notification.id)


def authenticate(client, context):
    client.headers.update({"Authorization": f"Bearer {context['access_token']}"})


# Existing notification API tests


def test_list_notifications(client, db_session_factory):
    context = create_notification_context(db_session_factory)
    authenticate(client, context)

    add_notification(db_session_factory, context, "First notification")
    add_notification(db_session_factory, context, "Second notification")

    response = client.get(
        f"/api/v1/organisations/{context['organisation_id']}/notifications"
    )

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_list_unread_notifications_only(client, db_session_factory):
    context = create_notification_context(db_session_factory)
    authenticate(client, context)

    notification_id = add_notification(db_session_factory, context)

    with db_session_factory() as db:
        notification = db.get(Notification, uuid.UUID(notification_id))
        notification.is_read = True
        db.commit()

    response = client.get(
        f"/api/v1/organisations/{context['organisation_id']}/notifications",
        params={"unread_only": True},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_get_unread_notification_count(client, db_session_factory):
    context = create_notification_context(db_session_factory)
    authenticate(client, context)

    add_notification(db_session_factory, context, "First")
    add_notification(db_session_factory, context, "Second")

    response = client.get(
        f"/api/v1/organisations/{context['organisation_id']}/notifications/unread-count"
    )

    assert response.status_code == 200
    assert response.json()["unread_count"] == 2


def test_mark_notification_as_read(client, db_session_factory):
    context = create_notification_context(db_session_factory)
    authenticate(client, context)

    notification_id = add_notification(db_session_factory, context)

    response = client.patch(
        f"/api/v1/organisations/{context['organisation_id']}"
        f"/notifications/{notification_id}/read"
    )

    assert response.status_code == 200
    assert response.json()["is_read"] is True
    assert response.json()["read_at"] is not None


def test_mark_nonexistent_notification_as_read(client, db_session_factory):
    context = create_notification_context(db_session_factory)
    authenticate(client, context)

    response = client.patch(
        f"/api/v1/organisations/{context['organisation_id']}"
        f"/notifications/{uuid.uuid4()}/read"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Notification not found."


def test_mark_all_notifications_as_read(client, db_session_factory):
    context = create_notification_context(db_session_factory)
    authenticate(client, context)

    add_notification(db_session_factory, context, "First")
    add_notification(db_session_factory, context, "Second")

    response = client.patch(
        f"/api/v1/organisations/{context['organisation_id']}/notifications/read-all"
    )

    assert response.status_code == 200
    assert response.json()["updated_count"] == 2

    count_response = client.get(
        f"/api/v1/organisations/{context['organisation_id']}/notifications/unread-count"
    )

    assert count_response.status_code == 200
    assert count_response.json()["unread_count"] == 0


def test_member_cannot_access_another_members_notification(
    client,
    db_session_factory,
):
    owner_context = create_notification_context(db_session_factory)
    notification_id = add_notification(db_session_factory, owner_context)

    other_context = create_notification_context(db_session_factory)
    authenticate(client, other_context)

    response = client.patch(
        f"/api/v1/organisations/{owner_context['organisation_id']}"
        f"/notifications/{notification_id}/read"
    )

    assert response.status_code == 403


def test_notifications_require_authentication(client, db_session_factory):
    context = create_notification_context(db_session_factory)

    response = client.get(
        f"/api/v1/organisations/{context['organisation_id']}/notifications"
    )

    assert response.status_code == 401


# New WebSocket tests


def test_websocket_connection_success(client, db_session_factory):
    context = create_notification_context(db_session_factory)
    membership_id = uuid.UUID(context["membership_id"])

    with client.websocket_connect(
        f"/api/v1/organisations/{context['organisation_id']}/notifications/ws"
    ) as websocket:
        websocket.send_json({"token": context["access_token"]})

        response = websocket.receive_json()

        assert response["type"] == "CONNECTED"
        assert response["message"] == "Connected to live notifications."
        assert membership_id in manager.active_connections


def test_websocket_rejects_invalid_token(client, db_session_factory):
    context = create_notification_context(db_session_factory)

    with client.websocket_connect(
        f"/api/v1/organisations/{context['organisation_id']}/notifications/ws"
    ) as websocket:
        websocket.send_json({"token": "invalid-token"})

        with pytest.raises(WebSocketDisconnect):
            websocket.receive_json()


def test_websocket_rejects_missing_token(client, db_session_factory):
    context = create_notification_context(db_session_factory)

    with client.websocket_connect(
        f"/api/v1/organisations/{context['organisation_id']}/notifications/ws"
    ) as websocket:
        websocket.send_json({})

        with pytest.raises(WebSocketDisconnect):
            websocket.receive_json()


def test_websocket_rejects_inactive_membership(client, db_session_factory):
    context = create_notification_context(db_session_factory)

    with db_session_factory() as db:
        membership = db.get(
            OrganisationMembership,
            uuid.UUID(context["membership_id"]),
        )
        membership.is_active = False
        db.commit()

    with client.websocket_connect(
        f"/api/v1/organisations/{context['organisation_id']}/notifications/ws"
    ) as websocket:
        websocket.send_json({"token": context["access_token"]})

        with pytest.raises(WebSocketDisconnect):
            websocket.receive_json()


def test_websocket_connection_is_removed_after_disconnect(
    client,
    db_session_factory,
):
    context = create_notification_context(db_session_factory)
    membership_id = uuid.UUID(context["membership_id"])

    with client.websocket_connect(
        f"/api/v1/organisations/{context['organisation_id']}/notifications/ws"
    ) as websocket:
        websocket.send_json({"token": context["access_token"]})

        response = websocket.receive_json()

        assert response["type"] == "CONNECTED"
        assert membership_id in manager.active_connections

    assert membership_id not in manager.active_connections


def test_send_to_member_delivers_message():
    connection_manager = ConnectionManager()
    membership_id = uuid.uuid4()

    websocket = AsyncMock()
    connection_manager.connect(membership_id, websocket)

    message = {
        "type": "NEW_NOTIFICATION",
        "title": "Ticket assigned",
        "message": "A ticket has been assigned to you.",
    }

    asyncio.run(connection_manager.send_to_member(membership_id, message))

    websocket.send_json.assert_awaited_once_with(message)


def test_send_to_member_does_not_send_to_another_member():
    connection_manager = ConnectionManager()

    first_membership_id = uuid.uuid4()
    second_membership_id = uuid.uuid4()

    first_websocket = AsyncMock()
    second_websocket = AsyncMock()

    connection_manager.connect(first_membership_id, first_websocket)
    connection_manager.connect(second_membership_id, second_websocket)

    message = {
        "type": "NEW_NOTIFICATION",
        "title": "Private notification",
        "message": "This belongs to the first member.",
    }

    asyncio.run(connection_manager.send_to_member(first_membership_id, message))

    first_websocket.send_json.assert_awaited_once_with(message)
    second_websocket.send_json.assert_not_awaited()


def test_send_to_member_removes_disconnected_connection():
    connection_manager = ConnectionManager()
    membership_id = uuid.uuid4()

    websocket = AsyncMock()
    websocket.send_json.side_effect = RuntimeError("Connection closed")

    connection_manager.connect(membership_id, websocket)

    asyncio.run(
        connection_manager.send_to_member(
            membership_id,
            {"type": "NEW_NOTIFICATION"},
        )
    )

    websocket.send_json.assert_awaited_once()
    assert membership_id not in connection_manager.active_connections
