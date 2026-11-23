import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".txt",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".csv",
}


def validate_file(filename: str, file_size: int) -> None:
    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File type is not allowed.",
        )

    if file_size <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty files are not allowed.",
        )

    if file_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="File size cannot exceed 10 MB.",
        )


async def save_upload_file(file: UploadFile) -> tuple[str, str, int]:
    original_filename = Path((file.filename or "").replace("\\", "/")).name

    if not original_filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid filename is required.",
        )

    extension = Path(original_filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File type is not allowed.",
        )

    upload_directory = settings.UPLOAD_DIRECTORY.resolve()
    upload_directory.mkdir(parents=True, exist_ok=True)

    stored_filename = f"{uuid.uuid4().hex}{extension}"
    storage_path = upload_directory / stored_filename

    file_size = 0

    try:
        with storage_path.open("xb") as destination:
            while chunk := await file.read(1024 * 1024):
                file_size += len(chunk)

                if file_size > settings.MAX_UPLOAD_SIZE:
                    raise HTTPException(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        detail="File size cannot exceed 10 MB.",
                    )

                destination.write(chunk)

        validate_file(original_filename, file_size)

    except Exception:
        storage_path.unlink(missing_ok=True)
        raise

    finally:
        await file.close()

    return stored_filename, str(storage_path), file_size


def delete_stored_file(storage_path: str) -> None:
    path = Path(storage_path).resolve()
    upload_root = settings.UPLOAD_DIRECTORY.resolve()

    if path.parent != upload_root:
        raise ValueError("Invalid attachment storage path.")

    path.unlink(missing_ok=True)
