from datetime import UTC
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.notification import Notification


def create_notification(
    db: Session,
    organisation_id: UUID,
    recipient_membership_id: UUID,
    notification_type: str,
    title: str,
    message: str,
    ticket_id: UUID | None = None,
) -> Notification:
    """Create a notification for an organisation member."""

    notification = Notification(
        organisation_id=organisation_id,
        recipient_membership_id=recipient_membership_id,
        ticket_id=ticket_id,
        notification_type=notification_type,
        title=title,
        message=message,
    )

    db.add(notification)

    return notification


def get_member_notifications(
    db: Session,
    organisation_id: UUID,
    recipient_membership_id: UUID,
    unread_only: bool = False,
    limit: int = 50,
) -> list[Notification]:
    """Get notifications belonging to one organisation member."""

    query = select(Notification).where(
        Notification.organisation_id == organisation_id,
        Notification.recipient_membership_id == recipient_membership_id,
    )

    if unread_only:
        query = query.where(Notification.is_read.is_(False))

    query = query.order_by(Notification.created_at.desc())
    query = query.limit(limit)

    return list(db.scalars(query).all())


def count_unread_notifications(
    db: Session,
    organisation_id: UUID,
    recipient_membership_id: UUID,
) -> int:
    """Count unread notifications for one organisation member."""

    from sqlalchemy import func

    query = select(func.count(Notification.id)).where(
        Notification.organisation_id == organisation_id,
        Notification.recipient_membership_id == recipient_membership_id,
        Notification.is_read.is_(False),
    )

    return db.scalar(query) or 0


def mark_notification_as_read(
    db: Session,
    organisation_id: UUID,
    recipient_membership_id: UUID,
    notification_id: UUID,
) -> Notification | None:
    """Mark one of the member's notifications as read."""

    notification = db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.organisation_id == organisation_id,
            Notification.recipient_membership_id == recipient_membership_id,
        )
    )

    if notification is None:
        return None

    if not notification.is_read:
        from datetime import datetime

        notification.is_read = True
        notification.read_at = datetime.now(UTC)

    return notification


def mark_all_notifications_as_read(
    db: Session,
    organisation_id: UUID,
    recipient_membership_id: UUID,
) -> int:
    """Mark all unread notifications for one member as read."""

    from datetime import datetime

    notifications = db.scalars(
        select(Notification).where(
            Notification.organisation_id == organisation_id,
            Notification.recipient_membership_id == recipient_membership_id,
            Notification.is_read.is_(False),
        )
    ).all()

    now = datetime.now(UTC)

    for notification in notifications:
        notification.is_read = True
        notification.read_at = now

    return len(notifications)
