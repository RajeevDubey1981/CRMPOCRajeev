import os
import uuid
import zipfile
from io import BytesIO
from datetime import datetime

from fastapi import HTTPException, UploadFile, status
from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import settings

MAX_IMAGE_DIM = 1920  # longest side after re-encoding, in pixels
JPEG_QUALITY = 85

ALLOWED_MIME = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/jpeg",
    "image/png",
    "image/jpg",
}
# No .doc (legacy OLE2 Word format): unlike .docx, its internal streams can't be scanned for an embedded
# macro project the way _validate_file_signature does below, so a macro-laden .doc would sail straight
# through as a plausible "proof document"/"agreement" upload (security review, 2026-10-27). .docx covers
# the same use case and is checked.
ALLOWED_EXT = {".pdf", ".docx", ".jpg", ".jpeg", ".png"}
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
    # ".." (consecutive dots) is the actual red flag -- path-traversal-style obfuscation or a
    # disguised double extension. A flat dot *count* isn't: ordinary filenames routinely have
    # several (a date, a version, an abbreviation like "A.C. Bill.pdf"), and rejecting those
    # outright blocked real customer document uploads for no security benefit -- the extension
    # allowlist below plus the content-signature check in _validate_file_signature are what
    # actually defend against a disguised file, not dot counting.
    if "\x00" in name or ".." in name:
        return ""
    ext = os.path.splitext(name)[1].lower()
    return ext if ext in allowed else ""


def _validate_file_signature(contents: bytes, extension: str) -> None:
    if extension == ".csv":
        if b"\x00" in contents:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "File content does not match its extension")
        try:
            contents.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "CSV must be UTF-8 text")
        return
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


def _reencode_image(contents: bytes, extension: str) -> bytes:
    """Decode every uploaded photo and re-save it through Pillow instead of storing the bytes as given.
    This is the real defense against a payload smuggled inside something that merely looks like a photo
    (its magic bytes already matched in _validate_file_signature): only genuine decoded pixel data
    survives the round trip, so a polyglot file or anything appended past the image data is dropped.
    It also strips EXIF/metadata and shrinks oversized photos, so every upload — from any user, any
    device — ends up compressed the same way, regardless of what originally sent it."""
    try:
        with Image.open(BytesIO(contents)) as img:
            img.load()
            img = ImageOps.exif_transpose(img)  # honor the phone's rotation before EXIF is stripped
            is_jpeg = extension in (".jpg", ".jpeg")
            if is_jpeg and img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            if max(img.size) > MAX_IMAGE_DIM:
                img.thumbnail((MAX_IMAGE_DIM, MAX_IMAGE_DIM), Image.LANCZOS)
            out = BytesIO()
            if is_jpeg:
                img.save(out, format="JPEG", quality=JPEG_QUALITY, optimize=True)
            else:
                img.save(out, format="PNG", optimize=True)
            return out.getvalue()
    except Image.DecompressionBombError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Image is too large to process") from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid image file") from exc


def validate_upload(
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
    reencode_images: bool = True,
) -> str:
    """Validate and persist an uploaded file under /uploads/{module}/{YYYY}/{MM}/.

    Returns the public URL path under /uploads/.
    """
    extension = validate_upload(file, allowed_ext=allowed_ext, allowed_mime=allowed_mime)

    contents = await file.read()
    if len(contents) > max_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"File exceeds {max_bytes // (1024 * 1024)}MB limit")
    if not contents:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file")

    return persist_upload(contents, extension, module, reencode_images=reencode_images)


def persist_upload(contents: bytes, extension: str, module: str, reencode_images: bool = True) -> str:
    """The write half of save_upload, for a caller that already has the validated bytes in hand (for
    example because it also needs to parse them) and so can't read an UploadFile's stream twice."""
    _validate_file_signature(contents, extension)
    if reencode_images and extension in {".jpg", ".jpeg", ".png"}:
        contents = _reencode_image(contents, extension)
    now = datetime.utcnow()
    sub = settings.resolved_upload_dir / module / f"{now.year:04d}" / f"{now.month:02d}"
    os.makedirs(sub, exist_ok=True)
    name = f"{uuid.uuid4().hex}{extension}"
    full_path = sub / name
    with open(full_path, "wb") as f:
        f.write(contents)
    return to_public_upload_path(str(full_path))


async def read_upload_bytes(
    file: UploadFile,
    allowed_ext: set[str] | None = None,
    allowed_mime: set[str] | None = None,
    max_bytes: int = MAX_BYTES,
    reencode_images: bool = True,
) -> tuple[bytes, str, str, int]:
    extension = validate_upload(file, allowed_ext=allowed_ext, allowed_mime=allowed_mime)

    contents = await file.read()
    if len(contents) > max_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"File exceeds {max_bytes // (1024 * 1024)}MB limit")
    if not contents:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file")
    _validate_file_signature(contents, extension)
    if reencode_images and extension in {".jpg", ".jpeg", ".png"}:
        contents = _reencode_image(contents, extension)

    original = os.path.basename((file.filename or "").replace("\\", "/"))
    safe_name = original or f"upload{extension}"
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
