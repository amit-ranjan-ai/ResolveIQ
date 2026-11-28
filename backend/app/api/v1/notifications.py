from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.authorization import check_membership_roles
from app.core.dependencies import get_current_user
from app.db.dependencies import get_db
from app.models.user import User
from app.schemas.notification import (
    MarkAllNotificationsReadResponse,
    NotificationResponse,
    UnreadNotificationCountResponse,
)
from app.services.notification import (
    count_unread_notifications,
    get_member_notifications,
    mark_all_notifications_as_read,
    mark_notification_as_read,
)

router = APIRouter(tags=["Notifications"])


@router.get(
    "/organisations/{organisation_id}/notifications",
    response_model=list[NotificationResponse],
)
def list_notifications(
    organisation_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    unread_only: bool = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[NotificationResponse]:
    """List notifications for the current organisation member."""

    membership = check_membership_roles(
        organisation_id=organisation_id,
        current_user=current_user,
        db=db,
        allowed_roles=("OWNER", "ADMIN", "AGENT", "REQUESTER"),
    )

    return get_member_notifications(
        db=db,
        organisation_id=organisation_id,
        recipient_membership_id=membership.id,
        unread_only=unread_only,
        limit=limit,
    )


@router.get(
    "/organisations/{organisation_id}/notifications/unread-count",
    response_model=UnreadNotificationCountResponse,
)
def get_unread_notification_count(
    organisation_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> UnreadNotificationCountResponse:
    """Get the unread notification count for the current member."""

    membership = check_membership_roles(
        organisation_id=organisation_id,
        current_user=current_user,
        db=db,
        allowed_roles=("OWNER", "ADMIN", "AGENT", "REQUESTER"),
    )

    count = count_unread_notifications(
        db=db,
        organisation_id=organisation_id,
        recipient_membership_id=membership.id,
    )

    return UnreadNotificationCountResponse(unread_count=count)


@router.patch(
    "/organisations/{organisation_id}/notifications/{notification_id}/read",
    response_model=NotificationResponse,
)
def mark_notification_read(
    organisation_id: UUID,
    notification_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Mark one of the current member's notifications as read."""

    membership = check_membership_roles(
        organisation_id=organisation_id,
        current_user=current_user,
        db=db,
        allowed_roles=("OWNER", "ADMIN", "AGENT", "REQUESTER"),
    )

    notification = mark_notification_as_read(
        db=db,
        organisation_id=organisation_id,
        recipient_membership_id=membership.id,
        notification_id=notification_id,
    )

    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )

    db.commit()
    db.refresh(notification)

    return notification


@router.patch(
    "/organisations/{organisation_id}/notifications/read-all",
    response_model=MarkAllNotificationsReadResponse,
)
def mark_all_notifications_read(
    organisation_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MarkAllNotificationsReadResponse:
    """Mark all notifications as read for the current member."""

    membership = check_membership_roles(
        organisation_id=organisation_id,
        current_user=current_user,
        db=db,
        allowed_roles=("OWNER", "ADMIN", "AGENT", "REQUESTER"),
    )

    updated_count = mark_all_notifications_as_read(
        db=db,
        organisation_id=organisation_id,
        recipient_membership_id=membership.id,
    )

    db.commit()

    return MarkAllNotificationsReadResponse(
        updated_count=updated_count,
    )
