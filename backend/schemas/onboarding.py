"""
Onboarding schemas — request/response models for candidate-to-employee conversion
and document verification.
"""

from typing import Optional

from pydantic import BaseModel

# ── Document verification ─────────────────────────────────────────────────────

class DocumentVerifyResponse(BaseModel):
    document_type: str = "Unknown"
    is_valid: bool = False
    confidence: str = "Low"
    details: str = ""


# ── Candidate → Employee conversion ──────────────────────────────────────────

class OnboardConvertRequest(BaseModel):
    candidate_id: int
    employee_id: str  # auto-generated on frontend, e.g. INF-EMP-260804-001
    department: str = "Engineering & Technology"
    manager: str = ""
    designation: Optional[str] = None  # override; defaults to candidate's role
    location: Optional[str] = None  # override; defaults to candidate's location
    ready_for: str = ""
    skill_gap: str = ""


class OnboardConvertResponse(BaseModel):
    message: str = "Candidate onboarded successfully"
