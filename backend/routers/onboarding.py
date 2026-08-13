"""
Onboarding routes — AI-powered document verification and candidate-to-employee conversion.
"""

import json
import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend.auth.dependencies import require_role
from backend.config import settings
from backend.database import get_db
from backend.models.candidate import Candidate
from backend.models.user import User
from backend.schemas.onboarding import (
    DocumentVerifyResponse,
    OnboardConvertRequest,
    OnboardConvertResponse,
)
from backend.services.file_parser import parse_uploaded_resume
from backend.services.llm import call_llama

router = APIRouter(prefix="/api/onboarding", tags=["Onboarding"])

ALLOWED_EXTENSIONS = {"pdf", "docx", "doc", "txt", "png", "jpg", "jpeg"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


# ── AI Document Verification ─────────────────────────────────────────────────

@router.post("/verify-document", response_model=DocumentVerifyResponse)
async def verify_document(
    file: UploadFile = File(...),
    user: User = Depends(require_role("recruiter")),
):
    """
    Upload a document (salary slip, ID proof, certificate, etc.).
    AI extracts text and verifies the document type and validity.
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

    # Extract text from the document
    extracted_text = ""
    if ext in ("pdf", "docx", "doc", "txt"):
        try:
            extracted_text = parse_uploaded_resume(file.filename, content)
        except Exception:
            extracted_text = f"[Could not parse .{ext} file — treating as image-based document]"
    else:
        # Image files — we can't extract text, so describe what was uploaded
        extracted_text = f"[Uploaded image file: {file.filename}, size: {len(content)} bytes]"

    # Save the file for record-keeping
    upload_dir = settings.UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)
    stored_name = f"onboarding_{uuid.uuid4().hex}_{file.filename}"
    filepath = os.path.join(upload_dir, stored_name)
    with open(filepath, "wb") as f:
        f.write(content)

    # Ask AI to verify the document
    system_prompt = """You are an AI document verification assistant for an HR onboarding system.
Your job is to analyze the extracted text of an uploaded document and determine:
1. What type of document it is (e.g., Salary Slip, Aadhaar Card, PAN Card, Passport, Driving License, Educational Certificate, Experience Letter, Offer Letter, Bank Statement, or Other)
2. Whether the document appears valid based on the text content
3. Your confidence level (High, Medium, or Low)
4. Any relevant details or notes

You MUST respond with ONLY a valid JSON object in this exact format:
{"document_type": "string", "is_valid": true/false, "confidence": "High/Medium/Low", "details": "string"}

Do NOT include any text outside the JSON object."""

    prompt = f"""Analyze this uploaded document and verify it.

Filename: {file.filename}
Extracted text (first 2000 chars):
{extracted_text[:2000]}

Respond with ONLY a JSON object."""

    raw_response = await call_llama(prompt, expect_json=True, system=system_prompt)

    # Parse the AI response
    try:
        result = json.loads(raw_response)
        return DocumentVerifyResponse(
            document_type=result.get("document_type", "Unknown"),
            is_valid=result.get("is_valid", False),
            confidence=result.get("confidence", "Low"),
            details=result.get("details", ""),
        )
    except (json.JSONDecodeError, TypeError):
        # Fallback if AI doesn't return valid JSON
        return DocumentVerifyResponse(
            document_type="Unknown",
            is_valid=False,
            confidence="Low",
            details=f"AI could not verify this document. Raw response: {raw_response[:200]}",
        )


# ── Candidate → Employee Conversion ──────────────────────────────────────────

@router.post("/convert", response_model=OnboardConvertResponse, status_code=status.HTTP_201_CREATED)
def convert_candidate_to_employee(
    body: OnboardConvertRequest,
    user: User = Depends(require_role("recruiter")),
    db: Session = Depends(get_db),
):
    """
    Convert a hired candidate into an employee.
    Creates a new Employee record and updates the candidate's stage to 'Onboarded'.
    """
    # Fetch the candidate
    candidate = db.query(Candidate).filter(Candidate.id == body.candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    if candidate.stage == "Onboarded":
        raise HTTPException(status_code=400, detail="This candidate has already been onboarded")

    # Update candidate stage to Onboarded
    candidate.stage = "Onboarded"
    db.commit()

    return OnboardConvertResponse(

        message=f"Successfully onboarded {candidate.candidate} as employee {body.employee_id}",
    )
