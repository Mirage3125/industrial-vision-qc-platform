from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

from backend.app.core.config import PROJECT_ROOT
from backend.app.core.errors import AppError

router = APIRouter(prefix="/files", tags=["files"])

ALLOWED_ROOTS = ("data", "artifacts")
ALLOWED_SUFFIXES = {
    ".bmp",
    ".gif",
    ".htm",
    ".html",
    ".jpeg",
    ".jpg",
    ".json",
    ".md",
    ".png",
    ".tif",
    ".tiff",
    ".txt",
    ".webp",
}
DENIED_NAMES = {".env", "factory_vision.db"}


def _allowed_roots() -> list[Path]:
    return [(PROJECT_ROOT / name).resolve() for name in ALLOWED_ROOTS]


@router.get("")
def get_file(path: str) -> FileResponse:
    requested = Path(path)
    if requested.is_absolute():
        raise AppError("FILE_ACCESS_DENIED", "Absolute paths are not allowed", 403)
    if any(part in {"..", ""} for part in requested.parts):
        raise AppError("FILE_ACCESS_DENIED", "Path traversal is not allowed", 403)
    if requested.name.lower() in DENIED_NAMES:
        raise AppError("FILE_ACCESS_DENIED", "File name is not allowed", 403)

    target = (PROJECT_ROOT / requested).resolve()
    allowed_roots = _allowed_roots()
    if not any(target.is_relative_to(root) for root in allowed_roots):
        raise AppError("FILE_ACCESS_DENIED", "File path is not allowed", 403)
    if not target.is_file():
        raise AppError("FILE_NOT_FOUND", "File does not exist", 404)
    if target.suffix.lower() not in ALLOWED_SUFFIXES:
        raise AppError("FILE_TYPE_DENIED", "File type is not allowed", 403)

    media_type, _ = mimetypes.guess_type(target.name)
    response = FileResponse(target, media_type=media_type or "application/octet-stream")
    response.headers["Cache-Control"] = "private, max-age=300"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response
