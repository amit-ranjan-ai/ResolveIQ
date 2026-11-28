import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4

from app.main import listen_for_notification_events


def test_listener_forwards_valkey_notification(monkeypatch):
    membership_id = uuid4()

    notification_payload = {
        "id": str(uuid4()),
        "notification_type": "SLA_BREACHED",
        "title": "SLA deadline breached",
        "message": "A ticket has breached its SLA deadline.",
        "ticket_id": str(uuid4()),
    }

    async def fake_notification_event_stream():
        yield {
            "recipient_membership_id": str(membership_id),
            "notification": notification_payload,
        }

    send_to_member = AsyncMock()

    monkeypatch.setattr(
        "app.main.notification_event_stream",
        fake_notification_event_stream,
    )

    monkeypatch.setattr(
        "app.main.manager.send_to_member",
        send_to_member,
    )

    asyncio.run(listen_for_notification_events())

    send_to_member.assert_awaited_once_with(
        membership_id,
        {
            "type": "NEW_NOTIFICATION",
            "notification": notification_payload,
        },
    )
