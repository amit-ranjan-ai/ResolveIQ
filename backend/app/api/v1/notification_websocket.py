from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.jwt import verify_access_token
from app.db.dependencies import get_db
from app.models.organisation_membership import OrganisationMembership
from app.models.user import User
from app.services.websocket_manager import manager

router = APIRouter(tags=["Notification WebSocket"])


@router.websocket("/organisations/{organisation_id}/notifications/ws")
async def notification_websocket(
    websocket: WebSocket,
    organisation_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Authenticate and connect a member to live notifications."""

    await websocket.accept()

    membership_id = None

    try:
        authentication = await websocket.receive_json()

        if not isinstance(authentication, dict):
            await websocket.close(code=1008)
            return

        token = authentication.get("token")

        if not isinstance(token, str) or not token:
            await websocket.close(code=1008)
            return

        user_id = verify_access_token(token)

        if user_id is None:
            await websocket.close(code=1008)
            return

        try:
            parsed_user_id = UUID(user_id)
        except ValueError:
            await websocket.close(code=1008)
            return

        user = db.get(User, parsed_user_id)

        if user is None or not user.is_active:
            await websocket.close(code=1008)
            return

        membership = db.scalar(
            select(OrganisationMembership).where(
                OrganisationMembership.organisation_id == organisation_id,
                OrganisationMembership.user_id == user.id,
                OrganisationMembership.is_active.is_(True),
                OrganisationMembership.role.in_(
                    ("OWNER", "ADMIN", "AGENT", "REQUESTER")
                ),
            )
        )

        if membership is None:
            await websocket.close(code=1008)
            return

        membership_id = membership.id

        manager.connect(membership_id, websocket)

        await websocket.send_json(
            {
                "type": "CONNECTED",
                "message": "Connected to live notifications.",
            }
        )

        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        pass

    finally:
        if membership_id is not None:
            manager.disconnect(membership_id, websocket)
