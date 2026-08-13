"""
File upload routes — resume PDF/DOCX upload and download.
"""

import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from backend.auth.dependencies import get_current_user, require_role
from backend.config import settings
from backend.models.user import User
from backend.services.file_parser import parse_uploaded_resume

router = APIRouter(prefix="/api/uploads", tags=["Uploads"])

ALLOWED_EXTENSIONS = {"pdf", "docx", "doc", "txt"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def _ensure_upload_dir() -> str:
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    return settings.UPLOAD_DIR


@router.post("/resume")
async def upload_resume(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    """
    Upload a resume file (PDF, DOCX, TXT).
    Returns the extracted text and the stored filename.
    """
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '.{ext}'. Accepted: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10 MB)")

    # Extract text
    try:
        extracted_text = parse_uploaded_resume(file.filename, content)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Failed to parse file: {exc}")

    # Save file
    upload_dir = _ensure_upload_dir()
    stored_name = f"{uuid.uuid4().hex}_{file.filename}"
    filepath = os.path.join(upload_dir, stored_name)
    with open(filepath, "wb") as f:
        f.write(content)

    return {
        "filename": stored_name,
        "original_name": file.filename,
        "extracted_text": extracted_text,
        "size_bytes": len(content),
    }


@router.get("/resume/{filename}")
def download_resume(
    filename: str,
    user: User = Depends(require_role("recruiter")),
):
    """Download a previously uploaded resume file."""
    filepath = os.path.join(settings.UPLOAD_DIR, filename)
    if not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(filepath, filename=filename)
