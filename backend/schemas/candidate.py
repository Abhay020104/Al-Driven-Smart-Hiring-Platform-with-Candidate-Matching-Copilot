"""
Candidate schemas.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CandidateBase(BaseModel):
    candidate: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: str
    location: str = ""
    experience: float = 0.0
    match: int = 0
    skills_match: int = 0
    stage: str = "Screening"
    availability: str = ""
    salary_fit: str = ""
    risk: str = "Low"
    skills: str = ""
    source: str = ""
    last_touch: str = ""
    education: str = ""
    certifications: str = ""
    summary: str = ""


class CandidateCreate(CandidateBase):
    user_id: Optional[int] = None
    resume_filename: Optional[str] = None


class CandidateUpdate(BaseModel):
    candidate: Optional[str] = None
    role: Optional[str] = None
    location: Optional[str] = None
    experience: Optional[float] = None
    match: Optional[int] = None
    skills_match: Optional[int] = None
    stage: Optional[str] = None
    availability: Optional[str] = None
    salary_fit: Optional[str] = None
    risk: Optional[str] = None
    skills: Optional[str] = None
    source: Optional[str] = None
    last_touch: Optional[str] = None
    education: Optional[str] = None
    certifications: Optional[str] = None
    summary: Optional[str] = None
    resume_filename: Optional[str] = None


class CandidateOut(CandidateBase):
    id: int
    user_id: Optional[int] = None
    resume_filename: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CandidateApplyRequest(BaseModel):
    """Used by Candidate role to apply for a job."""
    role: str
    email: Optional[str] = None
    phone: Optional[str] = None
    location: str = ""
    experience: float = 0.0
    availability: str = ""
    skills: str = ""
    education: str = ""
    certifications: str = ""
    summary: str = ""
    match: Optional[int] = 0
    skills_match: Optional[int] = 0
    resume_filename: Optional[str] = None
