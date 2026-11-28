import asyncio
import json
import logging
from collections.abc import AsyncIterator
from uuid import UUID

from valkey import Valkey
from valkey.asyncio import Valkey as AsyncValkey
from valkey.exceptions import ValkeyError

from app.core.config import settings

logger = logging.getLogger(__name__)

NOTIFICATION_CHANNEL = "resolveiq:notifications"
RECONNECT_DELAY_SECONDS = 2


def publish_notification_event(
    recipient_membership_id: UUID,
    notification_payload: dict,
) -> None:
    """Publish a committed notification for live WebSocket delivery."""

    client = Valkey.from_url(
        settings.VALKEY_URL,
        decode_responses=True,
    )

    try:
        event = {
            "recipient_membership_id": str(recipient_membership_id),
            "notification": notification_payload,
        }

        client.publish(
            NOTIFICATION_CHANNEL,
            json.dumps(event),
        )
    finally:
        client.close()


async def notification_event_stream() -> AsyncIterator[dict]:
    """Listen for notification events and reconnect if Valkey disconnects."""

    while True:
        client = AsyncValkey.from_url(
            settings.VALKEY_URL,
            decode_responses=True,
            socket_timeout=None,
        )

        pubsub = client.pubsub()

        try:
            await pubsub.subscribe(NOTIFICATION_CHANNEL)

            logger.info(
                "Subscribed to Valkey channel: %s",
                NOTIFICATION_CHANNEL,
            )

            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue

                try:
                    event = json.loads(message["data"])
                except (json.JSONDecodeError, TypeError):
                    logger.warning(
                        "Received an invalid notification event from Valkey."
                    )
                    continue

                if isinstance(event, dict):
                    yield event

        except (ValkeyError, OSError):
            logger.exception("Valkey notification subscription failed. Reconnecting...")

        finally:
            try:
                await pubsub.aclose()
            except (ValkeyError, OSError):
                logger.debug("Could not close Valkey Pub/Sub connection.")

            try:
                await client.aclose()
            except (ValkeyError, OSError):
                logger.debug("Could not close Valkey client.")

        await asyncio.sleep(RECONNECT_DELAY_SECONDS)
