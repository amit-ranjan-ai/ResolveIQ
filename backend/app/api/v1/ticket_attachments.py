import logging
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.core.ticket_access import get_accessible_ticket
from app.db.dependencies import get_db
from app.models.ticket_attachment import TicketAttachment
from app.models.user import User
from app.schemas.ticket_attachment import TicketAttachmentResponse
from app.services.file_storage import (
    delete_stored_file,
    save_upload_file,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Ticket Attachments"])


@router.post(
    "/tickets/{ticket_id}/attachments",
    response_model=TicketAttachmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_ticket_attachment(
    ticket_id: UUID,
    file: Annotated[UploadFile, File()],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    ticket, membership = get_accessible_ticket(
        ticket_id,
        current_user,
        db,
    )

    stored_filename = None

    try:
        (
            stored_filename,
            storage_path,
            file_size,
        ) = await save_upload_file(file)

        attachment = TicketAttachment(
            organisation_id=ticket.organisation_id,
            ticket_id=ticket.id,
            uploaded_by_membership_id=membership.id,
            original_filename=Path((file.filename or "").replace("\\", "/")).name,
            stored_filename=stored_filename,
            storage_path=storage_path,
            content_type=file.content_type or "application/octet-stream",
            file_size=file_size,
        )

        db.add(attachment)
        db.commit()
        db.refresh(attachment)

        return attachment

    except Exception:
        db.rollback()

        if stored_filename is not None:
            try:
                delete_stored_file(
                    str(settings.UPLOAD_DIRECTORY.resolve() / stored_filename)
                )
            except OSError:
                logger.exception("Failed to clean up uploaded attachment.")

        raise


@router.get(
    "/tickets/{ticket_id}/attachments",
    response_model=list[TicketAttachmentResponse],
)
def list_ticket_attachments(
    ticket_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    ticket, _ = get_accessible_ticket(
        ticket_id,
        current_user,
        db,
    )

    return db.scalars(
        select(TicketAttachment)
        .where(
            TicketAttachment.ticket_id == ticket.id,
            TicketAttachment.organisation_id == ticket.organisation_id,
        )
        .order_by(TicketAttachment.created_at.desc())
    ).all()


@router.get("/attachments/{attachment_id}/download")
def download_ticket_attachment(
    attachment_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    attachment = db.get(TicketAttachment, attachment_id)

    if attachment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found.",
        )

    get_accessible_ticket(
        attachment.ticket_id,
        current_user,
        db,
    )

    storage_path = Path(attachment.storage_path).resolve()
    upload_root = settings.UPLOAD_DIRECTORY.resolve()

    if storage_path.parent != upload_root or not storage_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment file not found.",
        )

    return FileResponse(
        path=storage_path,
        filename=attachment.original_filename,
        media_type="application/octet-stream",
    )
