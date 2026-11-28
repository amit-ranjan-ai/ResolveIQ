import asyncio
import logging
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.services.valkey_pubsub import notification_event_stream
from app.services.websocket_manager import manager

logger = logging.getLogger(__name__)


async def listen_for_notification_events() -> None:
    """Forward Valkey notification events to connected WebSocket members."""

    async for event in notification_event_stream():
        try:
            recipient_membership_id = UUID(event["recipient_membership_id"])
            notification = event["notification"]

            if not isinstance(notification, dict):
                logger.warning("Invalid notification payload received.")
                continue

            await manager.send_to_member(
                recipient_membership_id,
                {
                    "type": "NEW_NOTIFICATION",
                    "notification": notification,
                },
            )

        except (KeyError, ValueError, TypeError):
            logger.warning("Received an invalid notification event from Valkey.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start and stop the Valkey notification listener."""

    notification_task = asyncio.create_task(listen_for_notification_events())

    logger.info("ResolveIQ notification listener started.")

    try:
        yield
    finally:
        notification_task.cancel()

        try:
            await notification_task
        except asyncio.CancelledError:
            pass

        logger.info("ResolveIQ notification listener stopped.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered Support and IT Operations Intelligence Platform",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://localhost:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    api_router,
    prefix=settings.API_V1_PREFIX,
)


@app.get("/")
def root():
    return {
        "message": "Welcome to ResolveIQ API",
        "status": "running",
        "version": settings.APP_VERSION,
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "application": settings.APP_NAME,
    }
