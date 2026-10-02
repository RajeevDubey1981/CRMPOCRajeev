import os
import uuid
import zipfile
from io import BytesIO
from datetime import datetime

from fastapi import HTTPException, UploadFile, status

from app.config import settings

ALLOWED_MIME = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/jpeg",
    "image/png",
    "image/jpg",
}
ALLOWED_EXT = {".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png"}
MAX_BYTES = 2 * 1024 * 1024  # 2 MB


def to_public_upload_path(path: str | None) -> str | None:
    if not path:
        return path
    normalized = path.replace("\\", "/")
    marker = "/uploads/"
    idx = normalized.find(marker)
    if idx >= 0:
        return normalized[idx:]
    if normalized.startswith("uploads/"):
        return f"/{normalized}"
    return normalized


def _safe_ext(filename: str, allowed_ext: set[str] | None = None) -> str:
    allowed = allowed_ext or ALLOWED_EXT
    name = os.path.basename((filename or "").replace("\\", "/"))
    if "\x00" in name or name.count(".") > 2:
        return ""
    ext = os.path.splitext(name)[1].lower()
    return ext if ext in allowed else ""


def _validate_file_signature(contents: bytes, extension: str) -> None:
    signatures = {
        ".pdf": contents.startswith(b"%PDF-"),
        ".jpg": contents.startswith(b"\xff\xd8\xff"),
        ".jpeg": contents.startswith(b"\xff\xd8\xff"),
        ".png": contents.startswith(b"\x89PNG\r\n\x1a\n"),
        ".doc": contents.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"),
        ".docx": contents.startswith(b"PK\x03\x04"),
    }
    if not signatures.get(extension, False):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File content does not match its extension")
    if extension == ".docx":
        try:
            with zipfile.ZipFile(BytesIO(contents)) as archive:
                names = archive.namelist()
                if any(name.startswith(("/", "\\")) or ".." in name.split("/") for name in names):
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unsafe Office archive")
                if any(name.lower().endswith("vbaproject.bin") for name in names):
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, "Macro-enabled Office files are not allowed")
        except zipfile.BadZipFile:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid Office document")


def _validate_upload(
    file: UploadFile,
    allowed_ext: set[str] | None = None,
    allowed_mime: set[str] | None = None,
) -> str:
    extension = _safe_ext(file.filename, allowed_ext)
    allowed_content_types = allowed_mime or ALLOWED_MIME
    if not extension or file.content_type not in allowed_content_types:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unsupported or unsafe file type")
    return extension


async def save_upload(
    file: UploadFile,
    module: str,
    allowed_ext: set[str] | None = None,
    allowed_mime: set[str] | None = None,
    max_bytes: int = MAX_BYTES,
) -> str:
    """Validate and persist an uploaded file under /uploads/{module}/{YYYY}/{MM}/.

    Returns the public URL path under /uploads/.
    """
    extension = _validate_upload(file, allowed_ext=allowed_ext, allowed_mime=allowed_mime)

    contents = await file.read()
    if len(contents) > max_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File exceeds 2MB limit")
    if not contents:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file")

    now = datetime.utcnow()
    sub = settings.resolved_upload_dir / module / f"{now.year:04d}" / f"{now.month:02d}"
    os.makedirs(sub, exist_ok=True)

    _validate_file_signature(contents, extension)
    ext = extension
    name = f"{uuid.uuid4().hex}{ext}"
    full_path = sub / name
    with open(full_path, "wb") as f:
        f.write(contents)
    return to_public_upload_path(str(full_path))


async def read_upload_bytes(file: UploadFile) -> tuple[bytes, str, str, int]:
    extension = _validate_upload(file)

    contents = await file.read()
    if len(contents) > MAX_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File exceeds 2MB limit")
    if not contents:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file")
    _validate_file_signature(contents, extension)

    safe_name = f"upload{extension}"
    content_type = file.content_type or "application/octet-stream"
    return contents, safe_name, content_type, len(contents)


async def read_csv_upload(file: UploadFile) -> bytes:
    """Validate a UTF-8 CSV upload that is parsed as data, not stored as a file."""
    filename = os.path.basename((file.filename or "").replace("\\", "/"))
    if not filename or os.path.splitext(filename)[1].lower() != ".csv":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only CSV files are allowed")
    contents = await file.read()
    if len(contents) > MAX_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File exceeds 2MB limit")
    if not contents:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file")
    try:
        contents.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "CSV must be UTF-8 encoded")
    return contents
